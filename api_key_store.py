import os

PROVIDER_API_ENV = {
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}


def get_env_name_for_provider(provider: str) -> str | None:
    return PROVIDER_API_ENV.get((provider or "").strip().lower())


def _read_user_env_var(name: str) -> str | None:
    if os.name != "nt":
        return None

    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value).strip() or None
    except FileNotFoundError:
        return None
    except OSError:
        return None


def _broadcast_environment_change():
    if os.name != "nt":
        return

    try:
        import ctypes

        hwnd_broadcast = 0xFFFF
        wm_settingchange = 0x001A
        send_abort_if_hung = 0x0002
        ctypes.windll.user32.SendMessageTimeoutW(
            hwnd_broadcast,
            wm_settingchange,
            0,
            "Environment",
            send_abort_if_hung,
            5000,
            None,
        )
    except OSError:
        pass


def get_api_key(env_name: str) -> str | None:
    key = (os.getenv(env_name) or "").strip()
    if key:
        return key

    key = _read_user_env_var(env_name)
    if key:
        os.environ[env_name] = key
    return key


def has_api_key_for_provider(provider: str) -> bool:
    env_name = get_env_name_for_provider(provider)
    return bool(env_name and get_api_key(env_name))


def save_api_key_for_provider(provider: str, api_key: str):
    env_name = get_env_name_for_provider(provider)
    if not env_name:
        raise ValueError("이 provider는 API 키가 필요하지 않습니다.")

    api_key = (api_key or "").strip()
    if not api_key:
        raise ValueError("API 키를 입력해주세요.")

    os.environ[env_name] = api_key
    if os.name != "nt":
        return

    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
        winreg.SetValueEx(key, env_name, 0, winreg.REG_SZ, api_key)
    _broadcast_environment_change()


def delete_api_key_for_provider(provider: str):
    env_name = get_env_name_for_provider(provider)
    if not env_name:
        return

    os.environ.pop(env_name, None)
    if os.name != "nt":
        return

    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, env_name)
        _broadcast_environment_change()
    except FileNotFoundError:
        pass
    except OSError:
        pass
