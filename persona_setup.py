import json
import re
import threading
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from config import save_persona
from font_loader import get_ui_font_family
from llm_client import generate_text

BG = "#0b1020"
SURFACE = "#111827"
MUTED = "#1f2937"
BORDER = "#263244"
BORDER_STRONG = "#334155"
PRIMARY = "#3b82f6"
PRIMARY_HOVER = "#2563eb"
PRIMARY_SOFT = "#172554"
TEXT = "#f8fafc"
TEXT_STRONG = "#e5e7eb"
TEXT_MUTED = "#94a3b8"
TEXT_CAPTION = "#64748b"
PLACEHOLDER = "#64748b"
SUCCESS = "#22c55e"
ERROR = "#fb7185"
WARNING = "#f59e0b"
FONT_FAMILY = get_ui_font_family()

ctk.set_appearance_mode("dark")


INVALID_FILENAME_CHARS = set('\\/:*?"<>|')


def ui_font(size=14, weight="normal"):
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight)


def get_textbox_value(widget: ctk.CTkTextbox) -> str:
    return widget.get("1.0", tk.END).strip()


def parse_example_phrases(raw: str) -> list[str]:
    phrases = [part.strip() for part in re.split(r"[,\n]+", raw) if part.strip()]
    return phrases[:8]


def validate_persona_name(name: str) -> str | None:
    if not name:
        return "페르소나 이름을 입력해주세요."
    if any(ch in INVALID_FILENAME_CHARS for ch in name):
        return "페르소나 이름에는 \\, /, :, *, ?, <, >, | 문자를 사용할 수 없어요."
    return None


def analyze_persona(text: str, name: str) -> dict:
    prompt = f"""다음은 한 사람이 작성한 스레드 글 모음입니다.

{text}

이 글들을 분석해서 작성자의 글쓰기 스타일을 JSON 형식으로 정리해주세요.

다음 항목을 포함해야 합니다:
- tone: 말투 특징 (예: \"친근하고 직접적인\", \"전문적이지만 쉬운\")
- structure: 문장 구조 특징 (예: \"짧은 문장, 줄바꿈 많음, 핵심 먼저\")
- example_phrases: 자주 쓰는 표현이나 패턴 리스트 (5개)
- style_notes: 기타 특징 (1-2문장)

JSON만 출력하고 다른 설명은 하지 마세요.
```json
{{
  \"tone\": \"...\",
  \"structure\": \"...\",
  \"example_phrases\": [\"...\", \"...\", \"...\", \"...\", \"...\"],
  \"style_notes\": \"...\"
}}
```"""

    raw = generate_text(prompt)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        persona = json.loads(match.group())
        persona["name"] = name
        persona["source"] = "analysis"
        return persona
    raise ValueError("페르소나 분석 결과를 파싱할 수 없습니다.")


