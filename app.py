import customtkinter as ctk
from datetime import datetime
import pathlib
import re
import threading
import webbrowser

LOG_FILE = pathlib.Path.home() / "thread_app_debug.log"


def append_debug_log(msg):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


from config import OUTPUTS_DIR, list_personas, load_config, save_config
from api_key_store import (
    delete_api_key_for_provider,
    get_env_name_for_provider,
    has_api_key_for_provider,
    save_api_key_for_provider,
)
from font_loader import get_ui_font_family
from llm_client import list_available_models
from model_catalog import (
    get_default_model,
    get_model_alias_notice,
    get_model_presets,
    normalize_model_name,
)
from obsidian_integration import open_markdown_in_obsidian
from pipeline import run_pipeline
from persona_setup import PersonaSetupWindow

append_debug_log("=== app started ===")

ctk.set_default_color_theme("blue")

THEMES = {
    "dark": {
        "BG": "#0b1020",
        "SURFACE": "#111827",
        "MUTED": "#1f2937",
        "MUTED_STRONG": "#273449",
        "BORDER": "#263244",
        "BORDER_STRONG": "#334155",
        "PRIMARY": "#3b82f6",
        "PRIMARY_HOVER": "#2563eb",
        "PRIMARY_SOFT": "#172554",
        "SECONDARY_HOVER": "#1e3a8a",
        "TEXT": "#f8fafc",
        "TEXT_STRONG": "#e5e7eb",
        "TEXT_MUTED": "#94a3b8",
        "TEXT_CAPTION": "#64748b",
        "PLACEHOLDER": "#64748b",
        "SUCCESS": "#22c55e",
        "ERROR": "#fb7185",
        "WARNING": "#f59e0b",
    },
    "light": {
        "BG": "#f5f7fb",
        "SURFACE": "#ffffff",
        "MUTED": "#eef2f7",
        "MUTED_STRONG": "#e2e8f0",
        "BORDER": "#dbe3ef",
        "BORDER_STRONG": "#cbd5e1",
        "PRIMARY": "#2563eb",
        "PRIMARY_HOVER": "#1d4ed8",
        "PRIMARY_SOFT": "#dbeafe",
        "SECONDARY_HOVER": "#bfdbfe",
        "TEXT": "#0f172a",
        "TEXT_STRONG": "#1e293b",
        "TEXT_MUTED": "#64748b",
        "TEXT_CAPTION": "#94a3b8",
        "PLACEHOLDER": "#94a3b8",
        "SUCCESS": "#16a34a",
        "ERROR": "#e11d48",
        "WARNING": "#d97706",
    },
}


def normalize_theme_mode(mode: str | None) -> str:
    return "light" if str(mode).strip().lower() in {"light", "white", "화이트"} else "dark"


def apply_theme_tokens(mode: str | None) -> str:
    global BG, SURFACE, MUTED, MUTED_STRONG, BORDER, BORDER_STRONG
    global PRIMARY, PRIMARY_HOVER, PRIMARY_SOFT, SECONDARY_HOVER
    global TEXT, TEXT_STRONG, TEXT_MUTED, TEXT_CAPTION, PLACEHOLDER
    global SUCCESS, ERROR, WARNING

    normalized = normalize_theme_mode(mode)
    for name, value in THEMES[normalized].items():
        globals()[name] = value
    ctk.set_appearance_mode(normalized)
    return normalized


ACTIVE_THEME = apply_theme_tokens(load_config().get("theme_mode", "dark"))

FONT_FAMILY = get_ui_font_family()
FALLBACK_FONT = "Malgun Gothic"
NO_PERSONA_LABEL = "페르소나를 먼저 만들어주세요"
CREATOR_CHANNEL_URL = "https://www.youtube.com/@AI%EC%AD%8C"


_STATUS_PREFIX_RE = re.compile(r"^[\W_]+\s*")


def clean_status_text(text: str) -> str:
    cleaned = _STATUS_PREFIX_RE.sub("", text or "").strip()
    return cleaned or "준비됐어요"


def format_user_error(error: Exception) -> str:
    msg = str(error).strip()
    if "OPENAI_API_KEY" in msg:
        return "OpenAI API 키가 아직 등록되지 않았습니다. 메인 화면의 설정 도우미에서 OPENAI_API_KEY를 등록해주세요."
    if "GEMINI_API_KEY" in msg:
        return "Gemini API 키가 아직 등록되지 않았습니다. 메인 화면의 설정 도우미에서 GEMINI_API_KEY를 등록해주세요."
    if "모델" in msg and ("사용할 수 없습니다" in msg or "model_not_found" in msg or "does not exist" in msg):
        return f"{msg}\n\n모델 설정에서 추천 목록을 선택하거나, API 키 등록 후 '모델 불러오기'를 눌러 실제 사용 가능한 모델을 선택해주세요."
    if "Ollama" in msg or "ollama" in msg:
        return "Ollama 로컬 모델 실행에 실패했습니다. Ollama가 실행 중인지, 선택한 모델이 pull되어 있는지 확인해주세요."
    if "검색 결과" in msg:
        return f"{msg}\n\n예: 'AI 코딩 에이전트', '오픈소스 LLM 도구', 'vibe coding agent'처럼 조금 더 넓은 키워드로 시도해보세요."
    if "페르소나" in msg:
        return f"{msg}\n\n페르소나 만들기 버튼으로 말투를 먼저 저장해주세요."
    if "파싱" in msg or "출력 형식" in msg:
        return f"{msg}\n\n모델이 요청한 출력 형식을 지키지 못했습니다. 다시 생성하거나 다른 모델을 선택해보세요."
    if "No module named" in msg:
        return "필수 패키지가 설치되지 않았습니다. run_app.bat을 다시 실행해 자동 설치를 진행해주세요."
    return msg or "알 수 없는 오류가 발생했습니다. debug log를 확인해주세요."


def ui_font(size=14, weight="normal"):
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


class Card(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            fg_color=SURFACE,
            border_width=1,
            border_color=BORDER,
            corner_radius=12,
            **kwargs,
        )


