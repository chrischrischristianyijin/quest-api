from typing import Dict, Any, Optional, Callable
from datetime import datetime
from urllib.parse import urlparse, urljoin, parse_qs, unquote, quote
import os
import os
import httpx
from bs4 import BeautifulSoup, Comment
import asyncio
import random
from readability import Document
import json
import time
import logging
import re
import unicodedata
from typing import Tuple
import gzip
import bz2
from app.utils.curator_pipeline import apply_curator

# Sumy 内容预处理
try:
    from app.utils.sumy_summarizer import extract_key_content_with_sumy, _is_enabled as _sumy_preprocessing_enabled
    SUMY_PREPROCESSING_AVAILABLE = True
except ImportError:
    SUMY_PREPROCESSING_AVAILABLE = False
    extract_key_content_with_sumy = None
    _sumy_preprocessing_enabled = lambda: False

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except Exception:
    YouTubeTranscriptApi = None

try:
    from pdfminer.high_level import extract_text as pdf_extract_text
except Exception:
    pdf_extract_text = None


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

    # 1.2) Wikipedia 专用：REST Summary 优先
    try:
        host = urlparse(url).netloc.lower()
        if 'wikipedia.org' in host:
            async with httpx.AsyncClient(http2=True, timeout=8.0, proxies=_get_proxies()) as client:
                # 将 /wiki/Title 提取出来
                path = urlparse(url).path
                title_part = path.split('/wiki/', 1)[1] if '/wiki/' in path else None
                if title_part:
                    lang = host.split('.')[0] if host.count('.') >= 2 else 'en'
                    summary_api = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote(title_part, safe='')}"
                    resp = await _get_with_retries(client, summary_api)
                    resp.raise_for_status()
                    data = resp.json()
                    title = data.get('title') or '无标题'
                    description = (data.get('extract') or '')[:500]
                    image_url = None
                    if isinstance(data.get('thumbnail'), dict):
                        image_url = data['thumbnail'].get('source')
                    metadata = {
                        'title': title,
                        'description': description,
                        'image_url': image_url,
                        'url': url,
                        'domain': host,
                        'extracted_at': datetime.utcnow().isoformat(),
                        'canonical_url': data.get('content_urls', {}).get('desktop', {}).get('page') or url,
                        'site_name': 'Wikipedia',
                        'keywords': None,
                        'author': None,
                        'published_at': None,
                        'lang': lang,
                        'content_language': lang
                    }
                    return metadata
    except Exception:
        pass

    # 1.5) 简化模式：只取 OG/Twitter+basic（通过环境变量启用）
    try:
        if (os.getenv('METADATA_SIMPLE', '').lower() in ('1', 'true', 'yes')):
            _dbg(f"simple meta mode enabled url={url}")
            async with httpx.AsyncClient(http2=True, timeout=8.0, proxies=_get_proxies()) as client:
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
        async with httpx.AsyncClient(http2=True, timeout=10.0, proxies=_get_proxies()) as client:
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
                if (not title) or title == 'No title':
                    title = jsonld_meta.get('title') or title
                if not description:
                    description = jsonld_meta.get('description') or description
                if not image_url:
                    image_url = jsonld_meta.get('image_url') or image_url
            # 可选富化：当标题或描述欠缺时，尝试 oEmbed / RSS / 域适配器
            try:
                if os.getenv('METADATA_ENRICH', '').lower() in ('1', 'true', 'yes'):
                    async with httpx.AsyncClient(http2=True, timeout=6.0, proxies=_get_proxies()) as enrich_client:
                        enriched: Dict[str, Any] = {}
                        if (not title) or len(title) < 8:
                            enriched = await _try_oembed(url, soup, enrich_client) or enriched
                        if (not enriched) and ((not title) or (not description)):
                            enriched = await _try_rss(url, soup, enrich_client) or enriched
                        if (not enriched) and ((not title) or (not description) or (not image_url)):
                            maybe = await _apply_domain_adapter(url, enrich_client)
                            if maybe:
                                enriched = maybe
                        if enriched:
                            title = enriched.get('title') or title
                            description = enriched.get('description') or description
                            image_url = enriched.get('image_url') or image_url
            except Exception:
                pass

            cleaned_title = _clean_title(title, extract_site_name(soup), url)
            metadata = {
                "title": cleaned_title,
                "description": description,
                "image_url": image_url,
                "url": url,
                "domain": urlparse(url).netloc,
                "extracted_at": datetime.utcnow().isoformat(),
                "canonical_url": extract_canonical_url(soup, url),
                "site_name": extract_site_name(soup) or urlparse(url).netloc,
                "keywords": extract_keywords(soup),
                "author": extract_author(soup),
                "published_at": extract_published_time(soup),
                "lang": extract_lang(soup)[0],
                "content_language": extract_lang(soup)[1]
            }
            _cache_set(url, response, metadata)
            _dbg(f"meta-only url={url} title_len={len(metadata['title'] or '')} desc_len={len(metadata['description'] or '')}")
            # 若核心字段缺失，尝试 AMP 回退（CNN 等）
            if (not metadata.get('title')) or (not metadata.get('image_url')):
                try:
                    amp_url = extract_amp_url(soup, url)
                except Exception:
                    amp_url = None
                if amp_url and amp_url != url:
                    try:
                        amp_resp = await _get_with_retries(client, amp_url)
                        amp_resp.raise_for_status()
                        amp_soup = BeautifulSoup(amp_resp.text or '', 'html.parser')
                        amp_title = extract_title(amp_soup) or metadata.get('title')
                        amp_desc = extract_description(amp_soup) or metadata.get('description')
                        amp_img = extract_image(amp_soup, amp_url) or metadata.get('image_url')
                        metadata.update({
                            'title': _clean_title(amp_title, extract_site_name(amp_soup), amp_url),
                            'description': amp_desc,
                            'image_url': amp_img,
                            'canonical_url': extract_canonical_url(amp_soup, metadata.get('canonical_url') or url)
                        })
                    except Exception as amp_err:
                        _dbg(f"amp fallback failed url={amp_url} err={amp_err}")

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
        'meta[name="hdl"]',  # 一些新闻站点
        'meta[itemprop="headline"]',
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
        'meta[property="twitter:description"]',
        'meta[name="summary"]',
        'meta[itemprop="description"]'
    ]

    for selector in desc_selectors:
        element = soup.select_one(selector)
        if element:
            desc = element.get('content', '')
            if desc and len(desc) > 0:
                return desc[:500]

    paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]
    if paragraphs:
        # 选用较长的一段，避免导航/脚注
        paragraphs.sort(key=len, reverse=True)
        text = paragraphs[0]
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


