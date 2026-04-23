import random
import time

from ddgs import DDGS

from source_queries import DEFAULT_NEWS_QUERIES, DEFAULT_SOCIAL_QUERIES, DEFAULT_WEB_QUERIES, expand_topic_queries, extract_relevance_terms


def search_ai_news(keywords: list[str], max_results: int = 20) -> list[dict]:
    queries = _build_source_queries(keywords, max_results=max_results)
    relevance_terms = extract_relevance_terms(keywords)
    results = []
    fallback_results = []
    seen_urls = set()
    per_query = max(3, min(8, max_results // max(1, len(queries)) + 2))

    with DDGS() as ddgs:
        for i, query in enumerate(queries):
            if i > 0:
                time.sleep(random.uniform(0.8, 1.8))

            added = 0
            for hit in _search_query(ddgs, query, per_query):
                url = hit.get("url") or hit.get("href") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                source_type, source_name = _classify_source(url, hit.get("source", ""))
                item = {
                    "title": hit.get("title", ""),
                    "url": url,
                    "snippet": hit.get("body", "") or hit.get("snippet", ""),
                    "date": hit.get("date", ""),
                    "source": source_name,
                    "type": source_type,
                    "query": query,
                }
                if _is_relevant_hit(item, relevance_terms):
                    results.append(item)
                    added += 1
                else:
                    fallback_results.append(item)
                    continue
                if len(results) >= max_results:
                    break

            print(f"[searcher] '{query}' {added}개 수집")
            if len(results) >= max_results:
                break

    if len(results) < min(3, max_results):
        for item in fallback_results:
            results.append(item)
            if len(results) >= max_results:
                break

    return results[:max_results]


def _build_source_queries(keywords: list[str], max_results: int) -> list[str]:
    queries = []
    for keyword in keywords:
        topic_queries = expand_topic_queries(keyword, [], max_queries=5)
        for topic_query in topic_queries:
            queries.extend(_build_social_queries(topic_query))
        for topic_query in topic_queries:
            queries.extend(_build_official_web_queries(topic_query))
        queries.extend(expand_topic_queries(keyword, DEFAULT_WEB_QUERIES, max_queries=6))
        queries.extend(expand_topic_queries(keyword, DEFAULT_NEWS_QUERIES, max_queries=6))
    queries.extend(DEFAULT_SOCIAL_QUERIES)
    return _dedupe(queries)[:max(10, min(18, max_results + 6))]


def _build_social_queries(keyword: str) -> list[str]:
    keyword = (keyword or "").strip()
    if not keyword:
        return []
    return [
        f"{keyword} official site:x.com",
        f"{keyword} launch site:x.com",
        f"{keyword} announcement site:x.com",
        f"{keyword} official site:threads.com",
        f"{keyword} announcement site:threads.com",
    ]


def _build_official_web_queries(keyword: str) -> list[str]:
    keyword = (keyword or "").strip()
    if not keyword:
        return []
    return [
        f"{keyword} official announcement",
        f"{keyword} official blog",
        f"{keyword} launch",
        f"{keyword} site:openai.com OR site:anthropic.com OR site:ai.google.dev OR site:qwen.ai OR site:meta.com",
    ]


def _search_query(ddgs: DDGS, query: str, max_results: int) -> list[dict]:
    text_first = any(site in query.lower() for site in ("site:x.com", "site:twitter.com", "site:threads.com", "site:github.com"))
    searchers = (
        lambda: ddgs.text(query, region="wt-wt", safesearch="off", max_results=max_results),
        lambda: ddgs.news(query, region="kr-ko", safesearch="off", timelimit="w", max_results=max_results),
        lambda: ddgs.news(query, region="wt-wt", safesearch="off", timelimit="m", max_results=max_results),
    ) if text_first else (
        lambda: ddgs.news(query, region="kr-ko", safesearch="off", timelimit="w", max_results=max_results),
        lambda: ddgs.text(query, region="wt-wt", safesearch="off", max_results=max_results),
        lambda: ddgs.news(query, region="wt-wt", safesearch="off", timelimit="m", max_results=max_results),
    )

    for search in searchers:
        try:
            hits = list(search())
            if hits:
                return hits
        except Exception as e:
            print(f"[searcher] '{query}' 검색 실패: {e}")
    return []


def _classify_source(url: str, fallback_source: str = "") -> tuple[str, str]:
    lowered = url.lower()
    if "github.com/" in lowered:
        return "github", "GitHub"
    if "threads.com/" in lowered or "threads.net/" in lowered:
        return "social", "Threads"
    if "x.com/" in lowered or "twitter.com/" in lowered:
        return "social", "X"
    if any(domain in lowered for domain in ("openai.com", "anthropic.com", "googleblog.com", "deepmind.google", "ai.google.dev", "qwen.ai", "meta.com", "microsoft.com")):
        return "official", "Official"
    return "news", fallback_source or "Web"


def _is_relevant_hit(item: dict, relevance_terms: list[str]) -> bool:
    if not relevance_terms:
        return True

    haystack = " ".join([
        item.get("title", ""),
        item.get("snippet", ""),
        item.get("url", ""),
        item.get("source", ""),
    ]).lower()

    matches = [term for term in relevance_terms if term in haystack]
    if len(relevance_terms) >= 4:
        return len(matches) >= 2
    return bool(matches)


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


if __name__ == "__main__":
    results = search_ai_news(["AI 뉴스", "LLM"], max_results=10)
    for r in results[:3]:
        print(f"- {r['title']}\n  {r['url']}\n")
