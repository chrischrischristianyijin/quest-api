from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
import asyncio
import random
from readability import Document


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


async def extract_metadata_from_url(url: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await _get_with_retries(client, url)
            response.raise_for_status()

            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')

            title = extract_title(soup)
            description = extract_description(soup)
            image_url = extract_image(soup, url)

            metadata = {
                "title": title,
                "description": description,
                "image_url": image_url,
                "url": url,
                "domain": urlparse(url).netloc,
                "extracted_at": datetime.utcnow().isoformat()
            }

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


DEFAULT_HEADERS: Dict[str, str] = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'Cache-Control': 'no-cache',
}


async def _get_with_retries(client: httpx.AsyncClient, url: str, max_retries: int = 2, base_delay: float = 0.5) -> httpx.Response:
    attempt = 0
    last_exc: Optional[Exception] = None
    while attempt <= max_retries:
        try:
            return await client.get(url, headers=DEFAULT_HEADERS, follow_redirects=True)
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
        async with httpx.AsyncClient(timeout=15.0) as client:
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
                        if 'Just a moment' in page_title or 'Cloudflare' in page_title or 'cf-challenge' in (html or ''):
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


