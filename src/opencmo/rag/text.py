"""Deterministic token budgeting and bilingual lexical analysis."""
from __future__ import annotations

import functools
import re
import unicodedata


@functools.lru_cache(maxsize=1)
def encoder():
    import tiktoken
    return tiktoken.get_encoding("cl100k_base")


def tokens(text: str) -> int:
    return len(encoder().encode(text, disallowed_special=()))


def truncate(text: str, budget: int) -> str:
    if budget <= 0:
        return ""
    if tokens(text) <= budget:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if tokens(text[:mid]) <= budget:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo]


def lexical_terms(text: str) -> list[str]:
    import jieba
    normalized = unicodedata.normalize("NFKC", text).lower()
    result = []
    for piece in re.findall(r"[\u3400-\u9fff]+|[a-z0-9]+(?:[._-][a-z0-9]+)*", normalized):
        if re.search(r"[\u3400-\u9fff]", piece):
            result.extend(x for x in jieba.cut_for_search(piece) if x.strip())
        else:
            result.append(piece)
    return result


def fts_query(text: str) -> str:
    terms = list(dict.fromkeys(lexical_terms(text)))[:32]
    return " OR ".join('"' + t.replace('"', '""') + '"' for t in terms)