def extract_canonical_url(soup: BeautifulSoup, fallback_url: str) -> str:
    link = soup.find('link', rel=lambda r: r and 'canonical' in r)
    href = link.get('href') if link and link.has_attr('href') else None
    return href or fallback_url


def extract_amp_url(soup: BeautifulSoup, fallback_url: str) -> Optional[str]:
    try:
        link = soup.find('link', rel=lambda r: r and ('amphtml' in r or 'AmpHTML' in r))
        href = link.get('href') if link and link.has_attr('href') else None
        if href:
            return urljoin(fallback_url, href)
        # 针对 CNN 的常见 AMP 形态
        host = urlparse(fallback_url).netloc.lower()
        path = urlparse(fallback_url).path or '/'
        if 'cnn.com' in host:
            # 优先 ?outputType=amp
            sep = '&' if ('?' in fallback_url) else '?'
            return fallback_url + f"{sep}outputType=amp"
        return None
    except Exception:
        return None


def extract_site_name(soup: BeautifulSoup) -> Optional[str]:
    og_site = soup.find('meta', property='og:site_name')
    if og_site and og_site.get('content'):
        return og_site['content']
    title_tag = soup.find('title')
    return title_tag.text.strip() if title_tag and title_tag.text else None


def _clean_title(title: Optional[str], site_name: Optional[str], url: str) -> str:
    try:
        raw = (title or '').strip()
        if not raw:
            return '无标题'
        # 常见分隔符清洗
        seps = [' | ', ' - ', ' — ', ' · ']
        for sep in seps:
            if sep in raw:
                parts = [p.strip() for p in raw.split(sep) if p and len(p.strip()) > 0]
                # 如果包含站点名且在末尾，去掉
                if site_name:
                    parts = [p for p in parts if p.lower() != site_name.lower()]
                if len(parts) >= 1:
                    return parts[0][:200]
        return raw[:200]
    except Exception:
        return (title or '无标题')[:200]


def _sanitize_html(html: Optional[str]) -> str:
    """将正文 HTML 做净化：移除脚本/样式/广告容器/表单/iframe 等，并清理危险属性。"""
    try:
        soup = BeautifulSoup(html or '', 'html.parser')
        # 移除注释
        for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
            c.extract()
        # 移除高风险或无关标签
        for tag in soup([
            'script', 'style', 'noscript', 'iframe', 'form', 'svg', 'canvas',
            'video', 'audio', 'source', 'track', 'object', 'embed', 'picture',
            'table', 'thead', 'tbody', 'tfoot', 'tr', 'td', 'th', 'pre', 'code'
        ]):
            tag.decompose()
        # 根据 class/id 规则移除广告/无关容器
        pattern = re.compile(
            r'(ad[s]?(vert)?|sponsor|promo|cookie|gdpr|banner|breadcrumb|sidebar|nav|header|footer|share|social|subscribe|newsletter|comment|related|recommend|outbrain|taboola)',
            re.I
        )
        for el in soup.find_all(True, id=pattern):
            el.decompose()
        for el in soup.find_all(True, class_=pattern):
            el.decompose()
        # 清除危险属性（事件/内联样式/数据属性），保留少量安全属性
        allowed_attrs = {'href', 'src', 'alt', 'title'}
        for el in soup.find_all(True):
            attrs = dict(el.attrs)
            for k in list(attrs.keys()):
                if k not in allowed_attrs:
                    del el.attrs[k]
                # 事件处理器 on*
                if k.lower().startswith('on'):
                    el.attrs.pop(k, None)
        # 规范空白：去掉多余空行
        return str(soup)
    except Exception:
        return html or ''


def _normalize_text(text: Optional[str], max_len: Optional[int] = None) -> str:
    """文本规范化：
    - Unicode NFKC（全角转半角、兼容分解）
    - 合并多余空行
    - 去除首尾空白
    - 长度截断（可配置）
    """
    try:
        s = (text or '')
        # 标准化
        s = unicodedata.normalize('NFKC', s)
        # 统一换行并合并多余空行
        lines = [ln.rstrip() for ln in s.splitlines()]
        compact: list[str] = []
        blank = False
        for ln in lines:
            if ln.strip() == '':
                if not blank:
                    compact.append('')
                blank = True
            else:
                compact.append(ln)
                blank = False
        s = '\n'.join(compact).strip()
        if max_len is not None and max_len > 0:
            s = s[:max_len]
        return s
    except Exception:
        return (text or '')[: max_len or None]



# -------------------- 段落细化清洗：脚注/断词/图注/空白规整 --------------------
REFINE_VERSION = "1.3.0"
OS_PLACEHOLDER = "<<<OS_DATE_PLACEHOLDER>>>"
SIC_PLACEHOLDER = "<<<SIC_PLACEHOLDER>>>"
NARROW_NBSP_GUARD = "<<<NARROW_NBSP>>>"  # U+202F 保护

