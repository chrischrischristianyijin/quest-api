from typing import Optional, Dict, Any, List
import os
import logging
import re

logger = logging.getLogger(__name__)


def _is_enabled() -> bool:
    try:
        return (os.getenv('CURATOR_ENABLED', '').lower() in ('1', 'true', 'yes', 'on'))
    except Exception:
        return False


def _parse_langs(default: str = 'zh,en') -> List[str]:
    try:
        raw = os.getenv('CURATOR_LANGS', default)
        return [x.strip() for x in (raw or '').split(',') if x.strip()]
    except Exception:
        return [x.strip() for x in default.split(',') if x.strip()]


def _get_numbers(env_name: str, default: float) -> float:
    try:
        v = os.getenv(env_name)
        if v is None:
            return default
        return float(v)
    except Exception:
        return default


def apply_curator(html: Optional[str], text: Optional[str]) -> Optional[Dict[str, Any]]:
    """使用 NeMo Curator 对 html/text 进行清洗与过滤。

    返回 None 表示未启用或不可用；否则返回：
    { curated_text: str, chunks: list[dict], curation_info: dict }
    """
    try:
        if not _is_enabled():
            return None

        try:
            from nemo_curator.cleaners import PIIRedactor  # type: ignore
            from nemo_curator.filters import HeuristicFilter, LanguageFilter, FastTextQualityClassifier  # type: ignore
            from nemo_curator.splitters import SentenceSplitter, TokenTextSplitter  # type: ignore
        except Exception as imp_err:
            try:
                if (os.getenv('CURATOR_STRICT', '').lower() in ('1', 'true', 'yes', 'on')):
                    logger.warning(f"NeMo Curator 未安装或不可用，将跳过清洗：{imp_err}")
                else:
                    logger.debug(f"NeMo Curator 未安装或不可用（已静默跳过）：{imp_err}")
            except Exception:
                pass
            return None

        # 源端已完成正文抽取与基础清洗；此处只做标准化后半段
        doc: Dict[str, Any] = {"id": "inline", "text": (text or '')}

        # 2.5) 精确去重（段落级），可开关
        try:
            if os.getenv('CURATOR_EXACT_DEDUP', 'true').lower() in ('1', 'true', 'yes', 'on'):
                before_text = doc.get('text') or ''
                paragraphs = re.split(r"\n{2,}", before_text)
                seen_keys: set[str] = set()
                deduped: List[str] = []
                removed_paras = 0
                for p in paragraphs:
                    key = re.sub(r"\s+", " ", p).strip().lower()
                    if not key:
                        continue
                    if key in seen_keys:
                        removed_paras += 1
                        continue
                    seen_keys.add(key)
                    deduped.append(p)
                if removed_paras > 0:
                    doc['text'] = '\n\n'.join(deduped)
        except Exception as e:
            logger.debug(f"段落精确去重失败：{e}")

        # 3) 质量过滤
        try:
            min_chars = int(_get_numbers('CURATOR_MIN_CHARS', 200))
            max_chars = int(_get_numbers('CURATOR_MAX_CHARS', 500000))
            max_url_density = _get_numbers('CURATOR_MAX_URL_DENSITY', 0.15)
            max_repeat = _get_numbers('CURATOR_MAX_REPEAT_CHAR_RATIO', 0.2)

            hf = HeuristicFilter(
                min_chars=min_chars,
                max_chars=max_chars,
                max_url_density=max_url_density,
                max_repeat_char_ratio=max_repeat,
            )
            lf = LanguageFilter(allow=_parse_langs('zh,en'))
            qc = FastTextQualityClassifier(threshold=_get_numbers('CURATOR_QUALITY_THRESHOLD', 0.5))

            if not (hf.keep(doc) and lf.keep(doc) and qc.keep(doc)):
                logger.info("Curator 过滤后文本被丢弃（未通过启发式/语言/质量阈值）")
                return {
                    'curated_text': '',
                    'chunks': [],
                    'curation_info': {
                        'kept': False,
                        'reason': 'filtered_out'
                    }
                }
        except Exception as e:
            logger.debug(f"质量过滤阶段异常，继续后续流程: {e}")

        # 4) 可选：PII 脱敏
        try:
            if (os.getenv('CURATOR_USE_PII_REDACTOR', '').lower() in ('1', 'true', 'yes', 'on')):
                red = PIIRedactor(strategies=["emails", "phones"])  # 可按需扩展
                doc = red.process(doc)
        except Exception as e:
            logger.debug(f"PIIRedactor 失败，忽略: {e}")

        # 5) 分句分块
        try:
            sent_len = int(_get_numbers('CURATOR_MAX_SENT_LEN', 512))
            chunk_size = int(_get_numbers('CURATOR_CHUNK_SIZE', 700))
            overlap = int(_get_numbers('CURATOR_CHUNK_OVERLAP', 80))
            tokenizer = os.getenv('CURATOR_TOKENIZER', 'bert-base-multilingual-cased')

            sent = SentenceSplitter(max_sent_length=sent_len)
            doc_sent = sent.process(doc)
            splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap, tokenizer=tokenizer)
            chunks = splitter.process_many([doc_sent])
            # 分块后再做一次精确去重（防止重复块）
            if os.getenv('CURATOR_EXACT_DEDUP', 'true').lower() in ('1', 'true', 'yes', 'on'):
                seen_chunk_keys: set[str] = set()
                unique_chunks: List[Dict[str, Any]] = []
                for ch in chunks:
                    key = re.sub(r"\s+", " ", (ch.get('text') or '')).strip().lower()
                    if not key:
                        continue
                    if key in seen_chunk_keys:
                        continue
                    seen_chunk_keys.add(key)
                    unique_chunks.append(ch)
                chunks = unique_chunks
            # 可选：MinHash 近重复去重（依赖 datasketch）
            try:
                if os.getenv('CURATOR_MINHASH_DEDUP', 'true').lower() in ('1', 'true', 'yes', 'on'):
                    from datasketch import MinHash, MinHashLSH  # type: ignore
                    def _shingles(s: str, k: int) -> List[str]:
                        tokens = re.findall(r"\w+", s.lower())
                        return [" ".join(tokens[i:i+k]) for i in range(max(0, len(tokens)-k+1))]
                    k = int(_get_numbers('CURATOR_MINHASH_SHINGLE', 5))
                    num_perm = int(_get_numbers('CURATOR_MINHASH_NUM_PERM', 128))
                    threshold = float(_get_numbers('CURATOR_MINHASH_THRESHOLD', 0.8))
                    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
                    kept_chunks: List[Dict[str, Any]] = []
                    for idx, ch in enumerate(chunks):
                        t = (ch.get('text') or '').strip()
                        if not t:
                            continue
                        mh = MinHash(num_perm=num_perm)
                        for sh in _shingles(t, k):
                            mh.update(sh.encode('utf-8'))
                        if lsh.query(mh):
                            continue
                        lsh.insert(f"ch_{idx}", mh)
                        kept_chunks.append(ch)
                    chunks = kept_chunks
            except Exception as de:
                logger.debug(f"MinHash 去重失败或依赖缺失：{de}")
        except Exception as e:
            logger.debug(f"分句/分块失败，使用清理后的整段文本: {e}")
            chunks = []

        curated_text = ("\n\n".join([c.get('text', '') for c in chunks])) if chunks else (doc.get('text') or '')

        return {
            'curated_text': curated_text,
            'chunks': chunks,
            'curation_info': {
                'kept': True,
                'chunks': len(chunks),
                'tokenizer': os.getenv('CURATOR_TOKENIZER', 'bert-base-multilingual-cased')
            }
        }

    except Exception as e:
        logger.warning(f"Curator 清洗失败（自动回退）: {e}")
        return None


