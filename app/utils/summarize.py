from typing import Optional
import os
import logging
import httpx

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
    - SUMMARY_MAX_TOKENS: 输出上限（默认 220）
    - SUMMARY_INPUT_CHAR_LIMIT: 输入截断（默认 12000）
    """
    try:
        if not _enabled():
            return None

        if not text or len(text.strip()) == 0:
            return None

        provider = (os.getenv('SUMMARY_PROVIDER') or 'openai').lower()
        model = os.getenv('SUMMARY_MODEL') or 'gpt-5-nano'
        max_tokens = int(os.getenv('SUMMARY_MAX_TOKENS', '220') or '220')
        input_limit = int(os.getenv('SUMMARY_INPUT_CHAR_LIMIT', '12000') or '12000')
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
            "You are a concise summarization assistant. Provide a 2-4 sentence summary "
            "capturing the key points only. Exclude navigation, table of contents, and ads. "
            "If the text is not natural language prose (e.g., code/logs/noise), summarize its topic or purpose. "
            "Always write the summary in the same language as the input."
        )
        prompt_user = "Summarize the following content in the same language as the input."

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
                payload = {
                    'model': mdl,
                    'messages': [
                        {'role': 'system', 'content': prompt_system},
                        {'role': 'user', 'content': f"{prompt_user}\n\n{snip}"},
                    ],
                    'max_tokens': max_tokens,
                }
                if temp_value is not None:
                    payload['temperature'] = temp_value
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
                    content = choices[0].get('message', {}).get('content')
                    content_out = content.strip() if content else None
                    logger.info(f"summary: 调用成功，返回长度={len(content_out) if content_out else 0}")
                    return content_out

            # Map-Reduce 摘要：过长文本分块 → 分块摘要 → 汇总摘要
            chunks = _split_into_chunks(raw, min(chunk_limit, input_limit))
            if len(chunks) > max_chunks:
                chunks = chunks[:max_chunks]

            if len(chunks) == 1:
                return await _call_once(chunks[0], model)

            partial_summaries: list[str] = []
            for ch in chunks:
                one = await _call_once(ch, model)
                if one:
                    partial_summaries.append(one)
            if not partial_summaries:
                return None

            combined = "\n\n".join(partial_summaries)
            if len(combined) > input_limit:
                combined = combined[:input_limit]
            final_prompt = (
                "Summarize the following bullet summaries into a single concise 2-4 sentence summary, "
                "keeping the same language as the input.\n\n" + combined
            )
            return await _call_once(final_prompt, model)

        # 其他 provider 可在此扩展
        return None
    except Exception as e:
        logger.warning(f'summary 生成失败：{e}')
        return None


