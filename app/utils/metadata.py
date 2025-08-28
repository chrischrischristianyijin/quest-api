from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


async def extract_metadata_from_url(url: str) -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = await client.get(url, headers=headers, follow_redirects=True)
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


