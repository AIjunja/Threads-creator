from llm_client import generate_text


def summarize_news(articles: list[dict]) -> str:
    if not articles:
        return ""

    articles_text = "\n\n".join([
        f"제목: {a['title']}\n종류: {a.get('type', '')}\n내용: {a['snippet']}\n출처: {a.get('source', '')}\nURL: {a.get('url', '')}"
        for a in articles
    ])

    prompt = f"""다음은 오늘의 AI/개발 관련 뉴스와 GitHub 오픈 레포지토리 목록입니다.

{articles_text}

위 자료 중 Threads 콘텐츠로 만들었을 때 가장 반응이 좋을 5개를 선별해주세요.
단순 요약이 아니라 writer가 바로 강한 글을 쓸 수 있게 "구체 사실"과 "의미 해석"을 보존해야 합니다.

규칙:
- 제목만 보고 추측하지 말고, 제공된 내용 안에 있는 사실만 사용하세요.
- 숫자, 모델명, 회사명, 레포지토리명, 가격, 성능 비교가 있으면 반드시 보존하세요.
- 자료가 약하면 "확인된 수치 없음"이라고 쓰고 숫자를 지어내지 마세요.
- 각 항목은 서로 다른 소재가 되도록 고르세요.
- 뉴스 기사에만 치우치지 말고, 공식 발표, X/Threads 등 SNS 원문, GitHub 레포지토리, 공식 블로그를 우선 고려하세요.
- 같은 주제라면 2차 기사보다 공식 SNS/공식 블로그/GitHub 레포지토리를 더 높은 우선순위로 보세요.
- GitHub 레포지토리는 출처 URL을 반드시 직접 GitHub 링크로 유지하세요.

각 항목은 다음 형식으로 작성하세요.

**[번호]. [제목]**
- 콘텐츠 각도: (출시/공개/벤치마크/가격 변경/도구 비교/논쟁/실무 변화 중 하나)
- 구체 사실: (숫자, 제품명, 회사명, 레포지토리명 중심 2-3문장)
- 왜 중요한가: (실무자/창업가/자동화 관심층 관점 1-2문장)
- 추천 첫 문장: (숫자·반전·출시·공개가 드러나는 강한 한 문장)
- 출처 URL: (제공된 URL)

한국어로 작성하세요."""

    return generate_text(prompt)


if __name__ == "__main__":
    from searcher import search_ai_news
    articles = search_ai_news(["AI 뉴스", "LLM"], max_results=10)
    print(f"수집된 기사: {len(articles)}개\n")
    summary = summarize_news(articles)
    print(summary)
