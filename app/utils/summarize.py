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

        snippet = text.strip()
        if len(snippet) > input_limit:
            snippet = snippet[:input_limit]

        prompt_system = (
            "You are a concise summarization assistant. Provide a 2-4 sentence summary "
            "capturing the key points only. Exclude navigation, table of contents, and ads. "
            "If the text is not natural language prose (e.g., code/logs/noise), summarize its topic or purpose. "
            "Always write the summary in the same language as the input."
        )
        prompt_user = f"Summarize the following content in the same language as the input.\n\n{snippet}"

        if provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            base_url = os.getenv('OPENAI_BASE_URL') or 'https://api.openai.com/v1'
            if not api_key:
                logger.debug('summary: OPENAI_API_KEY 未配置，跳过摘要')
                return None
            payload = {
                'model': model,
                'messages': [
                    {'role': 'system', 'content': prompt_system},
                    {'role': 'user', 'content': prompt_user},
                ],
                'temperature': 0.3,
                'max_tokens': max_tokens,
            }
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            }
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    choices = data.get('choices') or []
                    if not choices:
                        return None
                    content = choices[0].get('message', {}).get('content')
                    if content:
                        return content.strip()
                    return None
            except Exception as e:
                logger.warning(f'summary 请求失败：{e}')
                return None

        # 其他 provider 可在此扩展
        return None
    except Exception as e:
        logger.warning(f'summary 生成失败：{e}')
        return None