# 零信息脚注（含全角/中文括号变体）： [e]/[12]、［a］/［12］、【1】 等
FOOTNOTE_RE_ASCII = re.compile(r"\s*\[(?:[a-zA-Z]|\d{1,3})\]\s*")
FOOTNOTE_RE_FULLWIDTH = re.compile(r"\s*[\uFF3B](?:[A-Za-z]|[\uFF10-\uFF19]{1,3})[\uFF3D]\s*")
FOOTNOTE_RE_CORNER = re.compile(r"\s*[\u3010](?:[A-Za-z]|\d{1,3})[\u3011]\s*")
FOOTNOTE_RE_PAREN_NOTE = re.compile(r"\s*（注(?:[0-9０-９]{0,2})）\s*")

# 保护 [O.S. ...] / [sic]（含全角/角括）
PROTECT_OS_SIC = re.compile(r"[\[\uFF3B\u3010]((?:O\.S\.|sic)\s*?[^\]\uFF3D\u3011]+)[\]\uFF3D\u3011]", re.I)

CAPTION_HINT = re.compile(r"\b(class photo|mugshot|first issue of pravda|figcaption)\b", re.I)
STAGE_HINT = re.compile(r"^\[?(music|applause|laughter|silence|inaudible|crosstalk)\]?$", re.I)
TIMESTAMP_HINT = re.compile(r"^\[?(?:\d{1,2}:\d{2}(?::\d{2}(?:,\d{3})?)?)\]?$")

