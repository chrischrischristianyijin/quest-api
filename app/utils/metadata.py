from typing import Dict, Any, Optional, Callable
from datetime import datetime
from urllib.parse import urlparse, urljoin
import os
import os
import httpx
from bs4 import BeautifulSoup
import asyncio
import random
from readability import Document
import json
import time
import logging


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def _dbg(message: str) -> None:
    try:
        if (os.getenv('METADATA_DEBUG', '').lower() in ('1', 'true', 'yes')):
            logging.getLogger(__name__).info(f"[metadata] {message}")
    except Exception:
        pass


async def extract_metadata_from_url(url: str) -> Dict[str, Any]:
    """优先 API/标准源 → 回退页面解析。包含简单的 ETag/Last-Modified 缓存。"""
    # 1) 读取缓存（若存在且未过期）
    cached = _cache_get(url)
    if cached and cached.get('parsed_meta') and not _cache_expired(cached.get('ts', 0)):
        _dbg(f"cache hit (ttl ok) url={url}")
        return cached['parsed_meta']

    # 1.5) 简化模式：只取 OG/Twitter+basic（通过环境变量启用）
    try:
        if (os.getenv('METADATA_SIMPLE', '').lower() in ('1', 'true', 'yes')):
            _dbg(f"simple meta mode enabled url={url}")
            async with httpx.AsyncClient(timeout=8.0, proxies=_get_proxies()) as client:
                resp = await _get_with_retries(client, url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text or '', 'html.parser')
                title = extract_title(soup)
                description = extract_description(soup)
                image_url = extract_image(soup, url)
                metadata = {
                    'title': title,
                    'description': description,
                    'image_url': image_url,
                    'url': url,
                    'domain': urlparse(url).netloc,
                    'extracted_at': datetime.utcnow().isoformat()
                }
                _cache_set(url, resp, metadata)
                return metadata
    except Exception:
        # 简化模式失败，继续走正常流程
        _dbg(f"simple meta mode failed, fallback url={url}")

    try:
        async with httpx.AsyncClient(timeout=10.0, proxies=_get_proxies()) as client:
            # 2) 先发起一次 GET（带上 If-None-Match / If-Modified-Since）以获取页面结构
            extra_headers: Dict[str, str] = {}
            if cached:
                if cached.get('etag'):
                    extra_headers['If-None-Match'] = cached['etag']
                if cached.get('last_modified'):
                    extra_headers['If-Modified-Since'] = cached['last_modified']

            response = await _get_with_retries(client, url, extra_headers=extra_headers)

            if response.status_code == 304 and cached and cached.get('parsed_meta'):
                # 未修改：直接返回缓存
                _dbg(f"304 not modified, return cached url={url}")
                return cached['parsed_meta']

            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            _dbg(f"GET ok url={url} status={response.status_code} ct={(response.headers.get('content-type') or '').lower()}")

            # 3) 仅 meta：OG/Twitter 基础 + JSON-LD 补全
            title = extract_title(soup)
            description = extract_description(soup)
            image_url = extract_image(soup, url)
            jsonld_meta = _try_jsonld(soup)
            if jsonld_meta:
                if (not title) or title == '无标题':
                    title = jsonld_meta.get('title') or title
                if not description:
                    description = jsonld_meta.get('description') or description
                if not image_url:
                    image_url = jsonld_meta.get('image_url') or image_url
            metadata = {
                "title": title,
                "description": description,
                "image_url": image_url,
                "url": url,
                "domain": urlparse(url).netloc,
                "extracted_at": datetime.utcnow().isoformat()
            }
            _cache_set(url, response, metadata)
            _dbg(f"meta-only url={url} title_len={len(metadata['title'] or '')} desc_len={len(metadata['description'] or '')}")
            return metadata

    except httpx.TimeoutException as e:
        raise e
    except httpx.HTTPStatusError as e:
        raise e
    except Exception as e:
        raise e


def extract_title(soup: BeautifulSoup) -> str:
    title_selectors = [
        'meta[property="og:title"]',
        'meta[name="twitter:title"]',
        'title',
        'h1',
        'h2'
    ]

    for selector in title_selectors:
        element = soup.select_one(selector)
        if element:
            title = element.get('content') or element.get_text(strip=True)
            if title and len(title) > 0:
                return title[:200]
    return "无标题"


