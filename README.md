# Thread AI

Thread AI is a local Windows app that helps creators draft Korean Threads posts from AI news, official announcements, social posts, and GitHub open repositories.

The app collects source material, summarizes the important signals with your selected LLM, rewrites the result in your saved persona style, and saves the drafts as Markdown.

## Features

- Local desktop GUI built with Python and customtkinter.
- Supports Ollama, OpenAI, and Gemini providers.
- Uses each user's own API key when cloud models are selected.
- Keeps API keys out of the repository and app config.
- Collects web, SNS, official, and GitHub open repository signals.
- Generates Korean Threads drafts with a 1/2 body and 2/2 source format.
- Saves Markdown outputs to `%USERPROFILE%\.ai_thread_app\outputs`.
- Can copy the latest Markdown output into an Obsidian vault and open it.
- Includes one-click Windows launch scripts.
- Supports an optional Moneygraphy font folder for consistent UI rendering.
- Supports dark mode and light mode.

## Quick Start

If you are using a vibe-coding tool or AI coding agent, paste this repository URL:

```text
https://github.com/AIjunja/Threads-creator
```

Then ask it to clone the repo and run the Windows launcher.

Fresh Windows PC install:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/AIjunja/Threads-creator/main/install.ps1 | iex"
```

This installer tries to:

- install Git with `winget` when Git is missing
- download the repository ZIP when Git cannot be installed
- install Python 3 with `winget` when Python is missing
- launch `run_app.bat`

Manual Git install:

```powershell
git clone https://github.com/AIjunja/Threads-creator.git
cd Threads-creator
.\run_app.bat
```

The launcher handles Python package installation on first run.

Double-click:

```text
run_app.bat
```

On first run, the launcher creates a virtual environment and installs Python dependencies automatically.

If you prefer PowerShell:

```powershell
cd path\to\thread-ai
.\run_app.bat
```

## Recommended Workflow

1. Open the app.
2. Choose a model provider: `ollama`, `openai`, or `gemini`.
3. If using OpenAI or Gemini, open the setup assistant and register your own API key.
4. Create a persona from existing posts or define one manually.
5. Enter a topic such as `AI agents`, `Claude MCP`, `open-source LLM`, or `vibe coding tools`.
6. Generate drafts.
7. Review, copy, or open the Markdown output in Obsidian.

## LLM Providers

### Ollama

Ollama runs locally and does not require a cloud LLM API key.

Performance depends heavily on the user's computer, model size, CPU, RAM, and GPU. Large local models can be slow on consumer hardware.

Default model:

```text
gemma4:31b
```

### OpenAI

OpenAI requires the user's own `OPENAI_API_KEY`.

The app uses the Responses API with `store=False`.

Default model:

```text
gpt-5.4-mini
```

### Gemini

Gemini requires the user's own `GEMINI_API_KEY`.

Default model:

```text
gemini-2.5-flash
```

## API Key Storage

API keys are saved as Windows user environment variables:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

They are not saved in this repository, the app folder, or `%USERPROFILE%\.ai_thread_app\config.json`.

## Output Files

Generated Markdown files are saved here:

```text
%USERPROFILE%\.ai_thread_app\outputs
```

Obsidian integration copies the latest Markdown output into the active vault under:

```text
AI Thread App/
```

## Startup Notification

Register Windows startup notification:

```text
register_startup.bat
```

Remove it:

```text
unregister_startup.bat
```

## Development

Install dependencies manually:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe app.py
```

Run a syntax check:

```powershell
python -m compileall -q .
```

## Repository Safety

Do not commit:

- `venv/`
- `__pycache__/`
- generated Markdown outputs
- personal personas
- `.env`
- API keys or tokens

## Optional Font

Moneygraphy font files are not included in this public repository because public font-file redistribution is prohibited by the font license.

If you have downloaded the font from the official source, place the files here:

```text
assets/fonts/
```

The app will automatically use `Moneygraphy Rounded` when the files are present. Otherwise it falls back to `Malgun Gothic`.

## License

Code is released under the MIT License.

Fonts are third-party assets. See `THIRD_PARTY_NOTICES.md`.