def refine_extracted_text_with_report(s: str) -> tuple[str, Dict[str, Any]]:
    """通用提取后文本清洗，返回 (clean_text, report)。
    规则包含：脚注剔除/保护、空行与空白策略、列表续行、PDF 断词修复、
    CJK 间距、字幕指示与时间戳过滤、可选破折号/引号风格、分节符保留等。
    """
    report: Dict[str, Any] = {
        'eol_normalized': False,
        'leading_trailing_blanks_removed': [0, 0],
        'max_consec_blanks_before': 0,
        'max_consec_blanks_after': 0,
        'tabs_found': 0,
        'nnbsp_found': 0,
        'zw_removed': 0,
        'list_items_detected': 0,
        'list_wrapped_lines': 0,
        'poetry_blocks_preserved': False,
        'hyphenation_joins': 0,
    }

    # 读取环境配置
    def _bool(env: str, default: bool = True) -> bool:
        v = os.getenv(env)
        if v is None:
            return default
        return v.lower() in ('1', 'true', 'yes', 'on')

    NORMALIZE_EOL = _bool('NORMALIZE_EOL', True)
    TRIM_LEADING = _bool('TRIM_LEADING_BLANKS', True)
    TRIM_TRAILING = _bool('TRIM_TRAILING_BLANKS', True)
    PRESERVE_SECTION_BREAKS = _bool('PRESERVE_SECTION_BREAKS', True)
    KEEP_POETRY_LINEBREAKS = _bool('KEEP_POETRY_LINEBREAKS', False)
    KEEP_ZWJ = _bool('KEEP_ZWJ', True)
    KEEP_NNBSP_FOR_UNITS = _bool('KEEP_NNBSP_FOR_UNITS', True)

    try:
        # 0) 统计初始状态
        report['tabs_found'] = s.count('\t')
        report['nnbsp_found'] = s.count('\u00A0') + s.count('\u2007') + s.count('\u202F')
        # 最大连续空行（before）
        report['max_consec_blanks_before'] = max((len(m) for m in re.findall(r'\n{2,}', s)), default=0)

        # 1) EOL 归一
        if NORMALIZE_EOL:
            if ('\r' in s):
                s = s.replace('\r\n', '\n').replace('\r', '\n')
                report['eol_normalized'] = True

        # 2) 去 BOM 与控制字符（保留 \n、\t）
        if s.startswith('\ufeff'):
            s = s.lstrip('\ufeff')
        s = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', s)

        # 3) Tabs → 空格，再合并多空白
        tabw = int(os.getenv('COLLAPSE_TABS', '4') or '4')
        if report['tabs_found'] > 0 and tabw > 0:
            s = s.expandtabs(tabw)

        # 4) 软连字符/零宽字符（保留 ZWJ/LRM/RLM）
        before_len = len(s)
        s = s.replace('\u00AD', '').replace('\u200B', '')
        if not KEEP_ZWJ:
            s = s.replace('\u200D', '')
        report['zw_removed'] = before_len - len(s)

        # 5) 保护 U+202F（数字+单位），其余 NBSP 家族转空格
        PROTECT = '<<<NNBSP_UNIT>>>'
        if KEEP_NNBSP_FOR_UNITS:
            s = re.sub(r'(\d)\u202F(?=\S)', r'\1' + PROTECT, s)
        s = s.replace('\u00A0', ' ').replace('\u2007', ' ').replace('\u202F', ' ')
        s = s.replace(PROTECT, '\u202F')

        # 6) 保护 O.S./sic 变体
        def _protect_os_sic(match: re.Match) -> str:
            inner = match.group(1)
            if inner.lower().startswith('o.s.'):
                return OS_PLACEHOLDER + inner
            return SIC_PLACEHOLDER + inner
        s = PROTECT_OS_SIC.sub(_protect_os_sic, s)

        # 7) 剔除零信息脚注族
        s = FOOTNOTE_RE_ASCII.sub('', s)
        s = FOOTNOTE_RE_FULLWIDTH.sub('', s)
        s = FOOTNOTE_RE_CORNER.sub('', s)
        s = FOOTNOTE_RE_PAREN_NOTE.sub('', s)

        # 8) O.S./sic 还原为括号，缺右括补全
        s = s.replace(OS_PLACEHOLDER, '(')
        s = s.replace(SIC_PLACEHOLDER, '(')
        s = re.sub(r'\(O\.S\.[^\)\n]+', lambda m: m.group(0) + ')', s)
        s = re.sub(r'\(sic[^\)\n]+', lambda m: m.group(0) + ')', s, flags=re.I)

        # 9) 去掉舞台指示/时间戳独立行，标准化说话人
        normalized_lines: list[str] = []
        for ln in (s.split('\n')):
            raw = ln.strip()
            if raw == '':
                normalized_lines.append('')
                continue
            if CAPTION_HINT.search(raw) and len(raw) < 200:
                continue
            if STAGE_HINT.match(raw):
                continue
            if TIMESTAMP_HINT.match(raw):
                continue
            if re.match(r'^[A-Z][A-Z0-9 _-]{1,20}:', raw):
                raw = re.sub(r'^([A-Z][A-Z0-9 _-]{1,20}):', r'**\1:**', raw)
            normalized_lines.append(raw)
        s = '\n'.join(normalized_lines)

        # 10) PDF 断词修复：word-\nwrap → wordwrap
        def _join_hyphen(m: re.Match) -> str:
            report['hyphenation_joins'] += 1
            return m.group(1) + m.group(2)
        s = re.sub(r'([A-Za-z]{2,})-\n([A-Za-z]{2,})', _join_hyphen, s)

        # 11) 行尾空白去除
        s = re.sub(r'[ \t]+\n', '\n', s)

        # 12) 列表续行与项目计数
        lines = s.split('\n')
        out_lines: list[str] = []
        list_item_re = re.compile(r'^\s*(?:[-*+]|\d{1,3}\.)\s+')
        indent_re = re.compile(r'^(\s{2,}).+')
        in_list = False
        current_indent = ''
        for ln in lines:
            if list_item_re.match(ln):
                report['list_items_detected'] += 1
                in_list = True
                m = indent_re.match(ln)
                current_indent = m.group(1) if m else ''
                out_lines.append(ln.rstrip())
                continue
            if in_list and (ln.startswith(current_indent) or ln.startswith('  ')) and not list_item_re.match(ln) and ln.strip() != '':
                # 续行：拼接到上一行
                out_lines[-1] = (out_lines[-1].rstrip() + ' ' + ln.strip())
                report['list_wrapped_lines'] += 1
                continue
            in_list = False
            current_indent = ''
            out_lines.append(ln)
        s = '\n'.join(out_lines)

        # 13) 诗歌/歌词保护（可选）
        if not KEEP_POETRY_LINEBREAKS:
            # 合并段内换行 → 空格
            paragraphs = re.split(r'\n{2,}', s)
            merged: list[str] = []
            for p in paragraphs:
                # 检测短行块
                lines_p = [x for x in p.split('\n') if x.strip() != '']
                short_block = len(lines_p) >= 3 and all(len(x) < 40 and not re.search(r'[。！？.!?]$', x) for x in lines_p)
                if short_block:
                    report['poetry_blocks_preserved'] = True
                    merged.append('\n'.join(lines_p))
                    continue
                one = re.sub(r'[ \t]*\n[ \t]*', ' ', p)
                one = re.sub(r'\s+', ' ', one).strip()
                merged.append(one)
            s = '\n\n'.join([m for m in merged if m])

        # 14) CJK 间距策略
        # 汉字之间不留空格
        s = re.sub(r'([\u4E00-\u9FFF])\s+([\u4E00-\u9FFF])', r'\1\2', s)
        # 汉字与英文/数字之间：auto/none/always
        side = (os.getenv('CJK_SIDE_SPACE') or 'auto').lower()
        if side == 'none':
            s = re.sub(r'([\u4E00-\u9FFF])\s+([A-Za-z0-9])', r'\1\2', s)
            s = re.sub(r'([A-Za-z0-9])\s+([\u4E00-\u9FFF])', r'\1\2', s)
        elif side == 'always':
            s = re.sub(r'([\u4E00-\u9FFF])([A-Za-z0-9])', r'\1 \2', s)
            s = re.sub(r'([A-Za-z0-9])([\u4E00-\u9FFF])', r'\1 \2', s)
        else:  # auto：仅在两侧都是 ASCII 单词边界时保留 1 空格
            s = re.sub(r'([\u4E00-\u9FFF])\s*([A-Za-z0-9])', r'\1 \2', s)
            s = re.sub(r'([A-Za-z0-9])\s*([\u4E00-\u9FFF])', r'\1 \2', s)

        # 15) 句点后双空格 → 单空格
        s = re.sub(r'([.!?。！？])\s{2,}', r'\1 ', s)

        # 16) 分节符保留与统一
        if PRESERVE_SECTION_BREAKS:
            s = re.sub(r'^\s*(?:[-*_]\s*){3,}\s*$', '---', s, flags=re.M)

        # 17) 连续空行压缩
        max_blanks = int(os.getenv('MAX_CONSEC_BLANKS', '1') or '1')
        if max_blanks < 1:
            max_blanks = 1
        # 统计 before→after
        report['max_consec_blanks_before'] = max((len(m) for m in re.findall(r'\n{2,}', s)), default=0)
        s = re.sub(r'\n{'+str(max_blanks+1)+',}', '\n'* (max_blanks+1 - 1 if max_blanks>0 else 1), s)
        report['max_consec_blanks_after'] = max((len(m) for m in re.findall(r'\n{2,}', s)), default=0)

        # 18) 标点风格（破折号/引号）
        dash_style = (os.getenv('TEXT_DASH_STYLE') or '').lower()
        if dash_style == 'hyphen':
            s = s.replace('—', '-').replace('–', '-')
        quote_style = (os.getenv('TEXT_QUOTES_STYLE') or '').lower()
        if quote_style == 'ascii':
            s = (s
                 .replace('“', '"').replace('”', '"')
                 .replace('‘', "'").replace('’', "'"))

        # 19) 还原受保护的窄不换行空格
        s = s.replace(NARROW_NBSP_GUARD, '\u202F')

        # 20) 首尾空行裁剪
        if TRIM_LEADING:
            leading = len(re.match(r'^(\n+)', s).group(1)) if re.match(r'^(\n+)', s) else 0
            if leading:
                report['leading_trailing_blanks_removed'][0] = leading
                s = s.lstrip('\n')
        if TRIM_TRAILING:
            trailing = len(re.search(r'(\n+)$', s).group(1)) if re.search(r'(\n+)$', s) else 0
            if trailing:
                report['leading_trailing_blanks_removed'][1] = trailing
                s = s.rstrip('\n')

        return s.strip(), report
    except Exception:
        return s, report