class SectionHeader(ctk.CTkFrame):
    def __init__(self, parent, title: str, subtitle: str = "", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        ctk.CTkLabel(
            self,
            text=title,
            font=ui_font(16, "bold"),
            text_color=TEXT,
            anchor="w",
        ).pack(fill="x")
        if subtitle:
            ctk.CTkLabel(
                self,
                text=subtitle,
                font=ui_font(13),
                text_color=TEXT_MUTED,
                anchor="w",
                justify="left",
            ).pack(fill="x", pady=(3, 0))


class ThreadCard(Card):
    def __init__(self, parent, index: int, text: str, **kwargs):
        super().__init__(parent, **kwargs)
        self.text = text

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=18, pady=(16, 0))

        ctk.CTkLabel(
            header,
            text=f"스레드 {index}",
            font=ui_font(14, "bold"),
            text_color=TEXT,
            anchor="w",
        ).pack(side="left")

        copy_btn = ctk.CTkButton(
            header,
            text="복사",
            width=56,
            height=30,
            font=ui_font(12, "bold"),
            fg_color=PRIMARY_SOFT,
            hover_color=SECONDARY_HOVER,
            text_color=PRIMARY,
            corner_radius=8,
            border_width=0,
            command=self._copy,
        )
        copy_btn.pack(side="right")

        body = ctk.CTkTextbox(
            self,
            font=ui_font(14),
            fg_color=SURFACE,
            text_color=TEXT_STRONG,
            wrap="word",
            activate_scrollbars=False,
            border_width=0,
            height=170,
        )
        body.pack(fill="both", expand=True, padx=18, pady=(10, 16))
        body.insert("0.0", text)
        body.configure(state="disabled")

    def _copy(self):
        self.clipboard_clear()
        self.clipboard_append(self.text)