def extract_description(soup: BeautifulSoup) -> str:
    desc_selectors = [
        'meta[property="og:description"]',
        'meta[name="description"]',
        'meta[name="twitter:description"]',
        'meta[property="twitter:description"]'
    ]

    for selector in desc_selectors:
        element = soup.select_one(selector)
        if element:
            desc = element.get('content', '')
            if desc and len(desc) > 0:
                return desc[:500]

    paragraphs = soup.find_all('p')
    if paragraphs:
        text = ' '.join([p.get_text(strip=True) for p in paragraphs[:3]])
        if text:
            return text[:500]
    return ""


def extract_image(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    img_selectors = [
        'meta[property="og:image"]',
        'meta[name="twitter:image"]',
        'meta[property="twitter:image"]',
        'meta[property="og:image:secure_url"]'
    ]

    for selector in img_selectors:
        element = soup.select_one(selector)
        if element:
            img_url = element.get('content', '')
            if img_url:
                return normalize_image_url(img_url, base_url)

    img_tag = soup.find('img')
    if img_tag:
        img_url = img_tag.get('src') or img_tag.get('data-src')
        if img_url:
            return normalize_image_url(img_url, base_url)
    return None


def normalize_image_url(img_url: str, base_url: str) -> str:
    if img_url.startswith('http'):
        return img_url
    elif img_url.startswith('//'):
        return 'https:' + img_url
    elif img_url.startswith('/'):
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{img_url}"
    else:
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}/{img_url}"


UA_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36',
]


def _build_headers(url: str, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    headers: Dict[str, str] = {
        'User-Agent': random.choice(UA_LIST),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': base,
    }
    if extra:
        headers.update(extra)
    return headers


async def _get_with_retries(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int = 2,
    base_delay: float = 0.5,
    extra_headers: Optional[Dict[str, str]] = None,
) -> httpx.Response:
    attempt = 0
    last_exc: Optional[Exception] = None
    while attempt <= max_retries:
        try:
            headers = _build_headers(url, extra_headers)
            return await client.get(url, headers=headers, follow_redirects=True)
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            # 对明显的临时性错误做重试
            status = getattr(exc, 'response', None).status_code if getattr(exc, 'response', None) else None
            if isinstance(exc, httpx.RequestError) or status in {429, 500, 502, 503, 504}:
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.2)
                await asyncio.sleep(delay)
                attempt += 1
                continue
            raise
    # 用最后一次异常抛出
    if last_exc:
        raise last_exc
    # 理论上不会到这里
    raise httpx.RequestError("Unknown error without exception")