def refine_extracted_text(s: str) -> str:
    text, _rep = refine_extracted_text_with_report(s)
    return text


def extract_keywords(soup: BeautifulSoup) -> Optional[str]:
    tag = soup.find('meta', attrs={'name': 'keywords'})
    if tag and tag.get('content'):
        return tag['content'][:500]
    return None


def extract_author(soup: BeautifulSoup) -> Optional[str]:
    for selector in [
        ('meta', {'name': 'author'}),
        ('meta', {'property': 'article:author'})
    ]:
        el = soup.find(selector[0], attrs=selector[1])
        if el and el.get('content'):
            return el['content'][:200]
    return None


def extract_published_time(soup: BeautifulSoup) -> Optional[str]:
    # 优先 article:published_time
    el = soup.find('meta', property='article:published_time')
    if el and el.get('content'):
        return el['content']
    # 其次 meta[name=date]
    el = soup.find('meta', attrs={'name': 'date'})
    if el and el.get('content'):
        return el['content']
    # 最后 time[datetime]
    time_tag = soup.find('time')
    if time_tag and time_tag.get('datetime'):
        return time_tag['datetime']
    return None


def extract_lang(soup: BeautifulSoup) -> (Optional[str], Optional[str]):
    # html[lang]
    html_tag = soup.find('html')
    lang = html_tag.get('lang') if html_tag and html_tag.has_attr('lang') else None
    # meta http-equiv content-language
    meta = soup.find('meta', attrs={'http-equiv': lambda v: v and v.lower() == 'content-language'})
    content_lang = meta.get('content') if meta and meta.get('content') else None
    return (lang, content_lang)


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
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8',
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
            response = await client.get(url, headers=headers, follow_redirects=True)
            
            # 内容类型预检查 - 确保是文本类型
            content_type = response.headers.get("Content-Type", "").lower()
            if not any(ct in content_type for ct in ["text/html", "application/xhtml+xml", "application/json", "text/"]):
                if "application/pdf" in content_type:
                    raise ValueError(f"PDF content detected: {content_type}")
                elif any(ct in content_type for ct in ["image/", "video/", "audio/"]):
                    raise ValueError(f"Non-text content: {content_type}")
            
            return response
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
        async with httpx.AsyncClient(http2=True, timeout=15.0, proxies=_get_proxies()) as client:
            resp = await _get_with_retries(client, url, max_retries=2, base_delay=0.6)
            resp.raise_for_status()

            status_code = resp.status_code
            final_url = str(resp.url)
            content_type = (resp.headers.get('content-type') or '').lower()
            html: Optional[str] = None
            text: Optional[str] = None
            blocked_reason: Optional[str] = None
            refine_report: Optional[Dict[str, Any]] = None
            use_curator_primary = (os.getenv('CURATOR_PRIMARY', 'true').lower() in ('1', 'true', 'yes', 'on'))

            # 防乱码/二进制：若声明 text/* 但 body 看起来像压缩或二进制，尝试解压后再解码
            try:
                raw_bytes = resp.content or b''
                safe_bytes = _maybe_decompress(raw_bytes)
                header_charset = None
                if 'charset=' in content_type:
                    try:
                        header_charset = content_type.split('charset=')[-1].split(';')[0].strip()
                    except Exception:
                        header_charset = None
                if (content_type.startswith('text/') or 'html' in content_type):
                    as_text, used = _decode_bytes_safely(safe_bytes, header_charset)
                    resp_text_override = as_text
                else:
                    resp_text_override = None
            except Exception:
                resp_text_override = None

            # 类型判断
            # Wikipedia 专用：直接走 Action API plaintext，获取原文
            host_lower = urlparse(url).netloc.lower()
            if 'wikipedia.org' in host_lower:
                try:
                    path = urlparse(url).path
                    title_part = path.split('/wiki/', 1)[1] if '/wiki/' in path else None
                    lang = host_lower.split('.')[0] if host_lower.count('.') >= 2 else 'en'
                    if title_part:
                        api_plain = (
                            f"https://{lang}.wikipedia.org/w/api.php?"
                            f"action=query&prop=extracts&explaintext=1&format=json&titles="
                            f"{quote(title_part, safe='')}"
                        )
                        r2 = await _get_with_retries(client, api_plain)
                        r2.raise_for_status()
                        data2 = r2.json() or {}
                        pages = (data2.get('query') or {}).get('pages') or {}
                        extracted_text = ''
                        if isinstance(pages, dict):
                            for _pid, page_obj in pages.items():
                                if isinstance(page_obj, dict) and isinstance(page_obj.get('extract'), str):
                                    extracted_text = page_obj.get('extract') or ''
                                    break
                        if extracted_text:
                            max_len = int(os.getenv('PAGE_TEXT_MAX_LEN', '120000') or '120000')
                            refined, rep = refine_extracted_text_with_report(extracted_text)
                            text = _normalize_text(refined, max_len=max_len)
                            refine_report = rep
                except Exception:
                    pass

            if ('text/html' in content_type) or (content_type.startswith('application/xhtml')) or (content_type == ''):
                html = (resp_text_override if resp_text_override is not None else resp.text) or None
                if use_curator_primary:
                    try:
                        curated = apply_curator(html=html, text=None)
                    except Exception:
                        curated = None
                    if curated and (curated.get('curated_text') or '').strip() != '':
                        text = curated.get('curated_text')
                        refine_report = (refine_report or {})
                        refine_report['curation_info'] = curated.get('curation_info')
                    else:
                        # Curator 未产出内容时，作为最后的兜底，做极简提取
                        try:
                            soup = BeautifulSoup(html or '', 'html.parser')
                            for tag in soup(['script', 'style', 'noscript']):
                                tag.decompose()
                            extracted_text = soup.get_text('\n', strip=True)
                            max_len = int(os.getenv('PAGE_TEXT_MAX_LEN', '120000') or '120000')
                            text = _normalize_text(extracted_text, max_len=max_len)
                        except Exception:
                            text = None
                else:
                    # 旧路径（保留回退）：Readability → 净化 → 规范化
                    article_html: Optional[str] = None
                    try:
                        doc = Document(html or '')
                        article_html = doc.summary()
                    except Exception:
                        article_html = None

                    if article_html:
                        try:
                            cleaned_html = _sanitize_html(article_html)
                            article_soup = BeautifulSoup(cleaned_html, 'html.parser')
                            extracted_text = article_soup.get_text('\n', strip=True)
                            if extracted_text:
                                max_len = int(os.getenv('PAGE_TEXT_MAX_LEN', '120000') or '120000')
                                refined, rep = refine_extracted_text_with_report(extracted_text)
                                text = _normalize_text(refined, max_len=max_len)
                                refine_report = rep
                            html = cleaned_html
                        except Exception:
                            text = None
                    else:
                        try:
                            soup = BeautifulSoup(html or '', 'html.parser')
                            for tag in soup(['script', 'style', 'noscript']):
                                tag.decompose()
                            main = soup.find('article') or soup.find(attrs={'role': 'main'}) or soup.find(id='main')
                            target = main if main else soup.body or soup
                            cleaned_html = _sanitize_html(str(target))
                            target_soup = BeautifulSoup(cleaned_html, 'html.parser')
                            extracted_text = target_soup.get_text(separator='\n', strip=True)
                            if extracted_text:
                                max_len = int(os.getenv('PAGE_TEXT_MAX_LEN', '120000') or '120000')
                                refined, rep = refine_extracted_text_with_report(extracted_text)
                                text = _normalize_text(refined, max_len=max_len)
                                refine_report = rep
                            html = cleaned_html
                            page_title = (soup.title.string or '').strip() if soup.title and soup.title.string else ''
                            if 'Just a moment' in page_title or 'Cloudflare' in page_title or 'cf-challenge' in (html or '') or 'Attention Required!' in page_title:
                                blocked_reason = 'cloudflare_challenge'
                        except Exception:
                            text = None
            elif content_type.startswith('text/'):
                # 纯文本资源
                raw_text = ((resp_text_override if resp_text_override is not None else resp.text) or '')[:50000]
                if use_curator_primary:
                    try:
                        curated = apply_curator(html=None, text=raw_text)
                    except Exception:
                        curated = None
                    if curated and (curated.get('curated_text') or '').strip() != '':
                        text = curated.get('curated_text')
                        refine_report = (refine_report or {})
                        refine_report['curation_info'] = curated.get('curation_info')
                    else:
                        max_len = int(os.getenv('PAGE_TEXT_MAX_LEN', '120000') or '120000')
                        refined, rep = refine_extracted_text_with_report(raw_text)
                        text = _normalize_text(refined, max_len=max_len)
                        refine_report = rep
                else:
                    refined, rep = refine_extracted_text_with_report(raw_text)
                    text = _normalize_text(refined, max_len=int(os.getenv('PAGE_TEXT_MAX_LEN', '120000') or '120000'))
                    refine_report = rep
                html = None
            else:
                # PDF: application/pdf 或 URL 以 .pdf 结尾
                if ('application/pdf' in content_type) or (str(resp.url).lower().endswith('.pdf')):
                    try:
                        if pdf_extract_text:
                            # 直接用响应内容写入内存文件并提取
                            raw = resp.content or b''
                            # pdfminer 接口对 bytes 直接支持有限，这里写临时文件更稳
                            import tempfile
                            with tempfile.NamedTemporaryFile(suffix='.pdf') as tf:
                                tf.write(raw)
                                tf.flush()
                                pdf_text = pdf_extract_text(tf.name) or ''
                            max_len = int(os.getenv('PAGE_TEXT_MAX_LEN', '120000') or '120000')
                            refined, rep = refine_extracted_text_with_report(pdf_text)
                            text = _normalize_text(refined, max_len=max_len)
                            refine_report = rep
                            html = None
                        else:
                            text = None
                            html = None
                    except Exception:
                        html = None
                        text = None
                else:
                    # 其他二进制/富媒体，不处理
                    html = None
                    text = None

            # YouTube 字幕抓取（仅当 URL 属于 youtube 且开启）
            try:
                if os.getenv('YOUTUBE_TRANSCRIPT_ENABLED', '').lower() in ('1', 'true', 'yes'):
                    vid = _extract_youtube_id(url)
                    _dbg(f"yt check url={url} vid={vid}")
                    if vid and YouTubeTranscriptApi:
                        transcript_text = await _fetch_youtube_transcript_async(vid)
                        if transcript_text:
                            max_len = int(os.getenv('PAGE_TEXT_MAX_LEN', '120000') or '120000')
                            refined_tr, _ = refine_extracted_text_with_report(transcript_text)
                            norm_tr = _normalize_text(refined_tr, max_len=max_len)
                            text = (text + '\n\n' if text else '') + norm_tr
                            _dbg(f"yt transcript appended len={len(norm_tr)}")
                        else:
                            _dbg("yt transcript not available")
                    elif YouTubeTranscriptApi is None:
                        _dbg("yt transcript api not installed")
            except Exception as yt_exc:
                _dbg(f"yt transcript error: {yt_exc}")

            # 末尾兜底：若未启用主清洗或前面未产出内容，再尝试一次 Curator
            if not use_curator_primary:
                try:
                    curated = apply_curator(html=html, text=text)
                except Exception:
                    curated = None
                if curated and (curated.get('curated_text') or '').strip() != '':
                    text = curated.get('curated_text')
                    if refine_report is None:
                        refine_report = {}
                    refine_report['curation_info'] = curated.get('curation_info')

            # Sumy 内容预处理：提取关键段落
            sumy_processing_info = None
            if text and SUMY_PREPROCESSING_AVAILABLE and _sumy_preprocessing_enabled():
                try:
                    _dbg(f"开始 Sumy 内容预处理，原文本长度: {len(text)}")
                    
                    # 获取 Sumy 配置
                    max_sentences = int(os.getenv('SUMY_MAX_SENTENCES', '8') or '8')
                    top_k_paragraphs = int(os.getenv('SUMY_TOP_K_PARAGRAPHS', '4') or '4')
                    context_window = int(os.getenv('SUMY_CONTEXT_WINDOW', '1') or '1')
                    algorithm = os.getenv('SUMY_ALGORITHM', 'lexrank').lower()
                    preserve_mode = os.getenv('SUMY_PRESERVE_MODE', 'balanced').lower()
                    
                    sumy_result = extract_key_content_with_sumy(
                        text=text,
                        max_sentences=max_sentences,
                        top_k_paragraphs=top_k_paragraphs,
                        context_window=context_window,
                        algorithm=algorithm,
                        preserve_mode=preserve_mode
                    )
                    
                    if sumy_result and sumy_result.get('processed_text'):
                        processed_text = sumy_result['processed_text'].strip()
                        if processed_text:
                            _dbg(f"Sumy 预处理成功: {sumy_result.get('original_length')} → {sumy_result.get('processed_length')} "
                                f"(压缩率: {sumy_result.get('compression_ratio', 0):.2%}, 模式: {preserve_mode})")
                            text = processed_text
                            sumy_processing_info = {
                                'applied': True,
                                'method': sumy_result.get('method'),
                                'algorithm': sumy_result.get('algorithm'),
                                'preserve_mode': sumy_result.get('preserve_mode'),
                                'compression_ratio': sumy_result.get('compression_ratio'),
                                'paragraphs_count': sumy_result.get('paragraphs_count'),
                                'key_sentences_count': sumy_result.get('key_sentences_count'),
                                'key_sentences': sumy_result.get('key_sentences', [])  # 保存关键句子
                            }
                        else:
                            _dbg("Sumy 预处理结果为空，保持原文本")
                    else:
                        _dbg("Sumy 预处理未产出结果，保持原文本")
                        
                except Exception as sumy_err:
                    _dbg(f"Sumy 预处理失败: {sumy_err}")
                    # 保持原文本不变
                    
            if sumy_processing_info is None:
                sumy_processing_info = {'applied': False, 'reason': 'disabled_or_unavailable'}

            # 全局策略：不再返回 HTML 内容
            html = None

            return {
                'html': html,
                'text': text,
                'content_type': content_type,
                'extracted_at': datetime.utcnow().isoformat(),
                'status_code': status_code,
                'final_url': final_url,
                'blocked_reason': blocked_reason,
                'refine_version': REFINE_VERSION,
                'refine_report': refine_report,
                'sumy_processing': sumy_processing_info,
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


def _extract_youtube_id(url: str) -> Optional[str]:
    try:
        u = urlparse(url)
        host = (u.netloc or '').lower()
        path = (u.path or '')
        # 支持多个域：
        if any(h in host for h in ['youtube.com', 'youtube-nocookie.com', 'm.youtube.com', 'music.youtube.com']):
            qs = parse_qs(u.query or '')
            if 'v' in qs and qs['v']:
                return qs['v'][0]
            # /embed/{id}、/shorts/{id}、/live/{id}、/v/{id}
            parts = [p for p in path.split('/') if p]
            for marker in ('embed', 'shorts', 'live', 'v'):
                if marker in parts:
                    idx = parts.index(marker)
                    if idx + 1 < len(parts):
                        return parts[idx + 1]
            # attribution_link 路径中带 url 编码的 watch?v=
            if 'attribution_link' in path and 'u=' in (u.query or ''):
                u_param = parse_qs(u.query).get('u', [None])[0]
                if u_param:
                    inner = urlparse(unquote(u_param))
                    inner_q = parse_qs(inner.query or '')
                    if 'v' in inner_q and inner_q['v']:
                        return inner_q['v'][0]
        if 'youtu.be' in host:
            parts = [p for p in path.split('/') if p]
            return parts[0] if parts else None
        return None
    except Exception:
        return None


async def _fetch_youtube_transcript_async(video_id: str) -> Optional[str]:
    try:
        if not YouTubeTranscriptApi:
            return None
        # 同步库，直接调用（可按需放线程池）
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        env_langs = os.getenv('YOUTUBE_TRANSCRIPT_LANGS', 'zh-Hans,zh,zh-CN,zh-TW,en')
        preferred_langs = [l.strip() for l in env_langs.split(',') if l.strip()]
        transcript = None
        # 直接匹配优先语言
        try:
            transcript = transcripts.find_transcript(preferred_langs)
        except Exception:
            transcript = None
        # 退而求其次：任意可用字幕
        if not transcript:
            try:
                all_list = list(transcripts)
                transcript = all_list[0] if all_list else None
            except Exception:
                transcript = None
        if not transcript:
            _dbg("yt transcript none for video")
            return None
        # 若语言不在首选且可翻译，尝试翻译
        if (transcript.language_code not in preferred_langs) and (os.getenv('YOUTUBE_TRANSCRIPT_TRANSLATE', '').lower() in ('1', 'true', 'yes')):
            try:
                target = preferred_langs[0] if preferred_langs else 'en'
                if getattr(transcript, 'is_translatable', False):
                    transcript = transcript.translate(target)
            except Exception as tr_exc:
                _dbg(f"yt translate fail: {tr_exc}")
        data = transcript.fetch()
        text = '\n'.join([seg.get('text', '') for seg in data if seg.get('text')])
        _dbg(f"yt transcript fetched len={len(text)} lang={getattr(transcript,'language_code','?')}")
        return text
    except Exception:
        return None


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



# -------------------- 内容探测与解压/二进制判定 --------------------
def _looks_binary(buf: bytes, sample: int = 2048) -> bool:
    try:
        s = buf[:sample] if buf else b''
        if not s:
            return False
        nontext = 0
        for ch in s:
            # 常见控制字符且非 \n/\r/\t
            if ch == 0x00 or (ch < 9) or (13 < ch < 32):
                nontext += 1
        return (nontext / max(1, len(s))) > 0.3
    except Exception:
        return False


def _maybe_decompress(buf: bytes) -> bytes:
    try:
        if not buf:
            return buf
        if buf.startswith(b"\x1f\x8b"):
            try:
                return gzip.decompress(buf)
            except Exception:
                return buf
        if buf.startswith(b"BZh"):
            try:
                return bz2.decompress(buf)
            except Exception:
                return buf
        # 尝试 brotli（若环境可用且可解压）
        try:
            import brotli  # type: ignore
            try:
                return brotli.decompress(buf)
            except Exception:
                pass
        except Exception:
            pass
        return buf
    except Exception:
        return buf


def _extract_charset_from_meta(html_snippet: str) -> Optional[str]:
    try:
        m = re.search(r'<meta[^>]+charset\s*=\s*(["\']?)([^\s"\'>/;]+)\1', html_snippet, re.I)
        if m:
            return m.group(2).strip()
        m2 = re.search(r'<meta[^>]+http-equiv\s*=\s*(["\']?)content-type\1[^>]*content\s*=\s*(["\'])([^\2]+?)\2', html_snippet, re.I)
        if m2:
            ct = m2.group(3)
            m3 = re.search(r'charset\s*=\s*([^\s;]+)', ct, re.I)
            if m3:
                return m3.group(1).strip()
        return None
    except Exception:
        return None


def _replacement_ratio(s: str) -> float:
    try:
        if not s:
            return 0.0
        bad = s.count('\uFFFD')
        return bad / max(1, len(s))
    except Exception:
        return 0.0


def _decode_bytes_safely(buf: bytes, header_charset: Optional[str] = None) -> tuple[str, str]:
    """鲁棒解码：报头→meta→charset-normalizer→chardet→常见编码回退。返回 (text, encoding)。"""
    tried: set[str] = set()
    # 报头
    if header_charset:
        enc = header_charset.strip().lower()
        try:
            txt = buf.decode(enc, errors='replace')
            if _replacement_ratio(txt) < 0.02:
                return txt, enc
            tried.add(enc)
        except Exception:
            tried.add(enc)
    # meta
    try:
        head = buf[:4096].decode('latin-1', errors='ignore')
        meta_enc = _extract_charset_from_meta(head)
        if meta_enc and meta_enc.lower() not in tried:
            try:
                txt = buf.decode(meta_enc, errors='replace')
                if _replacement_ratio(txt) < 0.02:
                    return txt, meta_enc
                tried.add(meta_enc.lower())
            except Exception:
                tried.add(meta_enc.lower())
    except Exception:
        pass
    # charset-normalizer
    try:
        from charset_normalizer import from_bytes  # type: ignore
        res = from_bytes(buf).best()
        if res and res.encoding and res.encoding.lower() not in tried:
            enc = res.encoding
            try:
                txt = buf.decode(enc, errors='replace')
                if _replacement_ratio(txt) < 0.03:
                    return txt, enc
                tried.add(enc.lower())
            except Exception:
                tried.add(enc.lower())
    except Exception:
        pass
    # chardet
    try:
        import chardet  # type: ignore
        det = chardet.detect(buf)
        enc = (det.get('encoding') or '').lower()
        if enc and enc not in tried:
            try:
                txt = buf.decode(enc, errors='replace')
                if _replacement_ratio(txt) < 0.04:
                    return txt, enc
                tried.add(enc)
            except Exception:
                tried.add(enc)
    except Exception:
        pass
    # 常见回退
    for enc in ['utf-8', 'gb18030', 'latin-1']:
        if enc in tried:
            continue
        try:
            txt = buf.decode(enc, errors='replace')
            return txt, enc
        except Exception:
            continue
    return (buf.decode('utf-8', errors='replace'), 'utf-8')

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