class PersonaSetupWindow:
    def __init__(self, parent=None, on_complete=None):
        self.on_complete = on_complete

        if parent:
            self.root = ctk.CTkToplevel(parent)
            self.root.transient(parent)
        else:
            self.root = ctk.CTk()

        self.root.title("페르소나 설정")
        self.root.geometry("600x760")
        self.root.minsize(500, 660)
        self.root.configure(fg_color=BG)
        self._build_ui()
        self.root.after(100, self.root.lift)
        self.root.after(150, self.name_entry.focus_set)

    def _build_ui(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        shell = ctk.CTkFrame(self.root, fg_color=BG, corner_radius=0)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(shell, fg_color=SURFACE, height=58, corner_radius=0)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            top,
            text="페르소나 설정",
            font=ui_font(17, "bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=0, padx=20, pady=16, sticky="w")
        ctk.CTkFrame(shell, fg_color=BORDER, height=1, corner_radius=0).grid(row=0, column=0, sticky="sew")

        content = ctk.CTkScrollableFrame(
            shell,
            fg_color=BG,
            scrollbar_button_color=BORDER_STRONG,
            scrollbar_button_hover_color=TEXT_CAPTION,
        )
        content.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        content.grid_columnconfigure(0, weight=1)

        self._build_intro(content)
        self._build_form(content)

    def _build_intro(self, parent):
        intro = ctk.CTkFrame(
            parent,
            fg_color=SURFACE,
            border_width=1,
            border_color=BORDER,
            corner_radius=12,
        )
        intro.grid(row=0, column=0, sticky="ew")
        intro.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            intro,
            text="글이 없어도\n내 말투를 직접 만들 수 있어요",
            font=ui_font(24, "bold"),
            text_color=TEXT,
            justify="left",
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 6))
        ctk.CTkLabel(
            intro,
            text="처음 시작하는 사람은 직접 설정을 쓰고, 기존 글이 있다면 AI 분석으로 더 빠르게 만들 수 있습니다.",
            font=ui_font(14),
            text_color=TEXT_MUTED,
            justify="left",
            anchor="w",
            wraplength=520,
        ).grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 18))

    def _build_form(self, parent):
        form = ctk.CTkFrame(
            parent,
            fg_color=SURFACE,
            border_width=1,
            border_color=BORDER,
            corner_radius=12,
        )
        form.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        form.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            form,
            text="페르소나 이름",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 0))

        self.name_var = tk.StringVar(value="persona_default")
        self.name_entry = ctk.CTkEntry(
            form,
            textvariable=self.name_var,
            height=42,
            font=ui_font(14),
            fg_color=MUTED,
            border_color=BORDER,
            text_color=TEXT,
            placeholder_text_color=PLACEHOLDER,
            corner_radius=12,
            border_width=1,
        )
        self.name_entry.grid(row=1, column=0, sticky="ew", padx=18, pady=(8, 14))

        self.mode_var = tk.StringVar(value="직접 설정")
        self.mode_tabs = ctk.CTkSegmentedButton(
            form,
            values=["직접 설정", "AI 분석"],
            variable=self.mode_var,
            command=self._switch_mode,
            height=38,
            font=ui_font(13, "bold"),
            fg_color=MUTED,
            selected_color=PRIMARY,
            selected_hover_color=PRIMARY_HOVER,
            unselected_color=MUTED,
            unselected_hover_color=BORDER,
            text_color="white",
            text_color_disabled=TEXT_CAPTION,
            corner_radius=10,
        )
        self.mode_tabs.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))

        self.frame_holder = ctk.CTkFrame(form, fg_color="transparent")
        self.frame_holder.grid(row=3, column=0, sticky="ew", padx=18)
        self.frame_holder.grid_columnconfigure(0, weight=1)

        self.manual_frame = ctk.CTkFrame(self.frame_holder, fg_color="transparent")
        self.manual_frame.grid(row=0, column=0, sticky="ew")
        self.manual_frame.grid_columnconfigure(0, weight=1)
        self._build_manual_fields(self.manual_frame)

        self.analysis_frame = ctk.CTkFrame(self.frame_holder, fg_color="transparent")
        self.analysis_frame.grid(row=0, column=0, sticky="ew")
        self.analysis_frame.grid_columnconfigure(0, weight=1)
        self._build_analysis_fields(self.analysis_frame)

        bottom = ctk.CTkFrame(form, fg_color="transparent")
        bottom.grid(row=4, column=0, sticky="ew", padx=18, pady=(16, 18))
        bottom.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            bottom,
            text="직접 설정으로 바로 시작할 수 있어요.",
            font=ui_font(13),
            text_color=TEXT_MUTED,
            anchor="w",
        )
        self.status_label.grid(row=0, column=0, sticky="w")

        self.cancel_btn = ctk.CTkButton(
            bottom,
            text="닫기",
            height=42,
            width=86,
            font=ui_font(14, "bold"),
            fg_color=PRIMARY_SOFT,
            hover_color="#1e3a8a",
            text_color=PRIMARY,
            corner_radius=12,
            command=self.root.destroy,
        )
        self.cancel_btn.grid(row=0, column=1, sticky="e", padx=(8, 0))

        self.primary_btn = ctk.CTkButton(
            bottom,
            text="저장하기",
            height=42,
            width=112,
            font=ui_font(14, "bold"),
            fg_color=PRIMARY,
            hover_color=PRIMARY_HOVER,
            text_color="white",
            corner_radius=12,
            command=self._submit,
        )
        self.primary_btn.grid(row=0, column=2, sticky="e", padx=(8, 0))

        self._switch_mode("직접 설정")

    def _build_manual_fields(self, parent):
        ctk.CTkLabel(
            parent,
            text="말투",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        self.tone_box = self._make_textbox(parent, 72)
        self.tone_box.grid(row=1, column=0, sticky="ew", pady=(8, 14))
        self.tone_box.insert("1.0", "친근하고 직접적인 말투. 전문 용어는 쉽게 풀어서 설명")

        ctk.CTkLabel(
            parent,
            text="글 구조",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).grid(row=2, column=0, sticky="ew")
        self.structure_box = self._make_textbox(parent, 82)
        self.structure_box.grid(row=3, column=0, sticky="ew", pady=(8, 14))
        self.structure_box.insert("1.0", "첫 줄은 강한 훅으로 시작. 짧은 문장과 줄바꿈을 많이 사용. 마지막은 질문으로 마무리")

        ctk.CTkLabel(
            parent,
            text="자주 쓰는 표현",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).grid(row=4, column=0, sticky="ew")
        ctk.CTkLabel(
            parent,
            text="쉼표나 줄바꿈으로 구분하세요.",
            font=ui_font(12),
            text_color=TEXT_CAPTION,
            anchor="w",
        ).grid(row=5, column=0, sticky="ew", pady=(4, 8))
        self.phrases_box = self._make_textbox(parent, 78)
        self.phrases_box.grid(row=6, column=0, sticky="ew", pady=(0, 14))
        self.phrases_box.insert("1.0", "쉽게 말하면, 핵심은 이거예요, 지금 중요한 건, 한 줄로 정리하면")

        ctk.CTkLabel(
            parent,
            text="추가 스타일 메모",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).grid(row=7, column=0, sticky="ew")
        self.notes_box = self._make_textbox(parent, 72)
        self.notes_box.grid(row=8, column=0, sticky="ew", pady=(8, 0))
        self.notes_box.insert("1.0", "과장된 표현은 줄이고, 실제로 써먹을 수 있는 시사점을 강조")

    def _build_analysis_fields(self, parent):
        ctk.CTkLabel(
            parent,
            text="기존 글 붙여넣기",
            font=ui_font(13, "bold"),
            text_color=TEXT_STRONG,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(
            parent,
            text="최소 50자 이상 입력해주세요. 현재 메인 앱에서 선택한 모델 설정을 사용합니다.",
            font=ui_font(12),
            text_color=TEXT_CAPTION,
            anchor="w",
            wraplength=520,
        ).grid(row=1, column=0, sticky="ew", pady=(4, 8))
        self.text_area = ctk.CTkTextbox(
            parent,
            height=260,
            font=ui_font(14),
            fg_color=MUTED,
            border_color=BORDER,
            border_width=1,
            text_color=TEXT,
            corner_radius=12,
            wrap="word",
        )
        self.text_area.grid(row=2, column=0, sticky="ew")

    def _make_textbox(self, parent, height: int):
        return ctk.CTkTextbox(
            parent,
            height=height,
            font=ui_font(14),
            fg_color=MUTED,
            border_color=BORDER,
            border_width=1,
            text_color=TEXT,
            corner_radius=12,
            wrap="word",
        )

    def _switch_mode(self, mode: str):
        if mode == "AI 분석":
            self.manual_frame.grid_remove()
            self.analysis_frame.grid()
            self.primary_btn.configure(text="분석 시작")
            self._set_status("기존 글을 분석해 페르소나를 만들어요.", TEXT_MUTED)
        else:
            self.analysis_frame.grid_remove()
            self.manual_frame.grid()
            self.primary_btn.configure(text="저장하기")
            self._set_status("직접 설정으로 바로 시작할 수 있어요.", TEXT_MUTED)

    def _set_status(self, text: str, color: str = TEXT_MUTED):
        self.status_label.configure(text=text, text_color=color)

    def _submit(self):
        if self.mode_var.get() == "AI 분석":
            self._start_analyze()
        else:
            self._save_manual_persona()

    def _save_manual_persona(self):
        name = self.name_var.get().strip()
        name_error = validate_persona_name(name)
        if name_error:
            self._set_status(name_error, WARNING)
            return

        tone = get_textbox_value(self.tone_box)
        structure = get_textbox_value(self.structure_box)
        phrases = parse_example_phrases(get_textbox_value(self.phrases_box))
        notes = get_textbox_value(self.notes_box)

        if not tone or not structure:
            self._set_status("말투와 글 구조는 꼭 입력해주세요.", WARNING)
            return

        persona = {
            "name": name,
            "tone": tone,
            "structure": structure,
            "example_phrases": phrases,
            "style_notes": notes,
            "source": "manual",
        }
        save_persona(name, persona)
        self._on_success(name, persona)

    def _start_analyze(self):
        text = get_textbox_value(self.text_area)
        name = self.name_var.get().strip()
        name_error = validate_persona_name(name)

        if name_error:
            self._set_status(name_error, WARNING)
            return
        if len(text) < 50:
            self._set_status("스레드 글을 더 많이 붙여넣어주세요.", WARNING)
            return

        self.primary_btn.configure(state=tk.DISABLED, text="분석 중")
        self.cancel_btn.configure(state=tk.DISABLED)
        self.mode_tabs.configure(state=tk.DISABLED)
        self._set_status("말투와 구조를 분석하고 있어요.", PRIMARY)
        threading.Thread(target=self._analyze, args=(text, name), daemon=True).start()

    def _analyze(self, text: str, name: str):
        try:
            persona = analyze_persona(text, name)
            save_persona(name, persona)
            self.root.after(0, self._on_success, name, persona)
        except Exception as e:
            self.root.after(0, self._on_error, str(e))

    def _on_success(self, name: str, persona: dict):
        self._set_status("페르소나가 저장됐어요.", SUCCESS)
        self.primary_btn.configure(state=tk.NORMAL, text="완료")
        self.cancel_btn.configure(state=tk.NORMAL)
        self.mode_tabs.configure(state=tk.NORMAL)
        if self.on_complete:
            self.on_complete(name)
        messagebox.showinfo(
            "페르소나 저장 완료",
            f"'{name}' 페르소나를 저장했어요.\n\n톤: {persona.get('tone', '')}\n구조: {persona.get('structure', '')}",
            parent=self.root,
        )
        self.root.destroy()

    def _on_error(self, msg: str):
        self.primary_btn.configure(state=tk.NORMAL, text="분석 시작")
        self.cancel_btn.configure(state=tk.NORMAL)
        self.mode_tabs.configure(state=tk.NORMAL)
        self._set_status("분석에 실패했어요. 설정과 API 키를 확인해주세요.", ERROR)
        messagebox.showerror("분석 실패", msg, parent=self.root)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    PersonaSetupWindow().run()
