import sys
import os
import subprocess
from pathlib import Path
from winotify import Notification, audio

APP_DIR = Path(__file__).parent
APP_PY = APP_DIR / "app.py"
PYTHON = APP_DIR / "venv" / "Scripts" / "pythonw.exe"

STARTUP_DIR = (
    Path.home()
    / "AppData"
    / "Roaming"
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "Startup"
)
BAT_PATH = STARTUP_DIR / "ai_thread_notifier.bat"


def send_toast():
    toast = Notification(
        app_id="AI 스레드 자동화",
        title="AI 스레드 만들까요? 🤖",
        msg="클릭하면 앱이 열립니다",
        duration="short",
        launch=str(APP_PY),
    )
    toast.set_audio(audio.Default, loop=False)
    toast.show()


def launch_app():
    python = PYTHON if PYTHON.exists() else sys.executable
    subprocess.Popen(
        [str(python), str(APP_PY)],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def register_startup():
    bat_content = f'@echo off\n"{PYTHON}" "{APP_DIR / "notifier.py"}"\n'
    BAT_PATH.write_text(bat_content, encoding="utf-8")
    print(f"시작프로그램 등록 완료: {BAT_PATH}")


def unregister_startup():
    if BAT_PATH.exists():
        BAT_PATH.unlink()
        print("시작프로그램 등록 해제 완료")


if __name__ == "__main__":
    if "--register" in sys.argv:
        register_startup()
    elif "--unregister" in sys.argv:
        unregister_startup()
    elif "--launch" in sys.argv:
        launch_app()
    else:
        send_toast()
