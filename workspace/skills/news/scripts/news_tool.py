# -*- coding: utf-8 -*-
import sys
import requests
import json
import argparse
import io

# Ensure UTF-8 output
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def fetch_sina_hot(count=10):
    """Fetch top news from Sina News Roll API (Public)."""
    # lid 2509 is general news
    url = f"https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&num={count}"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        
        items = data.get('result', {}).get('data', [])
        if not items:
            return "No hot news found at the moment."
            
        output = ["📰 今日头条 / Top News:"]
        for i, item in enumerate(items, 1):
            title = item.get('title')
            link = item.get('url')
            # link usually starts with //
            if link.startswith('//'): link = 'https:' + link
            ctime = item.get('createtime', '')
            output.append(f"{i}. {title}\n   [{ctime}] URL: {link}")
            
        return "\n\n".join(output)
    except Exception as e:
        return f"Error fetching Sina news: {str(e)}"

def search_news(query, count=5):
    """Search news by filtering Sina Roll API results by keyword (stable JSON API, no scraping).
    
    原来的实现依赖新浪搜索页面的 CSS 选择器 (.box-result) 和 36Kr JS 渲染页面，
    两者均已失效。现改为从新浪 Roll API 拉取大量新闻后在本地做关键词过滤。
    """
    fetch_count = max(count * 6, 60)
    url = f"https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&num={fetch_count}"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        items = data.get('result', {}).get('data', [])

        if not items:
            return f"No news found for '{query}'."

        # Split query into individual keywords for flexible matching
        keywords = [kw.strip() for kw in query.replace(',', ' ').split() if kw.strip()]

        matched = []
        for item in items:
            title = item.get('title', '')
            intro = item.get('intro', '') or item.get('summary', '') or ''
            text = title + intro
            # Match if ANY keyword appears in the title+intro
            if any(kw in text for kw in keywords):
                link = item.get('url', '')
                if link.startswith('//'): link = 'https:' + link
                ctime = item.get('createtime', '')
                matched.append((title, ctime, link))
            if len(matched) >= count:
                break

        if not matched:
            # Fallback: return hot news with a note
            return _fallback_hot_news(query, count)

        output = [f"📰 '{query}' 相关新闻搜索结果："]
        for i, (title, ctime, link) in enumerate(matched, 1):
            output.append(f"{i}. {title}\n   [{ctime}] URL: {link}")
        return "\n\n".join(output)

    except Exception as e:
        return f"Error searching news: {str(e)}"


def _fallback_hot_news(query, count=5):
    """Fallback: return top hot news with a note that specific query has no match."""
    url = f"https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2509&num={count}"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        items = data.get('result', {}).get('data', [])

        if not items:
            return f"No news found for '{query}'. Please try using 'search_web' tool if available."

        output = [f"未找到精确匹配 '{query}' 的新闻，以下是当前热点新闻供参考："]
        for i, item in enumerate(items[:count], 1):
            title = item.get('title', '')
            link = item.get('url', '')
            if link.startswith('//'): link = 'https:' + link
            ctime = item.get('createtime', '')
            output.append(f"{i}. {title}\n   [{ctime}] URL: {link}")
        return "\n\n".join(output)
    except Exception as e:
        return f"No news found for '{query}'. Please try using 'search_web' tool if available."


def main():
    parser = argparse.ArgumentParser(description="Multi-source News Tool")
    subparsers = parser.add_subparsers(dest="command")
    
    subparsers.add_parser("hot", help="Get top trending news")
    
    s_p = subparsers.add_parser("search", help="Search news by keyword")
    s_p.add_argument("query", help="Keyword to search")
    s_p.add_argument("count", type=int, nargs="?", default=5)
    
    args = parser.parse_args()
    
    if args.command == "hot":
        print(fetch_sina_hot())
    elif args.command == "search":
        print(search_news(args.query, args.count))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
