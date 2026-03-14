"""Web tools: web_search and web_fetch."""

import html
import ipaddress
import json
import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from nanobot.agent.tools.base import Tool
from nanobot.utils.http_client import http_client

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_2) AppleWebKit/537.36"
MAX_REDIRECTS = 5

BOCHA_API_URL = "https://api.bochaai.com/v1/web-search"

_PRIVATE_IP_RANGES = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
]


def _is_private_ip(host: str) -> bool:
    try:
        ip = ipaddress.ip_address(host)
        for network in _PRIVATE_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        return False


def _strip_tags(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r'<script[\s\S]*?</script>', '', text, flags=re.I)
    text = re.sub(r'<style[\s\S]*?</style>', '', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()


def _normalize(text: str) -> str:
    """Normalize whitespace."""
    text = re.sub(r'[ \t]+', ' ', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def _validate_url(url: str) -> tuple[bool, str]:
    """Validate URL: must be http(s) with valid domain and not a private/internal IP."""
    try:
        p = urlparse(url)
        if p.scheme not in ('http', 'https'):
            return False, f"Only http/https allowed, got '{p.scheme or 'none'}'"
        if not p.netloc:
            return False, "Missing domain"
        host = p.hostname
        if host and _is_private_ip(host):
            return False, f"Access to private/internal IP addresses is not allowed: {host}"
        return True, ""
    except Exception as e:
        return False, str(e)


class WebSearchTool(Tool):
    """Search the web using Bocha Search API (适合国内网络环境)."""
    
    name = "web_search"
    description = "Search the web. Returns titles, URLs, snippets and summaries."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "count": {"type": "integer", "description": "Results (1-50)", "minimum": 1, "maximum": 50},
            "freshness": {"type": "string", "enum": ["oneDay", "oneWeek", "oneMonth", "oneYear", "noLimit"],
                         "description": "Time range filter (default: noLimit)"},
            "summary": {"type": "boolean", "description": "Include long summary (default: true)"}
        },
        "required": ["query"]
    }
    
    def __init__(self, api_key: str | None = None, max_results: int = 10):
        self._init_api_key = api_key
        self.max_results = max_results

    @property
    def api_key(self) -> str:
        """Resolve API key at call time so env/config changes are picked up."""
        return self._init_api_key or os.environ.get("BOCHA_API_KEY", "")

    async def execute(
        self, 
        query: str, 
        count: int | None = None,
        freshness: str = "noLimit",
        summary: bool = True,
        **kwargs: Any
    ) -> str:
        if not self.api_key:
            return (
                "Error: 博查搜索 API key 未配置。"
                "请在 ~/.nanobot/config.json 的 tools.web.search.apiKey 中设置 "
                "(或设置环境变量 BOCHA_API_KEY)，然后重启网关。"
            )
        
        try:
            n = min(max(count or self.max_results, 1), 50)
            client = await http_client.get_client("web_search", timeout=15.0)
            r = await client.post(
                BOCHA_API_URL,
                json={
                    "query": query,
                    "count": n,
                    "freshness": freshness,
                    "summary": summary
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
            )
            r.raise_for_status()
            
            data = r.json()
            
            if data.get("code") != 200:
                return f"搜索失败: {data.get('msg', 'Unknown error')}"
            
            results = data.get("data", {}).get("webPages", {}).get("value", [])
            if not results:
                return f"未找到相关结果: {query}"
            
            lines = [f"搜索结果: {query}\n"]
            for i, item in enumerate(results[:n], 1):
                name = item.get("name", "")
                url = item.get("url", "")
                snippet = item.get("snippet", "")
                item_summary = item.get("summary", "")
                site_name = item.get("siteName", "")
                date_published = item.get("datePublished", "")
                
                lines.append(f"{i}. {name}")
                if site_name:
                    lines.append(f"   来源: {site_name}")
                if date_published:
                    lines.append(f"   时间: {date_published}")
                lines.append(f"   链接: {url}")
                if snippet:
                    lines.append(f"   摘要: {snippet}")
                if item_summary and summary:
                    lines.append(f"   详细: {item_summary}")
                lines.append("")
            
            return "\n".join(lines).strip()
        except httpx.HTTPStatusError as e:
            return f"搜索请求失败 (HTTP {e.response.status_code}): {e.response.text[:200]}"
        except Exception as e:
            return f"搜索出错: {e}"


class WebFetchTool(Tool):
    """Fetch and extract content from a URL using Readability."""
    
    name = "web_fetch"
    description = "Fetch URL and extract readable content (HTML → markdown/text)."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch"},
            "extractMode": {"type": "string", "enum": ["markdown", "text"], "default": "markdown"},
            "maxChars": {"type": "integer", "minimum": 100}
        },
        "required": ["url"]
    }
    
    def __init__(self, max_chars: int = 50000):
        self.max_chars = max_chars
    
    async def execute(self, url: str, extractMode: str = "markdown", maxChars: int | None = None, **kwargs: Any) -> str:
        from readability import Document

        max_chars = maxChars or self.max_chars

        # Validate URL before fetching
        is_valid, error_msg = _validate_url(url)
        if not is_valid:
            return json.dumps({"error": f"URL validation failed: {error_msg}", "url": url}, ensure_ascii=False)

        try:
            client = await http_client.get_client("web_fetch", timeout=30.0, max_redirects=MAX_REDIRECTS)
            r = await client.get(url, headers={"User-Agent": USER_AGENT})
            r.raise_for_status()
            
            ctype = r.headers.get("content-type", "")
            
            # JSON
            if "application/json" in ctype:
                text, extractor = json.dumps(r.json(), indent=2, ensure_ascii=False), "json"
            # HTML
            elif "text/html" in ctype or r.text[:256].lower().startswith(("<!doctype", "<html")):
                doc = Document(r.text)
                content = self._to_markdown(doc.summary()) if extractMode == "markdown" else _strip_tags(doc.summary())
                text = f"# {doc.title()}\n\n{content}" if doc.title() else content
                extractor = "readability"
            else:
                text, extractor = r.text, "raw"
            
            truncated = len(text) > max_chars
            if truncated:
                text = text[:max_chars]
            
            return json.dumps({"url": url, "finalUrl": str(r.url), "status": r.status_code,
                              "extractor": extractor, "truncated": truncated, "length": len(text), "text": text}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e), "url": url}, ensure_ascii=False)
    
    def _to_markdown(self, html: str) -> str:
        """Convert HTML to markdown."""
        # Convert links, headings, lists before stripping tags
        text = re.sub(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',
                      lambda m: f'[{_strip_tags(m[2])}]({m[1]})', html, flags=re.I)
        text = re.sub(r'<h([1-6])[^>]*>([\s\S]*?)</h\1>',
                      lambda m: f'\n{"#" * int(m[1])} {_strip_tags(m[2])}\n', text, flags=re.I)
        text = re.sub(r'<li[^>]*>([\s\S]*?)</li>', lambda m: f'\n- {_strip_tags(m[1])}', text, flags=re.I)
        text = re.sub(r'</(p|div|section|article)>', '\n\n', text, flags=re.I)
        text = re.sub(r'<(br|hr)\s*/?>', '\n', text, flags=re.I)
        return _normalize(_strip_tags(text))
