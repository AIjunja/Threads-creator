from datetime import datetime

from config import load_config, load_persona, OUTPUTS_DIR
from searcher import search_ai_news
from github_searcher import search_trending_repos
from summarizer import summarize_news
from writer import generate_threads


def run_pipeline(
    persona_name: str,
    count: int = 3,
    topic: str = "",
    include_github: bool = True,
    log_callback=None,
) -> list[str]:
    def log(msg: str):
        print(msg)
        if log_callback:
            log_callback(msg)

    config = load_config()
    persona = load_persona(persona_name)
    if not persona:
        raise ValueError(f"페르소나를 찾을 수 없습니다: {persona_name}")

    keywords = [topic] if topic.strip() else config["keywords"]
    label = f"'{topic}'" if topic.strip() else "기본 키워드"

    log(f"{label} 자료 수집 중")
    articles = search_ai_news(keywords, max_results=15)
    log(f"웹/SNS/공식 자료 {len(articles)}개 수집 완료")

    github_repos = []
    if include_github:
        log("GitHub 오픈 레포지토리 수집 중")
        github_repos = search_trending_repos(topic or "vibe coding ai", max_results=8)
        log(f"GitHub {len(github_repos)}개 수집 완료")

    all_sources = articles + github_repos
    if not all_sources:
        raise RuntimeError(
            "검색 결과를 찾지 못했습니다. 주제를 더 넓게 입력하거나, GitHub 오픈 레포지토리 포함을 켠 뒤 다시 시도해주세요."
        )

    log("요약 생성 중")
    summary = summarize_news(all_sources)
    if not summary.strip():
        raise RuntimeError("수집된 자료를 요약하지 못했습니다. 다른 주제나 다른 모델로 다시 시도해주세요.")
    log("요약 완료")

    log(f"스레드 초안 {count}개 생성 중")
    threads = generate_threads(summary, persona, count=count, topic=topic, sources=all_sources)
    log(f"{len(threads)}개 스레드 생성 완료")

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    output_path = OUTPUTS_DIR / f"{today}_threads.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# AI 뉴스 스레드 초안 — {today}\n\n")
        f.write(f"## 요약\n\n{summary}\n\n")
        f.write("## 스레드 초안\n\n")
        for i, thread in enumerate(threads, 1):
            f.write(f"{thread}\n\n")

    log(f"저장 완료: {output_path}")
    return threads


if __name__ == "__main__":
    from config import list_personas, save_persona

    if not list_personas():
        save_persona("persona_default", {
            "name": "기본 스타일",
            "tone": "친근하고 직접적인",
            "structure": "짧은 문장, 핵심 먼저, 줄바꿈 많이",
            "example_phrases": ["솔직히", "이거 중요함", "쉽게 말하면"]
        })

    threads = run_pipeline("persona_default", count=2)
    for t in threads:
        print(t)
        print()
