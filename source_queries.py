import re

DEFAULT_NEWS_QUERIES = [
    "AI news",
    "LLM news",
    "AI coding agent",
    "open source AI tools",
]

DEFAULT_WEB_QUERIES = [
    "AI official announcement",
    "AI launch blog",
    "AI developer tool release",
    "LLM open source release",
]

DEFAULT_SOCIAL_QUERIES = [
    "AI announcement site:x.com",
    "AI announcement site:threads.com",
    "AI coding agent site:x.com",
    "open source AI site:threads.com",
]

DEFAULT_GITHUB_QUERIES = [
    "vibe coding",
    "AI coding agent",
    "Claude Code",
    "Codex skills",
    "MCP server",
    "LLM tools",
]

TOPIC_HINTS = {
    "바이브": "vibe coding",
    "코딩": "coding",
    "스킬": "skills",
    "오픈": "open source",
    "에이전트": "agent",
    "이미지": "image generation",
    "그림": "image generation",
    "영상": "video generation",
    "모델": "model",
}

STOPWORDS = {
    "ai",
    "the",
    "and",
    "for",
    "with",
    "official",
    "announcement",
    "launch",
    "blog",
    "news",
    "repo",
    "repository",
    "search",
    "open",
    "source",
    "검색",
    "레포",
}


def expand_topic_queries(topic: str, defaults: list[str] | None = None, max_queries: int = 6) -> list[str]:
    topic = (topic or "").strip()
    defaults = defaults or []
    queries: list[str] = []

    if topic:
        queries.append(topic)
        translated = _translate_topic_hints(topic)
        if translated and translated.lower() != topic.lower():
            queries.append(translated)

        queries.extend(_special_topic_queries(topic))

        focused = _focus_topic(topic, translated)
        if focused:
            queries.append(focused)

    queries.extend(defaults)
    return _dedupe(queries)[:max_queries]


def extract_relevance_terms(topics: list[str] | str) -> list[str]:
    if isinstance(topics, str):
        topics = [topics]

    text = " ".join(topic or "" for topic in topics)
    expanded = " ".join(expand_topic_queries(text, [], max_queries=8))
    candidates = re.findall(r"[A-Za-z][A-Za-z0-9.+_-]*|[가-힣]{2,}", f"{text} {expanded}")

    terms = []
    for term in candidates:
        normalized = term.lower().strip("._-")
        if len(normalized) < 2 or normalized in STOPWORDS:
            continue
        if normalized not in terms:
            terms.append(normalized)
    return terms[:12]


def _translate_topic_hints(topic: str) -> str:
    translated_parts = []
    lowered = topic.lower()
    for korean, english in TOPIC_HINTS.items():
        if korean not in lowered:
            continue
        if english not in translated_parts:
            translated_parts.append(english)

    latin_terms = re.findall(r"[A-Za-z][A-Za-z0-9.+_-]*", topic)
    translated = " ".join(translated_parts + latin_terms).strip()
    if translated and "ai" not in translated.lower():
        translated = f"{translated} AI"
    return translated


def _special_topic_queries(topic: str) -> list[str]:
    lowered = topic.lower()
    queries = []

    if "gpt" in lowered and ("image" in lowered or "이미지" in topic or "그림" in topic):
        queries.extend([
            "OpenAI ChatGPT Images 2.0",
            "OpenAI image generation",
            "ChatGPT image model",
        ])

    if "mcp" in lowered:
        queries.extend([
            "Model Context Protocol",
            "MCP developer tools",
        ])

    if "codex" in lowered:
        queries.extend([
            "OpenAI Codex",
            "Codex coding agent",
        ])

    return queries


def _focus_topic(topic: str, translated: str) -> str:
    candidates = re.findall(r"[A-Za-z][A-Za-z0-9.+_-]*|[가-힣]{2,}", f"{topic} {translated}")
    terms = []
    for term in candidates:
        normalized = term.lower()
        if normalized not in STOPWORDS and len(normalized) > 1:
            terms.append(term)

    focused = " ".join(_dedupe(terms[:5]))
    if not focused:
        return ""
    if "ai" not in focused.lower():
        focused = f"{focused} AI"
    return focused


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for value in values:
        normalized = " ".join(value.split()).strip()
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            deduped.append(normalized)
    return deduped