async def fetch_page_content(url: str) -> Dict[str, Any]:
    """抓取网页HTML与提取的纯文本内容。

    返回: { html: str | None, text: str | None, content_type: str | None, extracted_at: iso str }
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, proxies=_get_proxies()) as client:
            resp = await _get_with_retries(client, url, max_retries=2, base_delay=0.6)
            resp.raise_for_status()

            status_code = resp.status_code
            final_url = str(resp.url)
            content_type = (resp.headers.get('content-type') or '').lower()
            html: Optional[str] = None
            text: Optional[str] = None
            blocked_reason: Optional[str] = None

            # 类型判断
            if ('text/html' in content_type) or (content_type.startswith('application/xhtml')) or (content_type == ''):
                html = resp.text or None
                # 优先 Readability 提取
                article_html: Optional[str] = None
                try:
                    doc = Document(html or '')
                    article_html = doc.summary()  # 主体HTML
                except Exception:
                    article_html = None

                if article_html:
                    try:
                        article_soup = BeautifulSoup(article_html, 'html.parser')
                        for tag in article_soup(['script', 'style', 'noscript']):
                            tag.decompose()
                        extracted_text = article_soup.get_text('\n', strip=True)
                        if extracted_text:
                            text = extracted_text[:50000]
                    except Exception:
                        text = None
                else:
                    # 回退：简单主体提取
                    try:
                        soup = BeautifulSoup(html or '', 'html.parser')
                        for tag in soup(['script', 'style', 'noscript']):
                            tag.decompose()
                        main = soup.find('article') or soup.find(attrs={'role': 'main'}) or soup.find(id='main')
                        target = main if main else soup.body or soup
                        extracted_text = target.get_text(separator='\n', strip=True)
                        if extracted_text:
                            text = extracted_text[:50000]
                        # 粗略检测被拦截场景（Cloudflare/反爬）
                        page_title = (soup.title.string or '').strip() if soup.title and soup.title.string else ''
                        if 'Just a moment' in page_title or 'Cloudflare' in page_title or 'cf-challenge' in (html or '') or 'Attention Required!' in page_title:
                            blocked_reason = 'cloudflare_challenge'
                    except Exception:
                        text = None
            elif content_type.startswith('text/'):
                # 纯文本资源
                text = (resp.text or '')[:50000]
                html = None
            else:
                # 二进制/富媒体，不处理
                html = None
                text = None

            return {
                'html': html,
                'text': text,
                'content_type': content_type,
                'extracted_at': datetime.utcnow().isoformat(),
                'status_code': status_code,
                'final_url': final_url,
                'blocked_reason': blocked_reason,
            }
    except Exception:
        return {
            'html': None,
            'text': None,
            'content_type': None,
            'extracted_at': datetime.utcnow().isoformat(),
            'status_code': None,
            'final_url': None,
            'blocked_reason': 'exception',
        }


def _get_proxies() -> Optional[Dict[str, str]]:
    """从环境变量读取代理配置，未配置则返回 None。支持按需开启代理。
    HTTP_PROXY / HTTPS_PROXY
    """
    http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
    https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')
    proxies: Dict[str, str] = {}
    if http_proxy:
        proxies['http://'] = http_proxy
    if https_proxy:
        proxies['https://'] = https_proxy
    return proxies or None



# -------------------- API 优先：oEmbed / JSON-LD / RSS / 适配器 --------------------

async def _try_oembed(url: str, soup: BeautifulSoup, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    try:
        # 1) 页面内声明的 oEmbed
        link = soup.find('link', rel='alternate', type=lambda t: t and 'json+oembed' in t)
        oembed_url = None
        if link and link.get('href'):
            oembed_url = urljoin(url, link['href'])

        # 2) 常见平台 fallback（简化版）
        host = urlparse(url).netloc.lower()
        if not oembed_url:
            if 'youtube.com' in host or 'youtu.be' in host:
                oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
            elif 'vimeo.com' in host:
                oembed_url = f"https://vimeo.com/api/oembed.json?url={url}"

        if not oembed_url:
            return None

        resp = await _get_with_retries(client, oembed_url)
        resp.raise_for_status()
        data = resp.json()

        title = data.get('title')
        description = data.get('author_name') or data.get('provider_name') or ''
        image_url = data.get('thumbnail_url')
        return {
            'title': title or '无标题',
            'description': description or '',
            'image_url': image_url,
            'url': url,
            'domain': urlparse(url).netloc,
            'extracted_at': datetime.utcnow().isoformat()
        }
    except Exception:
        return None


def _try_jsonld(soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
    try:
        scripts = soup.find_all('script', type='application/ld+json')
        for s in scripts:
            try:
                data = json.loads(s.string or '')
            except Exception:
                continue

            # JSON-LD 可能是数组
            candidates = data if isinstance(data, list) else [data]
            for node in candidates:
                if not isinstance(node, dict):
                    continue
                node_type = node.get('@type')
                if isinstance(node_type, list):
                    node_type = next((t for t in node_type if isinstance(t, str)), None)
                if node_type in ['Article', 'NewsArticle', 'BlogPosting', 'Report']:
                    title = node.get('headline') or node.get('name')
                    description = node.get('description') or ''
                    image = node.get('image')
                    image_url = None
                    if isinstance(image, str):
                        image_url = image
                    elif isinstance(image, list) and image:
                        image_url = image[0]
                    elif isinstance(image, dict):
                        image_url = image.get('url')
                    return {
                        'title': (title or '无标题')[:200],
                        'description': description[:500] if isinstance(description, str) else '',
                        'image_url': image_url,
                    }
        return None
    except Exception:
        return None


async def _try_rss(url: str, soup: BeautifulSoup, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    try:
        link_tag = soup.find('link', rel='alternate', type=lambda t: t and ('rss+xml' in t or 'atom+xml' in t))
        if not link_tag or not link_tag.get('href'):
            return None
        feed_url = urljoin(url, link_tag['href'])
        resp = await _get_with_retries(client, feed_url)
        resp.raise_for_status()

        feed = BeautifulSoup(resp.text or '', 'xml')
        # 尝试匹配当前 URL 的条目
        item = None
        for it in feed.find_all(['item', 'entry']):
            link_el = it.find('link')
            href = link_el.get('href') if link_el and link_el.has_attr('href') else (link_el.text if link_el else None)
            if href and href.strip() == url:
                item = it
                break
        if not item:
            item = feed.find('item') or feed.find('entry')

        if not item:
            return None

        title = (item.find('title').text if item.find('title') else '')
        description = ''
        if item.find('description'):
            description = item.find('description').text
        elif item.find('summary'):
            description = item.find('summary').text

        # 简单提取首图（优先 media:content 或内容中第一张图）
        image_url = None
        media = item.find('media:content') or item.find('media:thumbnail')
        if media and media.has_attr('url'):
            image_url = media['url']
        else:
            content_el = item.find('content:encoded') or item.find('content')
            if content_el and content_el.text:
                content_soup = BeautifulSoup(content_el.text, 'html.parser')
                img_tag = content_soup.find('img')
                if img_tag and (img_tag.get('src') or img_tag.get('data-src')):
                    image_url = img_tag.get('src') or img_tag.get('data-src')

        return {
            'title': (title or '无标题')[:200],
            'description': (description or '')[:500],
            'image_url': image_url,
            'url': url,
            'domain': urlparse(url).netloc,
            'extracted_at': datetime.utcnow().isoformat()
        }
    except Exception:
        return None


# 预留：域名适配器（按需扩展）
DOMAIN_ADAPTERS: Dict[str, Callable[[str, httpx.AsyncClient], Any]] = {
    'dev.to': None,           # 预留，实际在 _adapter_devto 中实现
    'www.reddit.com': None,   # 预留，实际在 _adapter_reddit 中实现
}


async def _apply_domain_adapter(url: str, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    try:
        host = urlparse(url).netloc.lower()
        handler = DOMAIN_ADAPTERS.get(host)
        if not handler:
            return None
        # 绑定实现（延迟注册，避免导入顺序问题）
        if host == 'dev.to':
            handler = _adapter_devto
        elif host == 'www.reddit.com':
            handler = _adapter_reddit
        else:
            return None

        data = await handler(url, client)
        if not isinstance(data, dict):
            return None
        # 统一补充字段
        data.setdefault('url', url)
        data.setdefault('domain', host)
        data.setdefault('extracted_at', datetime.utcnow().isoformat())
        return data
    except Exception:
        return None


# -------------------- 简易缓存：ETag/Last-Modified + TTL --------------------

logger = logging.getLogger(__name__)
FETCH_CACHE_TTL_SECONDS = 24 * 60 * 60  # 24h
_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}


def _cache_expired(ts: float) -> bool:
    return (time.time() - ts) > FETCH_CACHE_TTL_SECONDS


def _cache_get(url: str) -> Optional[Dict[str, Any]]:
    return _METADATA_CACHE.get(url)


def _cache_set(url: str, resp: httpx.Response, parsed_meta: Dict[str, Any]) -> None:
    try:
        _METADATA_CACHE[url] = {
            'etag': resp.headers.get('etag'),
            'last_modified': resp.headers.get('last-modified'),
            'ts': time.time(),
            'parsed_meta': parsed_meta,
        }
    except Exception as e:
        logger.debug(f"cache set failed: {e}")


# -------------------- 站点适配器实现：dev.to / reddit --------------------

async def _adapter_devto(url: str, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    try:
        api = f"https://dev.to/api/articles?url={url}"
        resp = await _get_with_retries(client, api)
        resp.raise_for_status()
        arr = resp.json()
        if not isinstance(arr, list) or not arr:
            return None
        art = arr[0]
        title = art.get('title')
        description = art.get('description') or (art.get('tags') or '')
        image_url = art.get('cover_image') or art.get('social_image')
        return {
            'title': (title or '无标题')[:200],
            'description': (description or '')[:500],
            'image_url': image_url,
        }
    except Exception:
        return None


async def _adapter_reddit(url: str, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    try:
        # reddit 文章增加 .json 获取结构化
        if not url.endswith('.json'):
            api = url + ('' if url.endswith('/') else '/') + '.json'
        else:
            api = url
        resp = await _get_with_retries(client, api)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or not data:
            return None
        post = data[0]['data']['children'][0]['data']
        title = post.get('title')
        description = post.get('selftext') or post.get('subreddit_name_prefixed')
        image_url = post.get('thumbnail') if (post.get('thumbnail') or '').startswith('http') else None
        return {
            'title': (title or '无标题')[:200],
            'description': (description or '')[:500],
            'image_url': image_url,
        }
    except Exception:
        return None
