SUPPORTED_PROVIDERS = ("ollama", "openai", "gemini")

MODEL_PRESETS = {
    "ollama": [
        "gemma4:31b",
        "gemma3:27b",
        "llama3.1:8b",
        "qwen2.5:14b",
    ],
    "openai": [
        "gpt-5.4-mini",
        "gpt-5.4",
        "gpt-5.4-nano",
        "gpt-4.1-mini",
        "gpt-4.1-nano",
    ],
    "gemini": [
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-2.5-flash-lite",
        "gemini-3-pro-preview",
    ],
}

MODEL_ALIASES = {
    "openai": {
        "gpt-5.3": "gpt-5.4-mini",
        "gpt-5.3-mini": "gpt-5.4-mini",
        "gpt-5.3-nano": "gpt-5.4-nano",
    },
}


def normalize_provider(provider: str) -> str:
    normalized = (provider or "ollama").strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise RuntimeError(f"지원하지 않는 LLM provider입니다: {normalized}")
    return normalized


def get_default_model(provider: str) -> str:
    provider = normalize_provider(provider)
    return MODEL_PRESETS[provider][0]


def get_model_presets(provider: str) -> list[str]:
    provider = normalize_provider(provider)
    return MODEL_PRESETS[provider].copy()


def normalize_model_name(provider: str, model: str | None) -> str:
    provider = normalize_provider(provider)
    model = (model or "").strip()
    if not model:
        return get_default_model(provider)
    return MODEL_ALIASES.get(provider, {}).get(model, model)


def get_model_alias_notice(provider: str, model: str | None) -> str | None:
    provider = normalize_provider(provider)
    model = (model or "").strip()
    replacement = MODEL_ALIASES.get(provider, {}).get(model)
    if not replacement:
        return None
    return f"{model} 모델은 사용할 수 없어 {replacement}로 바꿨습니다."
