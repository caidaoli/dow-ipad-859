# encoding:utf-8
import io
import os
import mimetypes
import threading
import json
import requests
from urllib.parse import urlparse, unquote

from bot.bot import Bot
from lib.dify.dify_client import DifyClient, ChatClient
from bot.dify.dify_session import DifySession, DifySessionManager
from bridge.context import ContextType, Context
from bridge.reply import Reply, ReplyType
from common.log import logger
from common import const, memory
from common.utils import parse_markdown_text, print_red
from common.tmp_dir import TmpDir
from config import conf

UNKNOWN_ERROR_MSG = "我暂时遇到了一些问题，请您稍后重试~"

class DifyBot(Bot):
    def __init__(self):
        super().__init__()
        self.sessions = DifySessionManager(DifySession, model=conf().get("model", const.DIFY))
        # 初始化内部状态
        self.current_app_type = conf().get("dify_app_type", "chatflow")
        # 支持的应用类型列表
        self.supported_app_types = [
            const.DIFY_CHATBOT,    # "chatbot"
            const.DIFY_AGENT,      # "agent"
            const.DIFY_CHATFLOW,   # "chatflow"
            const.DIFY_WORKFLOW    # "workflow"
        ]
        # 初始化API配置
        self.api_key = conf().get("dify_api_key", "")
        self.api_base = conf().get("dify_api_base", "https://api.dify.ai/v1")

    def reply(self, query, context: Context=None):
        # 处理模型切换命令
        if query.startswith("#model "):
            return self._handle_model_command(query[7:].strip())
            
        # acquire reply content
        if context.type == ContextType.TEXT or context.type == ContextType.IMAGE_CREATE:
            if context.type == ContextType.IMAGE_CREATE:
                query = conf().get('image_create_prefix', ['画'])[0] + query
            logger.info("[DIFY] query={}".format(query))
            session_id = context["session_id"]
            # TODO: 适配除微信以外的其他channel
            channel_type = conf().get("channel_type", "wx859")
            user = None
            if channel_type in ["wx859", "wework", "gewechat"]:
                user = context["msg"].other_user_nickname if context.get("msg") else "default"
            elif channel_type in ["wechatcom_app", "wechatmp", "wechatmp_service", "wechatcom_service", "web"]:
                user = context["msg"].other_user_id if context.get("msg") else "default"
            else:
                return Reply(ReplyType.ERROR, f"unsupported channel type: {channel_type}, now dify only support wx, wechatcom_app, wechatmp, wechatmp_service channel")
            logger.debug(f"[DIFY] dify_user={user}")
            user = user if user else "default" # 防止用户名为None，当被邀请进的群未设置群名称时用户名为None
            session = self.sessions.get_session(session_id, user)
            if context.get("isgroup", False):
                # 群聊：根据是否是共享会话群来决定是否设置用户信息
                if not context.get("is_shared_session_group", False):
                    # 非共享会话群：设置发送者信息
                    session.set_user_info(context["msg"].actual_user_id, context["msg"].actual_user_nickname)
                else:
                    # 共享会话群：不设置用户信息
                    session.set_user_info('', '')
                # 设置群聊信息
                session.set_room_info(context["msg"].other_user_id, context["msg"].other_user_nickname)
            else:
                # 私聊：使用发送者信息作为用户信息，房间信息留空
                session.set_user_info(context["msg"].other_user_id, context["msg"].other_user_nickname)
                session.set_room_info('', '')

            # 打印设置的session信息
            logger.debug(f"[DIFY] Session user and room info - user_id: {session.get_user_id()}, user_name: {session.get_user_name()}, room_id: {session.get_room_id()}, room_name: {session.get_room_name()}")
            logger.debug(f"[DIFY] session={session} query={query}")

            reply, err = self._reply(query, session, context)
            if err != None:
                dify_error_reply = conf().get("dify_error_reply", None)
                error_msg = dify_error_reply if dify_error_reply else err
                reply = Reply(ReplyType.TEXT, error_msg)
            return reply
        else:
            reply = Reply(ReplyType.ERROR, "Bot不支持处理{}类型的消息".format(context.type))
            return reply

    def _handle_model_command(self, model):
        """处理模型切换命令"""
        if model in self.supported_app_types:
            # 更新内部状态
            self.current_app_type = model
            # 返回成功消息
            return Reply(ReplyType.INFO, f"已切换到 {model} 模式")
        else:
            # 返回错误消息
            supported_types = ", ".join(self.supported_app_types)
            return Reply(ReplyType.ERROR, f"不支持的应用类型: {model}。支持的类型有: {supported_types}")

    # TODO: delete this function
    def _get_payload(self, query, session: DifySession, response_mode):
        # 输入的变量参考 wechat-assistant-pro：https://github.com/leochen-g/wechat-assistant-pro/issues/76
        return {
            'inputs': {
                'user_id': session.get_user_id(),
                'user_name': session.get_user_name(),
                'room_id': session.get_room_id(),
                'room_name': session.get_room_name()
            },
            "query": query,
            "response_mode": response_mode,
            "conversation_id": session.get_conversation_id(),
            "user": session.get_user()
        }

    def _get_dify_conf(self, context: Context, key, default=None):
        return context.get(key, conf().get(key, default))

    def _reply(self, query: str, session: DifySession, context: Context):
        try:
            session.count_user_message() # 限制一个conversation中消息数，防止conversation过长
            
            # 【关键修改】使用内部状态而不是配置，强制 chatflow 走 agent 逻辑
            if self.current_app_type == 'chatbot':
                return self._handle_chatbot(query, session, context)
            elif self.current_app_type == 'agent' or self.current_app_type == 'chatflow':
                # 让 chatflow 也走 agent 的流式处理逻辑
                return self._handle_agent(query, session, context)
            elif self.current_app_type == 'workflow':
                return self._handle_workflow(query, session, context)
            else:
                friendly_error_msg = "[DIFY] 当前应用类型设置错误，目前仅支持 agent, chatbot, chatflow, workflow"
                return None, friendly_error_msg

        except Exception as e:
            error_info = f"[DIFY] Exception: {e}"
            logger.exception(error_info)
            return None, UNKNOWN_ERROR_MSG

    def _handle_chatbot(self, query: str, session: DifySession, context: Context):
        api_key = self.api_key
        api_base = self.api_base
        chat_client = ChatClient(api_key, api_base)
        response_mode = 'blocking'
        payload = self._get_payload(query, session, response_mode)
        files = self._get_upload_files(session, context)
        
        # 发送请求
        response = chat_client.create_chat_message(
            inputs=payload['inputs'],
            query=payload['query'],
            user=payload['user'],
            response_mode=payload['response_mode'],
            conversation_id=payload['conversation_id'],
            files=files
        )

        # 【调试代码】处理非200状态码
        if response.status_code != 200:
            error_info = f"[DIFY] payload={payload} response text={response.text} status_code={response.status_code}"
            logger.warning(error_info)
            # 打印明显的错误提示
            print(f"\n======== DIFY API ERROR ========")
            print(f"Status Code: {response.status_code}")
            print(f"API Base: {api_base}")
            print(f"Response: {response.text}")
            print(f"================================\n")
            friendly_error_msg = self._handle_error_response(response.text, response.status_code)
            return None, friendly_error_msg

        # 【安全解析】防止JSONDecodeError
        try:
            rsp_data = response.json()
        except Exception as e:
            logger.error(f"[DIFY] Failed to parse JSON. Response: {response.text}")
            print(f"【解析失败】Dify返回内容非JSON: {response.text}")
            return None, "Dify服务返回异常，请联系管理员检查后台日志。"

        logger.debug("[DIFY] usage {}".format(rsp_data.get('metadata', {}).get('usage', 0)))

        # 检查 answer 字段是否存在
        if 'answer' not in rsp_data:
             logger.error(f"[DIFY] Response missing 'answer' field: {rsp_data}")
             return None, "Dify返回数据缺失 answer 字段"

        answer = rsp_data['answer']
        parsed_content = parse_markdown_text(answer)

        at_prefix = ""
        channel = context.get("channel")
        is_group = context.get("isgroup", False)
        if is_group:
            at_prefix = "@" + context["msg"].actual_user_nickname + "\n"
        
        for item in parsed_content[:-1]:
            reply = None
            if item['type'] == 'text':
                content = at_prefix + item['content']
                reply = Reply(ReplyType.TEXT, content)
            elif item['type'] == 'image':
                image_url = self._fill_file_base_url(item['content'])
                image = self._download_image(image_url)
                if image:
                    reply = Reply(ReplyType.IMAGE, image)
                else:
                    reply = Reply(ReplyType.TEXT, f"图片链接：{image_url}")
            elif item['type'] == 'file':
                file_url = self._fill_file_base_url(item['content'])
                file_path = self._download_file(file_url)
                if file_path:
                    reply = Reply(ReplyType.FILE, file_path)
                else:
                    reply = Reply(ReplyType.TEXT, f"文件链接：{file_url}")
            logger.debug(f"[DIFY] reply={reply}")
            if reply and channel:
                channel.send(reply, context)
        
        # parsed_content 没有数据时，直接不回复
        if not parsed_content:
            return None, None
            
        final_item = parsed_content[-1]
        final_reply = None
        if final_item['type'] == 'text':
            content = final_item['content']
            if is_group:
                at_prefix = "@" + context["msg"].actual_user_nickname + "\n"
                content = at_prefix + content
            final_reply = Reply(ReplyType.TEXT, final_item['content'])
        elif final_item['type'] == 'image':
            image_url = self._fill_file_base_url(final_item['content'])
            image = self._download_image(image_url)
            if image:
                final_reply = Reply(ReplyType.IMAGE, image)
            else:
                final_reply = Reply(ReplyType.TEXT, f"图片链接：{image_url}")
        elif final_item['type'] == 'file':
            file_url = self._fill_file_base_url(final_item['content'])
            file_path = self._download_file(file_url)
            if file_path:
                final_reply = Reply(ReplyType.FILE, file_path)
            else:
                final_reply = Reply(ReplyType.TEXT, f"文件链接：{file_url}")

        # 设置dify conversation_id, 依靠dify管理上下文
        if session.get_conversation_id() == '':
            session.set_conversation_id(rsp_data['conversation_id'])

        return final_reply, None

    def _download_file(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            parsed_url = urlparse(url)
            logger.debug(f"Downloading file from {url}")
            url_path = unquote(parsed_url.path)
            # 从路径中提取文件名
            file_name = url_path.split('/')[-1]
            logger.debug(f"Saving file as {file_name}")
            file_path = os.path.join(TmpDir().path(), file_name)
            with open(file_path, 'wb') as file:
                file.write(response.content)
            return file_path
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
            return None

    def _download_image(self, url):
        try:
            pic_res = requests.get(url, stream=True)
            pic_res.raise_for_status()
            image_storage = io.BytesIO()
            size = 0
            for block in pic_res.iter_content(1024):
                size += len(block)
                image_storage.write(block)
            logger.debug(f"[WX] download image success, size={size}, img_url={url}")
            image_storage.seek(0)
            return image_storage
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
        return None

    def _handle_agent(self, query: str, session: DifySession, context: Context):
        api_key = self.api_key
        api_base = self.api_base
        chat_client = ChatClient(api_key, api_base)
        response_mode = 'streaming'
        payload = self._get_payload(query, session, response_mode)
        files = self._get_upload_files(session, context)
        response = chat_client.create_chat_message(
            inputs=payload['inputs'],
            query=payload['query'],
            user= payload['user'],
            response_mode=payload['response_mode'],
            conversation_id=payload['conversation_id'],
            files=files
        )

        if response.status_code != 200:
            error_info = f"[DIFY] payload={payload} response text={response.text} status_code={response.status_code}"
            logger.warning(error_info)
            print(f"\n======== DIFY AGENT ERROR ========")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            print(f"================================\n")
            friendly_error_msg = self._handle_error_response(response.text, response.status_code)
            return None, friendly_error_msg
        
        try:
            msgs, conversation_id = self._handle_sse_response(response)
        except Exception as e:
            logger.error(f"[DIFY] Failed to handle SSE response: {e}")
            return None, "流式响应解析失败"

        channel = context.get("channel")
        is_group = context.get("isgroup", False)
        for msg in msgs[:-1]:
            if msg['type'] == 'agent_message':
                if is_group:
                    at_prefix = "@" + context["msg"].actual_user_nickname + "\n"
                    msg['content'] = at_prefix + msg['content']
                reply = Reply(ReplyType.TEXT, msg['content'])
                channel.send(reply, context)
            elif msg['type'] == 'message_file':
                url = self._fill_file_base_url(msg['content']['url'])
                reply = Reply(ReplyType.IMAGE_URL, url)
                thread = threading.Thread(target=channel.send, args=(reply, context))
                thread.start()
        
        if not msgs:
            return None, None

        final_msg = msgs[-1]
        reply = None
        if final_msg['type'] == 'agent_message':
            reply = Reply(ReplyType.TEXT, final_msg['content'])
        elif final_msg['type'] == 'message_file':
            url = self._fill_file_base_url(final_msg['content']['url'])
            reply = Reply(ReplyType.IMAGE_URL, url)
        
        if session.get_conversation_id() == '':
            session.set_conversation_id(conversation_id)
        return reply, None

    def _handle_workflow(self, query: str, session: DifySession, context: Context):
        payload = self._get_workflow_payload(query, session)
        api_key = self.api_key
        api_base = self.api_base
        dify_client = DifyClient(api_key, api_base)
        response = dify_client._send_request("POST", "/workflows/run", json=payload)
        
        if response.status_code != 200:
            error_info = f"[DIFY] payload={payload} response text={response.text} status_code={response.status_code}"
            logger.warning(error_info)
            print(f"\n======== DIFY WORKFLOW ERROR ========")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            print(f"====================================\n")
            friendly_error_msg = self._handle_error_response(response.text, response.status_code)
            return None, friendly_error_msg

        try:
            rsp_data = response.json()
        except Exception as e:
            logger.error(f"[DIFY] Workflow response not JSON: {response.text}")
            return None, "工作流返回数据异常"

        if 'data' not in rsp_data or 'outputs' not in rsp_data['data'] or 'text' not in rsp_data['data']['outputs']:
            error_info = f"[DIFY] Unexpected response format: {rsp_data}"
            logger.warning(error_info)
        reply = Reply(ReplyType.TEXT, rsp_data['data']['outputs']['text'])
        return reply, None

    def _get_upload_files(self, session: DifySession, context: Context):
        session_id = session.get_session_id()
        img_cache = memory.USER_IMAGE_CACHE.get(session_id)
        if not img_cache or not self._get_dify_conf(context, "image_recognition", False):
            return None
        # 清理图片缓存
        memory.USER_IMAGE_CACHE[session_id] = None
        api_key = self.api_key
        api_base = self.api_base
        dify_client = DifyClient(api_key, api_base)
        msg = img_cache.get("msg")
        path = img_cache.get("path")
        msg.prepare()

        with open(path, 'rb') as file:
            file_name = os.path.basename(path)
            file_type, _ = mimetypes.guess_type(file_name)
            files = {
                'file': (file_name, file, file_type)
            }
            response = dify_client.file_upload(user=session.get_user(), files=files)

        if response.status_code != 200 and response.status_code != 201:
            error_info = f"[DIFY] response text={response.text} status_code={response.status_code} when upload file"
            logger.warning(error_info)
            return None, error_info
        
        try:
            file_upload_data = response.json()
        except:
             return None, "File upload response not JSON"

        logger.debug("[DIFY] upload file {}".format(file_upload_data))
        return [
            {
                "type": "image",
                "transfer_method": "local_file",
                "upload_file_id": file_upload_data['id']
            }
        ]

    def _fill_file_base_url(self, url: str):
        if url.startswith("https://") or url.startswith("http://"):
            return url
        # 补全文件base url, 默认使用去掉"/v1"的dify api base url
        return self._get_file_base_url() + url

    def _get_file_base_url(self) -> str:
        api_base = conf().get("dify_api_base", "https://api.dify.ai/v1")
        return api_base.replace("/v1", "")

    def _get_workflow_payload(self, query, session: DifySession):
        return {
            'inputs': {
                "query": query
            },
            "response_mode": "blocking",
            "user": session.get_user()
        }

    def _parse_sse_event(self, event_str):
        """
        Parses a single SSE event string and returns a dictionary of its data.
        """
        event_prefix = "data: "
        if not event_str.startswith(event_prefix):
            return None
        trimmed_event_str = event_str[len(event_prefix):]

        # Check if trimmed_event_str is not empty and is a valid JSON string
        if trimmed_event_str:
            try:
                event = json.loads(trimmed_event_str)
                return event
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON from SSE event: {trimmed_event_str}")
                return None
        else:
            logger.warning("Received an empty SSE event.")
            return None

    # 【关键修改2】增加对 workflow_finished 的解析，并在最后强制打包
    def _handle_sse_response(self, response: requests.Response):
        events = []
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                event = self._parse_sse_event(decoded_line)
                if event:
                    events.append(event)

        merged_message = []
        accumulated_agent_message = ''
        conversation_id = None
        
        for event in events:
            event_name = event['event']
            
            # 1. 普通消息 / Agent消息
            if event_name == 'agent_message' or event_name == 'message':
                accumulated_agent_message += event['answer']
                logger.debug("[DIFY] accumulated_agent_message: {}".format(accumulated_agent_message))
                if not conversation_id:
                    conversation_id = event['conversation_id']
            
            # 2. Agent 思考过程
            elif event_name == 'agent_thought':
                self._append_agent_message(accumulated_agent_message, merged_message)
                accumulated_agent_message = ''
                logger.debug("[DIFY] agent_thought: {}".format(event))
            
            # 3. 文件消息
            elif event_name == 'message_file':
                self._append_agent_message(accumulated_agent_message, merged_message)
                accumulated_agent_message = ''
                self._append_message_file(event, merged_message)
                
            # 4. 【新增】 Chatflow 工作流结束事件
            elif event_name == 'workflow_finished':
                logger.debug(f"[DIFY] workflow_finished: {event}")
                if 'outputs' in event['data']:
                    outputs = event['data']['outputs']
                    # 尝试多种可能的字段名
                    final_text = outputs.get('answer') or outputs.get('result') or outputs.get('text') or str(outputs)
                    
                    # 【核心修复】：只有当之前没有收到流式消息时，才使用 workflow_finished 的结果
                    if not accumulated_agent_message:
                        accumulated_agent_message = final_text
                    
                if not conversation_id:
                    conversation_id = event['conversation_id']
            
            # 5. 消息结束
            elif event_name == 'message_end':
                self._append_agent_message(accumulated_agent_message, merged_message)
                logger.debug("[DIFY] message_end usage: {}".format(event.get('metadata', {}).get('usage')))
                break
            
            # 忽略其他不重要的中间事件
            elif event_name in ['workflow_started', 'node_started', 'node_finished', 'message_replace', 'ping']:
                pass
                
            elif event_name == 'error':
                logger.error("[DIFY] error: {}".format(event))
                raise Exception(event)
            else:
                logger.warning("[DIFY] unknown event: {}".format(event))

        # === 【关键修复】循环结束后，强制把最后积攒的消息打包 ===
        if accumulated_agent_message:
            self._append_agent_message(accumulated_agent_message, merged_message)
        # ========================================================

        if not conversation_id:
             conversation_id = "workflow_session_id_placeholder"

        return merged_message, conversation_id

    def _append_agent_message(self, accumulated_agent_message,  merged_message):
        if accumulated_agent_message:
            merged_message.append({
                'type': 'agent_message',
                'content': accumulated_agent_message,
            })

    def _append_message_file(self, event: dict, merged_message: list):
        if event.get('type') != 'image':
            logger.warning("[DIFY] unsupported message file type: {}".format(event))
        merged_message.append({
            'type': 'message_file',
            'content': event,
        })

    def _handle_error_response(self, response_text, status_code):
        """处理错误响应并提供用户指导"""
        try:
            friendly_error_msg = UNKNOWN_ERROR_MSG
            try:
                error_data = json.loads(response_text)
            except:
                # 如果错误信息都不是json，直接返回状态码
                return f"[DIFY] 请求失败，状态码 {status_code}，请检查API地址配置。"

            if status_code == 400 and "agent chat app does not support blocking mode" in error_data.get("message", "").lower():
                friendly_error_msg = "[DIFY] 请把config.json中的dify_app_type修改为agent再重启机器人尝试"
                print_red(friendly_error_msg)
            elif status_code == 401 and error_data.get("code", "").lower() == "unauthorized":
                friendly_error_msg = "[DIFY] apikey无效, 请检查config.json中的dify_api_key或dify_api_base是否正确"
                print_red(friendly_error_msg)
            elif status_code == 404:
                friendly_error_msg = f"[DIFY] 404 Not Found: 请检查 dify_api_base 配置。当前尝试访问: {self.api_base}"
                print_red(friendly_error_msg)
            
            return friendly_error_msg
        except Exception as e:
            logger.error(f"Failed to handle error response, response_text: {response_text} error: {e}")
            return UNKNOWN_ERROR_MSG
