from typing import Optional
import os
import logging
import httpx
import re

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    try:
        return (os.getenv('SUMMARY_ENABLED', '').lower() in ('1', 'true', 'yes', 'on'))
    except Exception:
        return False


async def generate_summary(text: str) -> Optional[str]:
    """调用轻量 LLM 生成摘要。未配置或失败时返回 None。

    环境变量：
    - SUMMARY_ENABLED: 开关
    - SUMMARY_PROVIDER: 默认 'openai'
    - SUMMARY_MODEL: 默认 'gpt-5-nano'（可替换为兼容模型）
    - OPENAI_API_KEY / OPENAI_BASE_URL: 兼容 OpenAI 风格接口
    - SUMMARY_MAX_TOKENS: 输出上限（默认 1200）
    - SUMMARY_INPUT_CHAR_LIMIT: 输入截断（默认 16000）
    """
    try:
        if not _enabled():
            return None

        if not text or len(text.strip()) == 0:
            return None

        provider = (os.getenv('SUMMARY_PROVIDER') or 'openai').lower()
        model = os.getenv('SUMMARY_MODEL') or 'gpt-5-nano'
        max_tokens = int(os.getenv('SUMMARY_MAX_TOKENS', '1200') or '1200')
        input_limit = int(os.getenv('SUMMARY_INPUT_CHAR_LIMIT', '16000') or '16000')
        chunk_limit = int(os.getenv('SUMMARY_CHUNK_CHAR_LIMIT', '4000') or '4000')
        max_chunks = int(os.getenv('SUMMARY_MAX_CHUNKS', '8') or '8')

        raw = text.strip()
        if len(raw) == 0:
            return None

        # 简单分段切块（优先按空行分段）
        def _split_into_chunks(s: str, limit: int) -> list[str]:
            s = s.strip()
            if len(s) <= limit:
                return [s]
            parts = [p for p in s.split('\n\n') if p.strip()]
            chunks: list[str] = []
            buf: list[str] = []
            cur_len = 0
            for p in parts:
                p2 = p.strip()
                if not p2:
                    continue
                if cur_len + len(p2) + (2 if buf else 0) <= limit:
                    buf.append(p2)
                    cur_len += len(p2) + (2 if buf else 0)
                else:
                    if buf:
                        chunks.append('\n\n'.join(buf))
                    if len(p2) <= limit:
                        buf = [p2]
                        cur_len = len(p2)
                    else:
                        # 段落本身过长，硬切
                        for i in range(0, len(p2), limit):
                            chunks.append(p2[i:i+limit])
                        buf = []
                        cur_len = 0
            if buf:
                chunks.append('\n\n'.join(buf))
            return chunks

        prompt_system = (
            "You are a neutral, concise summarization assistant.\n\n"
            "Always produce a usable summary (never return an empty string).\n"
            "If any content is sensitive or disallowed, replace only that portion with bracketed placeholders "
            "(e.g., ‘[redacted PII]’, ‘[political content omitted]’) and continue summarizing the rest.\n\n"
            "Rules:\n"
            "1) Target length: 2–4 sentences (or 3–6 short bullets if the source is highly structured).\n"
            "2) Keep the original language of the input (do not translate).\n"
            "3) Extract facts and key points; avoid opinions, speculation, or new claims.\n"
            "4) Exclude navigation, headers/footers, boilerplate, ads, cookie banners, and comments.\n"
            "5) For code/logs/configs, summarize purpose, main components, and notable issues.\n"
            "6) Redact PII (emails, phone numbers, addresses, IDs) and sensitive details as placeholders, but do not drop the entire summary.\n"
            "7) If the text is mostly noise or unreadable, output one sentence explaining it is noisy plus any clearly identifiable topic.\n"
            "8) Return plain text only."
        )
        prompt_user = "Summarize the following content accordingly:"

        if provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            base_url = os.getenv('OPENAI_BASE_URL') or 'https://api.openai.com/v1'
            org = os.getenv('OPENAI_ORGANIZATION')
            project = os.getenv('OPENAI_PROJECT')
            temp_env = os.getenv('SUMMARY_TEMPERATURE')
            temp_value = None
            try:
                if temp_env is not None and temp_env != '':
                    temp_value = float(temp_env)
            except Exception:
                temp_value = None
            if not api_key:
                logger.debug('summary: OPENAI_API_KEY 未配置，跳过摘要')
                return None
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }
            if org:
                headers['OpenAI-Organization'] = org
            if project:
                headers['OpenAI-Project'] = project

            async def _call_once(snip: str, mdl: str) -> Optional[str]:
                # 默认使用新版参数名，部分模型仅支持其中之一
                payload = {
                    'model': mdl,
                    'messages': [
                        {'role': 'system', 'content': prompt_system},
                        {'role': 'user', 'content': f"{prompt_user}\n\n{snip}"},
                    ],
                    'max_completion_tokens': max_tokens,
                }
                if temp_value is not None:
                    payload['temperature'] = temp_value
                # 可选开启强制文本输出
                try:
                    if (os.getenv('SUMMARY_RESPONSE_FORMAT_TEXT', '').lower() in ('1', 'true', 'yes', 'on')):
                        payload['response_format'] = {'type': 'text'}
                except Exception:
                    pass
                async with httpx.AsyncClient(timeout=20.0) as client:
                    try:
                        resp = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
                        resp.raise_for_status()
                    except httpx.HTTPStatusError as he:
                        body = None
                        try:
                            body = he.response.text[:500]
                        except Exception:
                            body = None
                        logger.warning(f"summary 请求失败：{he} body={body}")
                        # temperature 不被支持时，移除后重试一次
                        if body and 'temperature' in body:
                            payload.pop('temperature', None)
                            try:
                                resp = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
                                resp.raise_for_status()
                            except Exception:
                                pass
                            else:
                                data = resp.json()
                                choices = data.get('choices') or []
                                if choices:
                                    content = choices[0].get('message', {}).get('content')
                                    return content.strip() if content else None
                        # 保持只使用 max_completion_tokens，不做参数名切换
                        fb_model = os.getenv('SUMMARY_FALLBACK_MODEL')
                        if fb_model and fb_model != mdl:
                            try:
                                resp = await client.post(f"{base_url}/chat/completions", json={**payload, 'model': fb_model}, headers=headers)
                                resp.raise_for_status()
                            except Exception:
                                return None
                        else:
                            return None
                    data = resp.json()
                    choices = data.get('choices') or []
                    if not choices:
                        logger.warning('summary: choices 为空')
                        return None
                    choice0 = choices[0]
                    message = choice0.get('message', {})
                    finish_reason = choice0.get('finish_reason')
                    usage = data.get('usage') or {}
                    completion_tokens = usage.get('completion_tokens')
                    fingerprint = data.get('system_fingerprint')
                    refusal = message.get('refusal')
                    annotations = message.get('annotations')
                    # 打印 message 结构与预览，帮助排查 content 为空的原因
                    try:
                        msg_preview = str(message)[:400]
                        logger.info(
                            f"summary: finish_reason={finish_reason}, completion_tokens={completion_tokens}, "
                            f"fingerprint={fingerprint}, refusal={'Y' if refusal else 'N'}, "
                            f"annotations_len={len(annotations) if isinstance(annotations, list) else 'NA'}; "
                            f"message_keys={list(message.keys())}, preview={msg_preview}"
                        )
                    except Exception:
                        pass
                    content = message.get('content')
                    content_out = content.strip() if content else None
                    
                    # 检查 finish_reason 并提供详细日志
                    if finish_reason == 'length':
                        logger.warning(f"summary: 输出被长度截断，考虑增加 max_completion_tokens (当前={max_tokens})")
                    elif finish_reason == 'content_filter':
                        logger.warning("summary: 内容被过滤器拦截，可能包含敏感内容")
                    elif not content_out:
                        logger.warning(f"summary: 空输出，finish_reason={finish_reason}, completion_tokens={completion_tokens}")
                    
                    logger.info(f"summary: 调用成功，返回长度={len(content_out) if content_out else 0}, preview={(content_out[:200] if content_out else '')}")
                    return content_out

            async def _call_once_strict(snip: str, mdl: str) -> Optional[str]:
                """更强提示，避免空输出。"""
                strict_system = (
                    "You are a summarization assistant. Provide a clear, concise summary in 2-4 sentences. "
                    "Focus on the main points and key information. Use plain text format."
                )
                payload = {
                    'model': mdl,
                    'messages': [
                        {'role': 'system', 'content': strict_system},
                        {'role': 'user', 'content': f"Summarize in plain text only (2-4 sentences):\n\n{snip}"},
                    ],
                    'max_completion_tokens': max_tokens,
                }
                if temp_value is not None:
                    payload['temperature'] = temp_value
                try:
                    if (os.getenv('SUMMARY_RESPONSE_FORMAT_TEXT', '').lower() in ('1', 'true', 'yes', 'on')):
                        payload['response_format'] = {'type': 'text'}
                except Exception:
                    pass
                async with httpx.AsyncClient(timeout=20.0) as client:
                    try:
                        resp = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
                        resp.raise_for_status()
                    except Exception as e:
                        logger.warning(f"summary(strict) 请求失败：{e}")
                        return None
                    data = resp.json()
                    choices = data.get('choices') or []
                    if not choices:
                        return None
                    choice0 = choices[0]
                    message = choice0.get('message', {})
                    finish_reason = choice0.get('finish_reason')
                    usage = data.get('usage') or {}
                    completion_tokens = usage.get('completion_tokens')
                    fingerprint = data.get('system_fingerprint')
                    refusal = message.get('refusal')
                    annotations = message.get('annotations')
                    try:
                        msg_preview = str(message)[:400]
                        logger.info(
                            f"summary(strict): finish_reason={finish_reason}, completion_tokens={completion_tokens}, "
                            f"fingerprint={fingerprint}, refusal={'Y' if refusal else 'N'}, "
                            f"annotations_len={len(annotations) if isinstance(annotations, list) else 'NA'}; "
                            f"message_keys={list(message.keys())}, preview={msg_preview}"
                        )
                    except Exception:
                        pass
                    content = message.get('content')
                    content_out = content.strip() if content else None
                    
                    # 检查 finish_reason
                    if finish_reason == 'length':
                        logger.warning(f"summary(strict): 输出被长度截断，考虑增加 max_completion_tokens (当前={max_tokens})")
                    elif finish_reason == 'content_filter':
                        logger.warning("summary(strict): 内容被过滤器拦截")
                    elif not content_out:
                        logger.warning(f"summary(strict): 空输出，finish_reason={finish_reason}, completion_tokens={completion_tokens}")
                    
                    return content_out

            def _extractive_fallback(snip: str) -> str:
                """抽取式兜底：取前两句或前 240 字。"""
                s = snip.strip()
                if not s:
                    return ''
                # 按中英文句末分割，再取前两段
                parts = re.split(r"(?<=[。！？.!?])\s+", s)
                out = ''.join(parts[:2]).strip()
                if not out:
                    out = s[:240]
                return out[:240]

            # 简化：不做分段与汇总，直接对截断文本单次生成；失败→严格重试→抽取式兜底
            single = raw[:input_limit]
            first = await _call_once(single, model)
            if first and first.strip():
                return first
            second = await _call_once_strict(single, model)
            if second and second.strip():
                return second
            fb = _extractive_fallback(single)
            return fb if fb else None

        # 其他 provider 可在此扩展
        return None
    except Exception as e:
        logger.warning(f'summary 生成失败：{e}')
        return None


