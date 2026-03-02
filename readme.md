# Minimalist Clipboard Editor

A lightweight, distraction-free text editor with two modes: real-time system clipboard synchronization, and a full Markdown file editor with live syntax highlighting. Built with Python and Tkinter.

## Features

### Clipboard Mode (Default)

- **Two-Way Real-Time Sync**: Copy any text outside the app → it instantly appears in the editor. Edit text inside the app → it's instantly written to the clipboard. Just `Ctrl+V` anywhere!
- **Global Shortcut**: Press `Alt+X` (default) anywhere to toggle the window instantly.
- **Live Markdown Highlighting**: Pasting Markdown content automatically renders syntax highlighting within 600 ms — no mode switch needed.

### Markdown File Editor

Access via the **File** menu in the top menu bar.

| Action | Shortcut |
|---|---|
| New file | `Ctrl+N` |
| Open `.md` / `.txt` file | `Ctrl+O` |
| Save | `Ctrl+S` |
| Save As | `Ctrl+Shift+S` |
| Back to Clipboard Mode | File → Back to Clipboard Mode |

- **Syntax Highlighting** — live, debounced (600 ms after last keystroke):
  - Headings `# H1` through `#### H4` — scaled font size + bold
  - **Bold** (`**text**`), *Italic* (`*text*`)
  - Inline code (`` `code` ``) and fenced code blocks (` ``` `)
  - Links `[text](url)`
  - Ordered and unordered lists
  - Blockquotes `>`
  - Horizontal rules `---`
- **Unsaved-changes guard**: switching modes or closing the app prompts you to save if there are unsaved edits.
- **Window title** shows the filename and a `*` marker when the file has been modified.
- **Encoding**: reads files as UTF-8, falls back to GBK; always writes UTF-8.

### General Settings

Accessible via the **Settings** menu.

- **Change Shortcut** — customize the global hotkey.
- **Adjust Font Size** — via menu or `Ctrl + Mouse Wheel`.
- **Always on Top** — disable for normal `Alt+Tab` behavior.
- **Start with Windows** — toggle autostart.
- **Persistent Config** — all settings are saved to `~/.minimal_clipboard_config.json`.

---

## Prerequisites

- **Python 3.x**
- Dependencies: `pyperclip`, `keyboard`, `pystray`, `pillow`

```bash
pip install pyperclip keyboard pystray pillow
```

---

## Running the Script

```bash
python clipboard_editor.py
```

---

## Building a Standalone Executable (Windows)

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile clipboard_editor.py
```

The resulting `clipboard_editor.exe` will be inside the `dist/` folder. Double-click to run; autostart behavior is managed automatically by the app settings.

---

## How to Use

1. Launch the app. A minimalist window appears.
2. Closing the window via **X** hides it to the system tray — the app keeps running.
3. **Hide / Show**: press your configured shortcut (default `Alt+X`), or click the tray icon.
4. **Clipboard mode**: just edit — the clipboard updates automatically.
5. **Markdown editing**: open a file via `Ctrl+O` or create a new one with `Ctrl+N`. Save with `Ctrl+S`.
6. **Return to clipboard sync**: File → *Back to Clipboard Mode*.
7. **Exit**: right-click the text area → *Exit Application*, or use the tray menu.

---

## License

This project is open-source and available under the [MIT License](LICENSE). Feel free to fork, modify, and use it in your daily workflow!