class StatusBar(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color=SURFACE, height=44, corner_radius=0, **kwargs)
        self.indicator = ctk.CTkFrame(self, width=8, height=8, fg_color=SUCCESS, corner_radius=999)
        self.indicator.pack(side="left", padx=(20, 8))
        self.indicator.pack_propagate(False)

        self.label = ctk.CTkLabel(
            self,
            text="준비됐어요",
            font=ui_font(13),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.label.pack(side="left", fill="x", expand=True)

    def set(self, msg: str, state: str = "idle"):
        color_map = {"idle": TEXT_MUTED, "running": WARNING, "done": SUCCESS, "error": ERROR}
        indicator_map = {"idle": SUCCESS, "running": WARNING, "done": SUCCESS, "error": ERROR}
        self.label.configure(text=clean_status_text(msg), text_color=color_map.get(state, TEXT_MUTED))
        self.indicator.configure(fg_color=indicator_map.get(state, SUCCESS))


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=BG)
        config = load_config()
        self.theme_mode = normalize_theme_mode(config.get("theme_mode", ACTIVE_THEME))
        self.creator_acknowledged = bool(config.get("creator_cta_acknowledged", False))
        self.title("Thread AI")
        self.geometry("560x780")
        self.minsize(430, 620)
        self._build()
        self._refresh_personas()

    def _set_theme_mode(self, selected: str):
        next_mode = "light" if selected == "Light" else "dark"
        if next_mode == self.theme_mode:
            return

        snapshot = self._snapshot_form_state()
        config = load_config()
        config["theme_mode"] = next_mode
        save_config(config)

        self.theme_mode = apply_theme_tokens(next_mode)
        self.configure(fg_color=BG)
        for child in self.winfo_children():
            child.destroy()

        self._build()
        self._refresh_personas()
        self._restore_form_state(snapshot)
        self.status.set(f"{'화이트' if next_mode == 'light' else '다크'} 모드로 변경했어요", "done")

    def _snapshot_form_state(self) -> dict:
        return {
            "provider": self.provider_var.get() if hasattr(self, "provider_var") else "",
            "model": self.model_var.get() if hasattr(self, "model_var") else "",
            "topic": self.topic_entry.get() if hasattr(self, "topic_entry") else "",
            "persona": self.persona_var.get() if hasattr(self, "persona_var") else "",
            "count": self.count_var.get() if hasattr(self, "count_var") else "",
            "github": self.github_var.get() if hasattr(self, "github_var") else True,
            "creator_acknowledged": self.creator_cta_var.get() if hasattr(self, "creator_cta_var") else self.creator_acknowledged,
        }

    def _restore_form_state(self, snapshot: dict):
        provider = snapshot.get("provider")
        model = snapshot.get("model")
        persona = snapshot.get("persona")

        if provider and hasattr(self, "provider_var"):
            self.provider_var.set(provider)
            self._sync_provider_fields(provider)
        if model and hasattr(self, "model_var"):
            self.model_var.set(model)
        if snapshot.get("topic") and hasattr(self, "topic_entry"):
            self.topic_entry.insert(0, snapshot["topic"])
        if persona and hasattr(self, "persona_combo"):
            if persona in self.persona_combo.cget("values"):
                self.persona_var.set(persona)
        if snapshot.get("count") and hasattr(self, "count_var"):
            self.count_var.set(snapshot["count"])
        if hasattr(self, "github_var"):
            self.github_var.set(bool(snapshot.get("github", True)))
        if hasattr(self, "creator_cta_var"):
            self.creator_cta_var.set(bool(snapshot.get("creator_acknowledged", self.creator_acknowledged)))

    def _open_creator_channel(self):
        webbrowser.open(CREATOR_CHANNEL_URL)
        self.status.set("AI쭌 채널을 열었어요. 확인 후 체크해주세요", "done")

    def _save_creator_cta_state(self):
        self.creator_acknowledged = bool(self.creator_cta_var.get())
        config = load_config()
        config["creator_cta_acknowledged"] = self.creator_acknowledged
        save_config(config)

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        shell = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)

        self._build_top_bar(shell)
        self._build_content(shell)
        self.status = StatusBar(shell)
        self.status.grid(row=2, column=0, sticky="ew")

    def _build_top_bar(self, parent):
        top = ctk.CTkFrame(parent, fg_color=SURFACE, height=58, corner_radius=0)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            top,
            text="Thread AI",
            font=ui_font(17, "bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=0, padx=(20, 10), pady=16, sticky="w")

        ctk.CTkLabel(
            top,
            text="AI 뉴스 초안 자동화",
            font=ui_font(12),
            text_color=TEXT_CAPTION,
            anchor="e",
        ).grid(row=0, column=1, padx=(10, 10), pady=16, sticky="e")

        ctk.CTkButton(
            top,
            text="화이트 모드" if self.theme_mode == "dark" else "다크 모드",
            height=32,
            width=96,
            font=ui_font(12, "bold"),
            fg_color=PRIMARY_SOFT,
            hover_color=SECONDARY_HOVER,
            text_color=PRIMARY,
            corner_radius=10,
            command=lambda: self._set_theme_mode("Light" if self.theme_mode == "dark" else "Dark"),
        ).grid(row=0, column=2, padx=(0, 20), pady=14, sticky="e")

        ctk.CTkFrame(parent, fg_color=BORDER, height=1, corner_radius=0).grid(row=0, column=0, sticky="sew")

    def _build_content(self, parent):
        self.scroll = ctk.CTkScrollableFrame(
            parent,
            fg_color=BG,
            scrollbar_button_color=BORDER_STRONG,
            scrollbar_button_hover_color=TEXT_CAPTION,
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll.grid_columnconfigure(0, weight=1)

        container = ctk.CTkFrame(self.scroll, fg_color="transparent")
        container.grid(row=0, column=0, sticky="new", padx=20, pady=(22, 24))
        container.grid_columnconfigure(0, weight=1)

        self._build_hero(container)
        self._build_guide(container)
        self._build_settings(container)
        self._build_controls(container)
        self._build_results(container)

    def _build_hero(self, parent):
        hero = Card(parent)
        hero.grid(row=0, column=0, sticky="ew")
        hero.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hero,
            text="오늘 올릴 AI 스레드를\n한 번에 준비하세요",
            font=ui_font(26, "bold"),
            text_color=TEXT,
            anchor="w",
            justify="left",
        ).grid(row=0, column=0, padx=20, pady=(20, 6), sticky="w")

        ctk.CTkLabel(
            hero,
            text="뉴스와 GitHub 오픈 레포지토리를 모아 내 말투에 맞는 초안을 만듭니다.",
            font=ui_font(14),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=470,
        ).grid(row=1, column=0, padx=20, pady=(0, 18), sticky="w")

        stat_row = ctk.CTkFrame(hero, fg_color="transparent")
        stat_row.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        stat_row.grid_columnconfigure((0, 1, 2), weight=1)

        self._build_metric(stat_row, 0, "모델", "선택 가능")
        self._build_metric(stat_row, 1, "출력", "Markdown")
        self._build_metric(stat_row, 2, "발행", "준비 중")

        cta_row = ctk.CTkFrame(hero, fg_color=MUTED, corner_radius=12)
        cta_row.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="ew")
        cta_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cta_row,
            text="AI쭌 채널을 확인한 뒤 사용해주세요",
            font=ui_font(15, "bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 2))

        ctk.CTkLabel(
            cta_row,
            text="업데이트와 사용 팁은 AI쭌 채널에서 계속 안내합니다. 채널을 열고 확인 체크를 해야 초안 생성이 진행됩니다.",
            font=ui_font(12),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=430,
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))

        action_row = ctk.CTkFrame(cta_row, fg_color="transparent")
        action_row.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 14))
        action_row.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            action_row,
            text="AI쭌 채널 열기",
            height=38,
            width=132,
            font=ui_font(13, "bold"),
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            text_color="white",
            corner_radius=10,
            command=self._open_creator_channel,
        ).grid(row=0, column=0, sticky="w")

        self.creator_cta_var = ctk.BooleanVar(value=self.creator_acknowledged)
        ctk.CTkCheckBox(
            action_row,
            text="채널 확인했어요. 계속 진행할게요",
            variable=self.creator_cta_var,
            command=self._save_creator_cta_state,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=6,
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            text_color=TEXT,
            font=ui_font(12, "bold"),
        ).grid(row=0, column=1, sticky="e")

    def _build_metric(self, parent, column: int, label: str, value: str):
        box = ctk.CTkFrame(parent, fg_color=MUTED, corner_radius=10)
        box.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0 if column == 2 else 6))
        ctk.CTkLabel(
            box,
            text=label,
            font=ui_font(11),
            text_color=TEXT_CAPTION,
            anchor="w",
        ).pack(fill="x", padx=12, pady=(10, 0))
        ctk.CTkLabel(
            box,
            text=value,
            font=ui_font(14, "bold"),
            text_color=TEXT,
            anchor="w",
        ).pack(fill="x", padx=12, pady=(2, 10))

    def _build_guide(self, parent):
        guide = Card(parent)
        guide.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        guide.grid_columnconfigure(0, weight=1)

        SectionHeader(
            guide,
            "처음이라면 여기부터 보세요",
            "이 앱은 뉴스 찾기, 요약, 내 말투로 초안 쓰기, Markdown 저장까지 한 번에 자동화합니다.",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 14))

        flow = ctk.CTkFrame(guide, fg_color="transparent")
        flow.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))
        flow.grid_columnconfigure((0, 1), weight=1)

        self._build_guide_step(flow, 0, 0, "1", "모델 선택", "Ollama, OpenAI, Gemini 중 사용할 모델을 고릅니다.")
        self._build_guide_step(flow, 0, 1, "2", "말투 설정", "기존 글이 없어도 직접 페르소나를 만들 수 있습니다.")
        self._build_guide_step(flow, 1, 0, "3", "주제 입력", "오늘 올릴 AI 주제나 키워드를 입력합니다.")
        self._build_guide_step(flow, 1, 1, "4", "자동 생성", "뉴스와 GitHub 오픈 레포지토리를 모아 초안과 MD 파일을 만듭니다.")

        action_row = ctk.CTkFrame(guide, fg_color=MUTED, corner_radius=12)
        action_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        action_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            action_row,
            text="추천 순서: 모델 설정 저장 -> 페르소나 만들기 -> 주제 입력 -> 초안 생성",
            font=ui_font(13, "bold"),
            text_color=TEXT,
            anchor="w",
            wraplength=360,
            justify="left",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=12)

        ctk.CTkButton(
            action_row,
            text="설정 도우미",
            height=38,
            width=104,
            font=ui_font(13, "bold"),
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            text_color="white",
            corner_radius=10,
            command=self._open_setup_assistant,
        ).grid(row=0, column=1, sticky="e", padx=(8, 8), pady=12)

        ctk.CTkButton(
            action_row,
            text="사용법 보기",
            height=38,
            width=96,
            font=ui_font(13, "bold"),
            fg_color=PRIMARY_SOFT,
            hover_color=SECONDARY_HOVER,
            text_color=TEXT,
            corner_radius=10,
            command=self._open_help_window,
        ).grid(row=0, column=2, sticky="e", padx=(0, 14), pady=12)

    def _build_guide_step(self, parent, row: int, column: int, number: str, title: str, body: str):
        step = ctk.CTkFrame(parent, fg_color=MUTED, border_width=1, border_color=BORDER, corner_radius=12)
        step.grid(row=row, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0 if column == 1 else 6), pady=(0, 10))
        step.grid_columnconfigure(1, weight=1)

        badge = ctk.CTkFrame(step, width=30, height=30, fg_color=PRIMARY, corner_radius=999)
        badge.grid(row=0, column=0, rowspan=2, sticky="n", padx=(12, 10), pady=12)
        badge.grid_propagate(False)
        ctk.CTkLabel(
            badge,
            text=number,
            font=ui_font(13, "bold"),
            text_color="white",
        ).place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            step,
            text=title,
            font=ui_font(13, "bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(12, 2))
        ctk.CTkLabel(
            step,
            text=body,
            font=ui_font(12),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=185,
        ).grid(row=1, column=1, sticky="ew", padx=(0, 12), pady=(0, 12))

    def _open_help_window(self):
        window = ctk.CTkToplevel(self)
        window.title("Thread AI 사용법")
        window.geometry("560x680")
        window.minsize(460, 560)
        window.configure(fg_color=BG)
        window.transient(self)
        window.lift()

        shell = ctk.CTkFrame(window, fg_color=BG, corner_radius=0)
        shell.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            shell,
            text="Thread AI는 어떻게 자동화되나요?",
            font=ui_font(23, "bold"),
            text_color=TEXT,
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            shell,
            text="매일 반복되는 뉴스 탐색, 요약, 글 구조 잡기, 저장 과정을 하나의 파이프라인으로 묶어줍니다.",
            font=ui_font(14),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=500,
        ).pack(fill="x", pady=(0, 14))

        guide_text = """1. 모델을 고릅니다
로컬 PC에서 돌릴 때는 Ollama를 사용합니다. 빠른 결과가 필요하면 본인 OpenAI 또는 Gemini API 키를 환경변수로 연결합니다.

2. 페르소나를 만듭니다
기존 글이 있으면 AI 분석을 쓰고, 글이 없어도 직접 설정으로 말투와 글 구조를 저장할 수 있습니다.

3. 주제를 입력합니다
예: AI 에이전트, Claude MCP, 오픈소스 LLM, 바이브코딩 도구처럼 오늘 올리고 싶은 방향을 적습니다.

4. 앱이 자동으로 처리합니다
뉴스 검색과 GitHub 오픈 레포지토리를 수집하고, 중요한 내용을 요약한 뒤, 저장된 페르소나 말투로 Threads 초안을 만듭니다.

5. 결과를 사용합니다
생성된 카드에서 바로 복사할 수 있고, 결과는 data/outputs 폴더에 Markdown 파일로 저장됩니다.

왜 좋은가요?
매일 같은 리서치와 초안 작성 루틴을 줄여줍니다. 사용자는 주제 선택과 최종 검토에 집중하고, 앱은 반복 작업을 맡습니다."""

        body = ctk.CTkTextbox(
            shell,
            font=ui_font(14),
            fg_color=SURFACE,
            border_color=BORDER,
            border_width=1,
            text_color=TEXT_STRONG,
            corner_radius=12,
            wrap="word",
        )
        body.pack(fill="both", expand=True)
        body.insert("1.0", guide_text)
        body.configure(state="disabled")

        ctk.CTkButton(
            shell,
            text="확인",
            height=42,
            font=ui_font(14, "bold"),
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            text_color="white",
            corner_radius=12,
            command=window.destroy,
        ).pack(fill="x", pady=(14, 0))

    def _build_settings(self, parent):
        config = load_config()
        provider = str(config.get("llm_provider", "ollama")).strip().lower()
        if provider not in {"ollama", "openai", "gemini"}:
            provider = "ollama"

        settings = Card(parent)
        settings.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        settings.grid_columnconfigure(0, weight=1)

        SectionHeader(
            settings,
            "모델 설정",
            "처음 실행했다면 설정 도우미로 provider, 모델명, API 키 등록까지 한 번에 끝낼 수 있습니다.",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 14))

        model_grid = ctk.CTkFrame(settings, fg_color="transparent")
        model_grid.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))
        model_grid.grid_columnconfigure(0, weight=1)
        model_grid.grid_columnconfigure(1, weight=1)

        provider_box = ctk.CTkFrame(model_grid, fg_color="transparent")
        provider_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(
            provider_box,
            text="Provider",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).pack(fill="x")

        self.provider_var = ctk.StringVar(value=provider)
        self.provider_combo = ctk.CTkComboBox(
            provider_box,
            variable=self.provider_var,
            values=["ollama", "openai", "gemini"],
            height=40,
            fg_color=MUTED,
            border_color=BORDER,
            button_color=BORDER,
            button_hover_color=BORDER_STRONG,
            dropdown_fg_color=SURFACE,
            dropdown_text_color=TEXT,
            text_color=TEXT,
            font=ui_font(13),
            corner_radius=12,
            state="readonly",
            command=self._on_provider_changed,
        )
        self.provider_combo.pack(fill="x", pady=(8, 0))

        model_box = ctk.CTkFrame(model_grid, fg_color="transparent")
        model_box.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(
            model_box,
            text="모델명",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).pack(fill="x")

        self.model_var = ctk.StringVar(value=self._get_model_for_provider(provider, config))
        self.model_combo = ctk.CTkComboBox(
            model_box,
            variable=self.model_var,
            values=self._get_model_options(provider, self.model_var.get()),
            height=40,
            fg_color=MUTED,
            border_color=BORDER,
            button_color=BORDER,
            button_hover_color=BORDER_STRONG,
            dropdown_fg_color=SURFACE,
            dropdown_text_color=TEXT,
            text_color=TEXT,
            font=ui_font(13),
            corner_radius=12,
            state="normal",
        )
        self.model_combo.pack(fill="x", pady=(8, 0))

        status_row = ctk.CTkFrame(settings, fg_color=MUTED, corner_radius=12)
        status_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        status_row.grid_columnconfigure(0, weight=1)

        self.api_status_label = ctk.CTkLabel(
            status_row,
            text="",
            font=ui_font(13, "bold"),
            text_color=TEXT,
            anchor="w",
            justify="left",
            wraplength=320,
        )
        self.api_status_label.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 2))

        self.api_hint_label = ctk.CTkLabel(
            status_row,
            text="",
            font=ui_font(12),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=320,
        )
        self.api_hint_label.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))

        self.save_settings_btn = ctk.CTkButton(
            status_row,
            text="설정 저장",
            height=38,
            width=92,
            font=ui_font(13, "bold"),
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            text_color="white",
            corner_radius=10,
            command=self._save_settings,
        )
        self.save_settings_btn.grid(row=0, column=2, rowspan=2, sticky="e", padx=(8, 6), pady=12)

        self.load_models_btn = ctk.CTkButton(
            status_row,
            text="모델 불러오기",
            height=38,
            width=116,
            font=ui_font(13, "bold"),
            fg_color=MUTED_STRONG,
            hover_color=BORDER_STRONG,
            text_color=TEXT,
            corner_radius=10,
            command=self._load_provider_models,
        )
        self.load_models_btn.grid(row=0, column=1, rowspan=2, sticky="e", padx=(8, 0), pady=12)

        self.api_key_btn = ctk.CTkButton(
            status_row,
            text="설정 도우미",
            height=38,
            width=104,
            font=ui_font(13, "bold"),
            fg_color=PRIMARY_SOFT,
            hover_color=SECONDARY_HOVER,
            text_color=TEXT,
            corner_radius=10,
            command=self._open_setup_assistant,
        )
        self.api_key_btn.grid(row=0, column=3, rowspan=2, sticky="e", padx=(0, 14), pady=12)
        self._update_api_status()

    def _get_model_for_provider(self, provider: str, config: dict | None = None) -> str:
        config = config or load_config()
        key = f"{provider}_model"
        return normalize_model_name(provider, str(config.get(key, get_default_model(provider))).strip())

    def _get_model_options(self, provider: str, selected: str | None = None) -> list[str]:
        options = get_model_presets(provider)
        selected = normalize_model_name(provider, selected)
        if selected and selected not in options:
            options.insert(0, selected)
        return options

    def _on_provider_changed(self, provider: str):
        provider = provider.strip().lower()
        model = self._get_model_for_provider(provider)
        self.model_combo.configure(values=self._get_model_options(provider, model))
        self.model_var.set(model)
        self._update_api_status()

    def _load_provider_models(self):
        provider = self.provider_var.get().strip().lower()
        self.load_models_btn.configure(state="disabled", text="불러오는 중")
        self.status.set(f"{provider} 모델 목록을 불러오는 중이에요", "running")

        def worker():
            try:
                models = list_available_models(provider)
                self.after(0, self._on_models_loaded, provider, models)
            except Exception as exc:
                self.after(0, self._on_models_load_error, exc)

        threading.Thread(target=worker, daemon=True).start()

    def _on_models_loaded(self, provider: str, models: list[str]):
        current = normalize_model_name(provider, self.model_var.get())
        values = models or self._get_model_options(provider, current)
        if current and current not in values:
            values.insert(0, current)
        self.model_combo.configure(values=values)
        if values and not current:
            self.model_var.set(values[0])
        self.load_models_btn.configure(state="normal", text="모델 불러오기")
        self.status.set(f"{len(values)}개 모델을 불러왔어요", "done")

    def _on_models_load_error(self, error: Exception):
        self.load_models_btn.configure(state="normal", text="모델 불러오기")
        self.status.set(format_user_error(error), "error")

    def _update_api_status(self):
        provider = self.provider_var.get().strip().lower()
        env_name = get_env_name_for_provider(provider)

        if env_name:
            has_key = has_api_key_for_provider(provider)
            text = f"{env_name} 등록됨" if has_key else f"{env_name} 등록이 필요해요"
            color = SUCCESS if has_key else WARNING
            hint = "키는 Windows 사용자 환경변수에 저장됩니다. 앱 설정 파일에는 저장하지 않습니다."
            self.api_key_btn.configure(text="API 키 관리")
        else:
            text = "로컬 Ollama 모델 사용"
            color = PRIMARY
            hint = "API 키는 필요 없지만, Ollama 설치와 모델 pull이 필요합니다. PC 성능에 따라 속도가 달라집니다."
            self.api_key_btn.configure(text="설정 도우미")

        self.api_status_label.configure(text=text, text_color=color)
        self.api_hint_label.configure(text=hint)

    def _save_settings(self):
        provider = self.provider_var.get().strip().lower()
        if provider not in {"ollama", "openai", "gemini"}:
            self.status.set("지원하지 않는 provider입니다", "error")
            return

        raw_model = self.model_var.get().strip()
        model = normalize_model_name(provider, raw_model)
        if not model:
            self.api_status_label.configure(text="모델명을 입력해주세요", text_color=WARNING)
            return
        notice = get_model_alias_notice(provider, raw_model)

        config = load_config()
        config["llm_provider"] = provider
        config[f"{provider}_model"] = model
        save_config(config)
        self.model_var.set(model)
        self.model_combo.configure(values=self._get_model_options(provider, model))
        self._update_api_status()

        if get_env_name_for_provider(provider) and not has_api_key_for_provider(provider):
            self.status.set("모델 설정은 저장됐고 API 키 등록이 남았어요", "running")
        else:
            self.status.set(notice or "모델 설정을 저장했어요", "done")

    def _open_setup_assistant(self):
        window = ctk.CTkToplevel(self)
        window.title("설정 도우미")
        window.geometry("580x720")
        window.minsize(480, 620)
        window.configure(fg_color=BG)
        window.transient(self)
        window.lift()

        shell = ctk.CTkScrollableFrame(
            window,
            fg_color=BG,
            scrollbar_button_color=BORDER_STRONG,
            scrollbar_button_hover_color=TEXT_CAPTION,
        )
        shell.pack(fill="both", expand=True, padx=20, pady=20)
        shell.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            shell,
            text="처음 설정을 같이 끝내볼게요",
            font=ui_font(24, "bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ctk.CTkLabel(
            shell,
            text="Provider와 모델명을 저장하고, OpenAI/Gemini를 쓸 경우 API 키를 Windows 사용자 환경변수에 등록합니다.",
            font=ui_font(14),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=520,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 14))

        form = Card(shell)
        form.grid(row=2, column=0, sticky="ew")
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form,
            text="1. 사용할 모델 provider",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 0))

        self.setup_provider_var = ctk.StringVar(value=self.provider_var.get())
        self.setup_provider_combo = ctk.CTkComboBox(
            form,
            variable=self.setup_provider_var,
            values=["ollama", "openai", "gemini"],
            height=42,
            fg_color=MUTED,
            border_color=BORDER,
            button_color=BORDER,
            button_hover_color=BORDER_STRONG,
            dropdown_fg_color=SURFACE,
            dropdown_text_color=TEXT,
            text_color=TEXT,
            font=ui_font(13),
            corner_radius=12,
            state="readonly",
            command=self._sync_setup_provider_fields,
        )
        self.setup_provider_combo.grid(row=1, column=0, sticky="ew", padx=18, pady=(8, 14))

        ctk.CTkLabel(
            form,
            text="2. 모델명",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=18)

        self.setup_model_var = ctk.StringVar(value=self.model_var.get())
        self.setup_model_combo = ctk.CTkComboBox(
            form,
            variable=self.setup_model_var,
            values=self._get_model_options(self.setup_provider_var.get(), self.setup_model_var.get()),
            height=42,
            fg_color=MUTED,
            border_color=BORDER,
            button_color=BORDER,
            button_hover_color=BORDER_STRONG,
            dropdown_fg_color=SURFACE,
            dropdown_text_color=TEXT,
            text_color=TEXT,
            font=ui_font(14),
            corner_radius=12,
            state="normal",
        )
        self.setup_model_combo.grid(row=3, column=0, sticky="ew", padx=18, pady=(8, 14))

        ctk.CTkLabel(
            form,
            text="3. API 키 등록",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).grid(row=4, column=0, sticky="ew", padx=18)

        self.setup_key_entry = ctk.CTkEntry(
            form,
            height=42,
            font=ui_font(14),
            fg_color=MUTED,
            border_color=BORDER,
            text_color=TEXT,
            placeholder_text_color=PLACEHOLDER,
            corner_radius=12,
            border_width=1,
            show="*",
        )
        self.setup_key_entry.grid(row=5, column=0, sticky="ew", padx=18, pady=(8, 8))

        self.setup_key_hint = ctk.CTkLabel(
            form,
            text="",
            font=ui_font(12),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=500,
        )
        self.setup_key_hint.grid(row=6, column=0, sticky="ew", padx=18, pady=(0, 14))

        info = ctk.CTkFrame(form, fg_color=MUTED, corner_radius=12)
        info.grid(row=7, column=0, sticky="ew", padx=18, pady=(0, 14))
        info.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            info,
            text="API 키 발급 위치",
            font=ui_font(13, "bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 2))
        ctk.CTkLabel(
            info,
            text="OpenAI: https://platform.openai.com/api-keys\nGemini: https://aistudio.google.com/app/apikey\n저장 위치: Windows 사용자 환경변수. 다른 사용자에게 배포되는 앱 파일에는 키가 포함되지 않습니다.",
            font=ui_font(12),
            text_color=TEXT_MUTED,
            anchor="w",
            justify="left",
            wraplength=500,
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))

        self.setup_status_label = ctk.CTkLabel(
            form,
            text="설정을 확인한 뒤 저장하고 적용을 누르세요.",
            font=ui_font(13),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.setup_status_label.grid(row=8, column=0, sticky="ew", padx=18, pady=(0, 14))

        button_row = ctk.CTkFrame(form, fg_color="transparent")
        button_row.grid(row=9, column=0, sticky="ew", padx=18, pady=(0, 18))
        button_row.grid_columnconfigure(0, weight=1)

        self.setup_delete_key_btn = ctk.CTkButton(
            button_row,
            text="키 삭제",
            height=42,
            width=92,
            font=ui_font(13, "bold"),
            fg_color=PRIMARY_SOFT,
            hover_color=SECONDARY_HOVER,
            text_color=TEXT,
            corner_radius=12,
            command=self._delete_setup_api_key,
        )
        self.setup_delete_key_btn.grid(row=0, column=1, sticky="e", padx=(8, 0))

        ctk.CTkButton(
            button_row,
            text="저장하고 적용",
            height=42,
            width=132,
            font=ui_font(13, "bold"),
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            text_color="white",
            corner_radius=12,
            command=self._save_setup_assistant,
        ).grid(row=0, column=2, sticky="e", padx=(8, 0))

        ctk.CTkButton(
            button_row,
            text="닫기",
            height=42,
            width=82,
            font=ui_font(13, "bold"),
            fg_color=MUTED,
            hover_color=BORDER_STRONG,
            text_color=TEXT,
            corner_radius=12,
            command=window.destroy,
        ).grid(row=0, column=3, sticky="e", padx=(8, 0))

        self._sync_setup_provider_fields(self.setup_provider_var.get())

    def _sync_setup_provider_fields(self, provider: str):
        provider = provider.strip().lower()
        model = self._get_model_for_provider(provider)
        self.setup_model_combo.configure(values=self._get_model_options(provider, model))
        self.setup_model_var.set(model)
        env_name = get_env_name_for_provider(provider)

        self.setup_key_entry.configure(state="normal")
        self.setup_key_entry.delete(0, "end")

        if not env_name:
            self.setup_key_entry.configure(placeholder_text="Ollama는 API 키가 필요하지 않습니다.", state="disabled")
            self.setup_key_hint.configure(
                text="로컬 모델을 쓰려면 Ollama 설치와 모델 pull이 필요합니다. 예: ollama pull gemma4:31b",
                text_color=TEXT_MUTED,
            )
            self.setup_delete_key_btn.configure(state="disabled")
            return

        has_key = has_api_key_for_provider(provider)
        self.setup_key_entry.configure(placeholder_text=f"{env_name} 값을 붙여넣으세요", state="normal")
        self.setup_key_hint.configure(
            text=(
                f"현재 {env_name}가 이미 등록되어 있습니다. 새 키를 입력하면 교체됩니다."
                if has_key
                else f"아직 {env_name}가 등록되지 않았습니다. 키를 붙여넣고 저장하면 바로 사용할 수 있습니다."
            ),
            text_color=SUCCESS if has_key else WARNING,
        )
        self.setup_delete_key_btn.configure(state="normal" if has_key else "disabled")

    def _save_setup_assistant(self):
        provider = self.setup_provider_var.get().strip().lower()
        raw_model = self.setup_model_var.get().strip()
        model = normalize_model_name(provider, raw_model)
        api_key = self.setup_key_entry.get().strip()

        if provider not in {"ollama", "openai", "gemini"}:
            self.setup_status_label.configure(text="지원하지 않는 provider입니다.", text_color=ERROR)
            return
        if not model:
            self.setup_status_label.configure(text="모델명을 입력해주세요.", text_color=WARNING)
            return
        notice = get_model_alias_notice(provider, raw_model)

        config = load_config()
        config["llm_provider"] = provider
        config[f"{provider}_model"] = model
        save_config(config)

        env_name = get_env_name_for_provider(provider)
        if env_name and api_key:
            try:
                save_api_key_for_provider(provider, api_key)
            except Exception as exc:
                self.setup_status_label.configure(text=f"API 키 저장 실패: {exc}", text_color=ERROR)
                return
        elif env_name and not has_api_key_for_provider(provider):
            self.provider_var.set(provider)
            self.model_var.set(model)
            self.model_combo.configure(values=self._get_model_options(provider, model))
            self._update_api_status()
            self.setup_status_label.configure(
                text="모델 설정은 저장됐고 API 키 등록만 남았습니다.",
                text_color=WARNING,
            )
            self.status.set("API 키 등록이 필요해요", "running")
            return

        self.provider_var.set(provider)
        self.model_var.set(model)
        self.model_combo.configure(values=self._get_model_options(provider, model))
        self._update_api_status()
        self._sync_setup_provider_fields(provider)
        self.setup_status_label.configure(text=notice or "설정이 저장됐습니다. 이제 초안을 생성할 수 있어요.", text_color=SUCCESS)
        self.status.set("초기 설정을 저장했어요", "done")

    def _delete_setup_api_key(self):
        provider = self.setup_provider_var.get().strip().lower()
        env_name = get_env_name_for_provider(provider)
        if not env_name:
            self.setup_status_label.configure(text="이 provider는 삭제할 API 키가 없습니다.", text_color=TEXT_MUTED)
            return

        delete_api_key_for_provider(provider)
        self._update_api_status()
        self._sync_setup_provider_fields(provider)
        self.setup_status_label.configure(text=f"{env_name}를 삭제했습니다.", text_color=SUCCESS)
    def _build_controls(self, parent):
        controls = Card(parent)
        controls.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        controls.grid_columnconfigure(0, weight=1)

        SectionHeader(
            controls,
            "마지막 단계: 초안 생성",
            "모델과 페르소나를 준비한 뒤 주제를 입력하면 자동화가 시작됩니다.",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 14))

        ctk.CTkLabel(
            controls,
            text="주제",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=18)

        self.topic_entry = ctk.CTkEntry(
            controls,
            placeholder_text="예: Claude MCP, AI 에이전트, 바이브코딩 도구",
            height=44,
            font=ui_font(14),
            fg_color=MUTED,
            border_color=BORDER,
            text_color=TEXT,
            placeholder_text_color=PLACEHOLDER,
            corner_radius=12,
            border_width=1,
        )
        self.topic_entry.grid(row=2, column=0, sticky="ew", padx=18, pady=(8, 14))
        self.topic_entry.bind("<Return>", lambda e: self._start())

        options = ctk.CTkFrame(controls, fg_color="transparent")
        options.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 14))
        options.grid_columnconfigure(0, weight=1)
        options.grid_columnconfigure(1, weight=1)

        persona_box = ctk.CTkFrame(options, fg_color="transparent")
        persona_box.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkLabel(
            persona_box,
            text="페르소나",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).pack(fill="x")

        self.persona_var = ctk.StringVar()
        self.persona_combo = ctk.CTkComboBox(
            persona_box,
            variable=self.persona_var,
            values=[],
            height=40,
            fg_color=MUTED,
            border_color=BORDER,
            button_color=BORDER,
            button_hover_color=BORDER_STRONG,
            dropdown_fg_color=SURFACE,
            dropdown_text_color=TEXT,
            text_color=TEXT,
            font=ui_font(13),
            corner_radius=12,
            state="readonly",
        )
        self.persona_combo.pack(fill="x", pady=(8, 0))

        count_box = ctk.CTkFrame(options, fg_color="transparent")
        count_box.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        ctk.CTkLabel(
            count_box,
            text="생성 개수",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).pack(fill="x")

        self.count_var = ctk.StringVar(value="3")
        self.count_combo = ctk.CTkComboBox(
            count_box,
            variable=self.count_var,
            values=["1", "2", "3", "5"],
            height=40,
            fg_color=MUTED,
            border_color=BORDER,
            button_color=BORDER,
            button_hover_color=BORDER_STRONG,
            dropdown_fg_color=SURFACE,
            dropdown_text_color=TEXT,
            text_color=TEXT,
            font=ui_font(13),
            corner_radius=12,
            state="readonly",
        )
        self.count_combo.pack(fill="x", pady=(8, 0))

        source_row = ctk.CTkFrame(controls, fg_color=MUTED, corner_radius=12)
        source_row.grid(row=4, column=0, sticky="ew", padx=18, pady=(0, 16))
        source_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            source_row,
            text="GitHub 오픈 레포지토리 포함",
            font=ui_font(14, "bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 0))
        ctk.CTkLabel(
            source_row,
            text="별이 많은 최신 저장소를 함께 참고합니다.",
            font=ui_font(12),
            text_color=TEXT_MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(2, 12))

        self.github_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            source_row,
            text="",
            variable=self.github_var,
            progress_color=PRIMARY,
            button_color=SURFACE,
            button_hover_color=SURFACE,
            width=46,
        ).grid(row=0, column=1, rowspan=2, sticky="e", padx=14, pady=12)

        action_row = ctk.CTkFrame(controls, fg_color="transparent")
        action_row.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 18))
        action_row.grid_columnconfigure(0, weight=1)

        self.persona_btn = ctk.CTkButton(
            action_row,
            text="페르소나 만들기",
            height=44,
            width=128,
            font=ui_font(14, "bold"),
            fg_color=PRIMARY_SOFT,
            hover_color=SECONDARY_HOVER,
            text_color=PRIMARY,
            corner_radius=12,
            command=self._open_persona_setup,
        )
        self.persona_btn.grid(row=0, column=0, sticky="w")

        self.run_btn = ctk.CTkButton(
            action_row,
            text="초안 생성하기",
            height=44,
            width=150,
            font=ui_font(14, "bold"),
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            text_color="white",
            corner_radius=12,
            command=lambda: (append_debug_log("[DEBUG] generate button clicked"), self._start()),
        )
        self.run_btn.grid(row=0, column=1, sticky="e")

    def _build_results(self, parent):
        result_wrap = ctk.CTkFrame(parent, fg_color="transparent")
        result_wrap.grid(row=4, column=0, sticky="ew", pady=(18, 0))
        result_wrap.grid_columnconfigure(0, weight=1)

        result_header = ctk.CTkFrame(result_wrap, fg_color="transparent")
        result_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        result_header.grid_columnconfigure(0, weight=1)

        SectionHeader(
            result_header,
            "스레드 초안",
            "생성된 초안을 검토하고 필요한 항목만 복사하세요.",
        ).grid(row=0, column=0, sticky="ew")

        self.obsidian_btn = ctk.CTkButton(
            result_header,
            text="Obsidian 열기",
            height=38,
            width=120,
            font=ui_font(13, "bold"),
            fg_color=PRIMARY_SOFT,
            hover_color=SECONDARY_HOVER,
            text_color=TEXT,
            corner_radius=10,
            state="disabled",
            command=self._open_latest_output_in_obsidian,
        )
        self.obsidian_btn.grid(row=0, column=1, sticky="e", padx=(12, 0))

        self.result_frame = ctk.CTkFrame(result_wrap, fg_color="transparent")
        self.result_frame.grid(row=1, column=0, sticky="ew")
        self.result_frame.grid_columnconfigure(0, weight=1)
        self._show_empty_state()

    def _show_empty_state(self):
        for w in self.result_frame.winfo_children():
            w.destroy()
        if hasattr(self, "obsidian_btn"):
            self.obsidian_btn.configure(state="disabled")

        empty = Card(self.result_frame)
        empty.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            empty,
            text="아직 생성된 초안이 없어요",
            font=ui_font(16, "bold"),
            text_color=TEXT,
            anchor="center",
        ).pack(fill="x", padx=20, pady=(24, 4))
        ctk.CTkLabel(
            empty,
            text="위 순서대로 설정한 뒤 주제를 입력해보세요.",
            font=ui_font(13),
            text_color=TEXT_MUTED,
            anchor="center",
        ).pack(fill="x", padx=20, pady=(0, 24))

    def _get_latest_output_path(self):
        today = datetime.now().strftime("%Y-%m-%d")
        return OUTPUTS_DIR / f"{today}_threads.md"

    def _open_latest_output_in_obsidian(self):
        output_path = self._get_latest_output_path()
        if not output_path.exists():
            self.status.set("아직 열 수 있는 Markdown 파일이 없어요", "error")
            return

        try:
            _, target_path = open_markdown_in_obsidian(output_path)
            self.status.set(f"Obsidian vault에 복사하고 열었어요: {target_path}", "done")
        except Exception as exc:
            self.status.set(f"Obsidian에서 파일을 열지 못했습니다: {exc}", "error")

    def _refresh_personas(self):
        personas = list_personas()
        if personas:
            self.persona_combo.configure(values=personas)
            cfg = load_config()
            default = cfg.get("default_persona", personas[0])
            self.persona_var.set(default if default in personas else personas[0])
        else:
            self.persona_combo.configure(values=[NO_PERSONA_LABEL])
            self.persona_var.set(NO_PERSONA_LABEL)

    def _open_persona_setup(self):
        PersonaSetupWindow(parent=self, on_complete=self._on_persona_created)

    def _on_persona_created(self, name: str):
        self._refresh_personas()
        self.persona_var.set(name)

    def _start(self):
        persona = self.persona_combo.get()
        append_debug_log(f"[DEBUG] _start called, persona='{persona}'")
        if hasattr(self, "creator_cta_var") and not self.creator_cta_var.get():
            self.status.set("AI쭌 채널을 확인하고 체크해주세요", "error")
            return
        if not persona or persona == NO_PERSONA_LABEL:
            self.status.set("먼저 페르소나 만들기로 말투를 설정해주세요", "error")
            return

        count = int(self.count_var.get())
        topic = self.topic_entry.get().strip()
        include_github = self.github_var.get()
        append_debug_log(f"[DEBUG] count={count}, topic='{topic}', github={include_github}")

        self.run_btn.configure(state="disabled", text="생성 중")
        self.persona_btn.configure(state="disabled")
        self._show_empty_state()
        self.status.set("수집 중이에요", "running")

        threading.Thread(
            target=self._run,
            args=(persona, count, topic, include_github),
            daemon=True,
        ).start()

    def _run(self, persona, count, topic, include_github):
        append_debug_log("[DEBUG] _run thread started")

        def log(msg):
            append_debug_log(f"[LOG] {msg}")
            self.after(0, self.status.set, msg, "running")

        try:
            append_debug_log("[DEBUG] calling run_pipeline...")
            threads = run_pipeline(
                persona,
                count,
                topic=topic,
                include_github=include_github,
                log_callback=log,
            )
            append_debug_log(f"[DEBUG] pipeline done, {len(threads)} threads")
            self.after(0, self._on_done, threads)
        except Exception as e:
            import traceback
            full = traceback.format_exc()
            append_debug_log(f"[ERROR] {full}")
            self.after(0, self._on_error, format_user_error(e))

    def _on_done(self, threads: list[str]):
        self.run_btn.configure(state="normal", text="초안 생성하기")
        self.persona_btn.configure(state="normal")
        self.status.set(f"{len(threads)}개 초안을 만들었어요", "done")
        if hasattr(self, "obsidian_btn") and self._get_latest_output_path().exists():
            self.obsidian_btn.configure(state="normal")

        for w in self.result_frame.winfo_children():
            w.destroy()

        if not threads:
            self._show_empty_state()
            return

        for i, t in enumerate(threads, 1):
            card = ThreadCard(self.result_frame, index=i, text=t)
            card.grid(row=i - 1, column=0, sticky="ew", pady=(0, 10))

    def _on_error(self, msg: str):
        self.run_btn.configure(state="normal", text="초안 생성하기")
        self.persona_btn.configure(state="normal")
        self.status.set("실행 중 오류가 발생했어요", "error")

        for w in self.result_frame.winfo_children():
            w.destroy()

        error_card = Card(self.result_frame)
        error_card.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            error_card,
            text="오류가 발생했어요",
            font=ui_font(16, "bold"),
            text_color=ERROR,
            anchor="w",
        ).pack(fill="x", padx=18, pady=(18, 4))
        ctk.CTkLabel(
            error_card,
            text=msg,
            font=ui_font(12),
            text_color=TEXT_MUTED,
            wraplength=460,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=18, pady=(0, 18))


if __name__ == "__main__":
    App().mainloop()

