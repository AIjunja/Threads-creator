import ollama

from api_key_store import get_api_key
from config import load_config
from model_catalog import get_default_model, normalize_model_name, normalize_provider


def get_provider_and_model(config: dict | None = None) -> tuple[str, str]:
    config = config or load_config()
    provider = normalize_provider(config.get("llm_provider", "ollama"))
    model_map = {
        "ollama": str(config.get("ollama_model", get_default_model("ollama"))).strip(),
        "openai": str(config.get("openai_model", get_default_model("openai"))).strip(),
        "gemini": str(config.get("gemini_model", get_default_model("gemini"))).strip(),
    }
    model = normalize_model_name(provider, model_map[provider])
    if not model:
        raise RuntimeError(f"{provider} provider의 모델명이 비어 있습니다.")
    return provider, model


def _merge_prompt(prompt: str, system_prompt: str | None = None) -> str:
    if system_prompt:
        return f"{system_prompt.strip()}\n\n{prompt.strip()}"
    return prompt.strip()


def _generate_with_ollama(model: str, prompt: str) -> str:
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.get("message", {}).get("content", "").strip()
    if not text:
        raise RuntimeError("Ollama 응답에 텍스트가 없습니다.")
    return text


def _generate_with_openai(model: str, prompt: str) -> str:
    api_key = get_api_key("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OpenAI를 사용하려면 OPENAI_API_KEY 환경변수가 필요합니다.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI provider를 사용하려면 openai 패키지를 설치해야 합니다.") from exc

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(model=model, input=prompt, store=False)
    except Exception as exc:
        if "model_not_found" in str(exc) or "does not exist" in str(exc):
            raise RuntimeError(
                f"OpenAI 모델 '{model}'을 사용할 수 없습니다. 설정에서 gpt-5.4-mini, gpt-5.4, gpt-5.4-nano 중 하나를 선택해보세요."
            ) from exc
        raise

    text = (getattr(response, "output_text", "") or "").strip()
    if not text:
        raise RuntimeError("OpenAI 응답에 텍스트가 없습니다.")
    return text


def _generate_with_gemini(model: str, prompt: str) -> str:
    api_key = get_api_key("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Gemini를 사용하려면 GEMINI_API_KEY 환경변수가 필요합니다.")

    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError("Gemini provider를 사용하려면 google-genai 패키지를 설치해야 합니다.") from exc

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(model=model, contents=prompt)
    except Exception as exc:
        if "not found" in str(exc).lower() or "model" in str(exc).lower():
            raise RuntimeError(
                f"Gemini 모델 '{model}'을 사용할 수 없습니다. 설정에서 gemini-2.5-flash, gemini-2.5-pro, gemini-2.5-flash-lite 중 하나를 선택해보세요."
            ) from exc
        raise

    text = (getattr(response, "text", "") or "").strip()
    if not text:
        raise RuntimeError("Gemini 응답에 텍스트가 없습니다.")
    return text


def generate_text(prompt: str, system_prompt: str | None = None) -> str:
    config = load_config()
    provider, model = get_provider_and_model(config)
    merged_prompt = _merge_prompt(prompt, system_prompt=system_prompt)

    if provider == "ollama":
        return _generate_with_ollama(model, merged_prompt)
    if provider == "openai":
        return _generate_with_openai(model, merged_prompt)
    if provider == "gemini":
        return _generate_with_gemini(model, merged_prompt)

    raise RuntimeError(f"알 수 없는 provider입니다: {provider}")


def list_available_models(provider: str) -> list[str]:
    provider = normalize_provider(provider)

    if provider == "ollama":
        response = ollama.list()
        models = response.get("models", []) if isinstance(response, dict) else getattr(response, "models", [])
        names = []
        for item in models:
            name = item.get("model") if isinstance(item, dict) else getattr(item, "model", None)
            name = name or (item.get("name") if isinstance(item, dict) else getattr(item, "name", None))
            if name:
                names.append(str(name))
        return sorted(set(names))

    if provider == "openai":
        api_key = get_api_key("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OpenAI 모델 목록을 불러오려면 OPENAI_API_KEY가 필요합니다.")

        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        models = client.models.list()
        excluded = ("audio", "embedding", "image", "moderation", "realtime", "sora", "transcribe", "tts")
        names = [
            model.id
            for model in getattr(models, "data", [])
            if getattr(model, "id", "").startswith(("gpt-", "o"))
            and not any(part in getattr(model, "id", "") for part in excluded)
        ]
        return sorted(set(names))

    if provider == "gemini":
        api_key = get_api_key("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Gemini 모델 목록을 불러오려면 GEMINI_API_KEY가 필요합니다.")

        from google import genai

        client = genai.Client(api_key=api_key)
        names = []
        excluded = ("audio", "embedding", "image", "live", "tts")
        for model in client.models.list():
            raw_name = getattr(model, "name", "")
            name = str(raw_name).split("/")[-1]
            if "gemini" in name and not any(part in name for part in excluded):
                names.append(name)
        return sorted(set(names))

    return []
