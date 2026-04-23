from datetime import datetime, timedelta
import re
import time

import requests

from source_queries import DEFAULT_GITHUB_QUERIES, expand_topic_queries, extract_relevance_terms


def search_trending_repos(topic: str = "vibe-coding", max_results: int = 10) -> list[dict]:
    """Search public GitHub repositories that are relevant, active, and popular."""
    queries = expand_topic_queries(topic, DEFAULT_GITHUB_QUERIES, max_queries=6)
    relevance_terms = extract_relevance_terms(topic)
    since = (datetime.utcnow() - timedelta(days=730)).strftime("%Y-%m-%d")
    results = {}

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-Thread-App/1.0",
    }

    for query in queries:
        for min_stars in (50, 5, 0):
            found = _search_repositories(query, since, min_stars, max_results, headers, relevance_terms)
            for item in found:
                url = item["html_url"]
                current = results.get(url)
                if not current or item["stargazers_count"] > current.get("stars", 0):
                    results[url] = _to_source_item(item, query)
            if found:
                break
        if len(results) >= max_results:
            break
        time.sleep(0.5)

    ranked = sorted(results.values(), key=_repo_score, reverse=True)
    return ranked[:max_results]


def _search_repositories(query: str, since: str, min_stars: int, max_results: int, headers: dict, relevance_terms: list[str]) -> list[dict]:
    qualifiers = f"in:name,description,readme pushed:>{since}"
    if min_stars:
        qualifiers += f" stars:>{min_stars}"

    params = {
        "q": f"{query} {qualifiers}",
        "sort": "stars",
        "order": "desc",
        "per_page": max(5, min(20, max_results + 4)),
    }

    try:
        resp = requests.get("https://api.github.com/search/repositories", params=params, headers=headers, timeout=10)
        if resp.status_code == 200:
            return [
                item
                for item in resp.json().get("items", [])
                if _is_relevant_repo(item, query, relevance_terms)
            ]
        if resp.status_code == 403:
            print("[github] rate limit 초과, 잠시 대기합니다.")
            time.sleep(5)
        else:
            print(f"[github] '{query}' 검색 실패: {resp.status_code} {resp.text[:120]}")
    except Exception as e:
        print(f"[github] '{query}' 오류: {e}")
    return []


def _is_relevant_repo(item: dict, query: str, relevance_terms: list[str]) -> bool:
    haystack = " ".join([
        item.get("name", ""),
        item.get("full_name", ""),
        item.get("description") or "",
        " ".join(item.get("topics") or []),
    ]).lower()

    domain_patterns = [
        r"\bai\b",
        r"\bagent(s)?\b",
        r"\bllm(s)?\b",
        r"\bmcp\b",
        r"\bcodex\b",
        r"\bclaude\b",
        r"\bvibe\b",
        r"\bprompt(s)?\b",
        r"\bcopilot\b",
        r"\bcursor\b",
        r"\bwindsurf\b",
        r"\baider\b",
    ]
    domain_relevant = any(re.search(pattern, haystack) for pattern in domain_patterns)
    if not relevance_terms:
        return domain_relevant

    topic_matches = [term for term in relevance_terms if term in haystack]
    if len(relevance_terms) >= 4:
        return domain_relevant and len(topic_matches) >= 1
    return domain_relevant and bool(topic_matches)


def _to_source_item(item: dict, query: str) -> dict:
    description = item.get("description") or "설명 없음"
    stars = int(item.get("stargazers_count") or 0)
    return {
        "title": f"★ {stars:,} | {item['full_name']}",
        "url": item["html_url"],
        "snippet": description,
        "date": (item.get("pushed_at") or "")[:10],
        "source": "GitHub",
        "stars": stars,
        "type": "github",
        "query": query,
    }


def _repo_score(repo: dict) -> float:
    stars = repo.get("stars", 0)
    date = repo.get("date", "")
    recency = 0
    if date:
        try:
            days_old = (datetime.utcnow() - datetime.strptime(date, "%Y-%m-%d")).days
            recency = max(0, 730 - days_old)
        except ValueError:
            recency = 0
    return stars + recency * 2


if __name__ == "__main__":
    repos = search_trending_repos("vibe coding", max_results=5)
    for r in repos:
        print(f"{r['title']}\n  {r['url']}\n  {r['snippet']}\n")
