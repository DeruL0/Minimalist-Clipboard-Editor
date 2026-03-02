import json
import os
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import keyboard
import pyperclip

# --- Configuration Management ---
CONFIG_FILE = os.path.expanduser("~/.minimal_clipboard_config.json")
DEFAULT_CONFIG = {
    "font_size": 14,
    "hotkey": "alt+x",
    "autostart": True,
    "always_on_top": True,
}
SYNC_INTERVAL_MS = 300
HIGHLIGHT_DEBOUNCE_MS = 250


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Failed to save config: {e}")


def set_autostart(enable=True):
    if os.name != "nt":
        return
    import winreg as reg

    try:
        key = reg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        open_key = reg.OpenKey(key, key_path, 0, reg.KEY_ALL_ACCESS)

        if enable:
            file_path = os.path.realpath(sys.argv[0])
            if file_path.endswith(".py"):
                command = f'"{sys.executable}" "{file_path}"'
            else:
                command = f'"{file_path}"'
            reg.SetValueEx(open_key, "MinimalClipboardEditor", 0, reg.REG_SZ, command)
        else:
            try:
                reg.DeleteValue(open_key, "MinimalClipboardEditor")
            except FileNotFoundError:
                pass
        reg.CloseKey(open_key)
    except Exception as e:
        print(f"Failed to configure autostart: {e}")


class ClipboardApp:
    def __init__(self):
        self.config = load_config()
        set_autostart(self.config["autostart"])

        self.root = tk.Tk()
        self.root.title("Minimalist Clipboard")
        self.root.geometry("800x600")
        self.root.configure(bg="#F5F5F7")

        self.icon_path = "app_icon.ico"
        if hasattr(sys, "_MEIPASS"):
            self.icon_path = os.path.join(sys._MEIPASS, "app_icon.ico")
        if os.path.exists(self.icon_path):
            try:
                self.root.iconbitmap(self.icon_path)
            except Exception as e:
                print(f"Failed to load window icon: {e}")

        self.root.attributes("-topmost", self.config["always_on_top"])

        self.font_size = self.config["font_size"]
        self.font_family = "Segoe UI"

        self.current_file_path = None
        self.last_clipboard_text = ""
        self.last_editor_text = ""
        self.editor_dirty = False
        self._programmatic_update = False
        self._highlight_after_id = None

        self._build_menu()
        self._build_editor()
        self._bind_events()

        welcome_text = (
            "Welcome to the Minimalist Clipboard!\n\n"
            "Clipboard sync is always enabled.\n"
            "Read In File loads .md/.txt content directly into the editor.\n"
            "Markdown highlight is unified for all content.\n"
        )
        self._replace_editor_content(welcome_text, keep_cursor=False)
        self._update_title()

        self.sync_clipboard()
        self.setup_tray()

    def _build_menu(self):
        self.menubar = tk.Menu(self.root)

        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label="New              Ctrl+N", command=self.new_file)
        self.file_menu.add_command(label="Read In File...  Ctrl+O", command=self.open_file)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Save             Ctrl+S", command=self.save_file)
        self.file_menu.add_command(label="Save As...       Ctrl+Shift+S", command=self.save_file_as)
        self.menubar.add_cascade(label="File", menu=self.file_menu)

        self.settings_menu = tk.Menu(self.menubar, tearoff=0)
        self.autostart_var = tk.BooleanVar(value=self.config["autostart"])
        self.topmost_var = tk.BooleanVar(value=self.config["always_on_top"])
        self.settings_menu.add_command(label="Change Shortcut...", command=self.change_shortcut)
        self.settings_menu.add_command(label="Change Font Size...", command=self.change_font_size)
        self.settings_menu.add_separator()
        self.settings_menu.add_checkbutton(
            label="Always on Top",
            variable=self.topmost_var,
            command=self.toggle_topmost,
        )
        self.settings_menu.add_checkbutton(
            label="Start with Windows",
            variable=self.autostart_var,
            command=self.toggle_autostart,
        )
        self.menubar.add_cascade(label="Settings", menu=self.settings_menu)
        self.root.config(menu=self.menubar)

    def _build_editor(self):
        self.main_frame = tk.Frame(self.root, bg="#F5F5F7")
        self.main_frame.pack(fill="both", expand=True)

        self.scrollbar = tk.Scrollbar(self.main_frame)
        self.scrollbar.pack(side="right", fill="y")

        self.text_area = tk.Text(
            self.main_frame,
            font=(self.font_family, self.font_size),
            bg="#F5F5F7",
            fg="#1D1D1F",
            bd=0,
            highlightthickness=0,
            padx=40,
            pady=40,
            wrap="word",
            insertbackground="#0066CC",
            yscrollcommand=self.scrollbar.set,
        )
        self.text_area.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.text_area.yview)

        self._setup_markdown_tags()

        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label=f"Hide Window (Shortcut: {self.config['hotkey']})", command=self.hide_window)
        self.menu.add_separator()
        self.menu.add_command(label="Exit Application", command=self.quit_app)
        self.text_area.bind("<Button-3>", self.show_context_menu)

    def _bind_events(self):
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.current_hotkey = self.config["hotkey"]
        try:
            keyboard.add_hotkey(self.current_hotkey, self.toggle_window)
        except Exception as e:
            messagebox.showerror(
                "Shortcut Error",
                f"Cannot bind shortcut {self.current_hotkey}. Please change it in Settings.\n{e}",
            )

        self.text_area.bind("<Control-MouseWheel>", self.adjust_font_size)
        self.text_area.bind("<Control-Button-4>", self.adjust_font_size)
        self.text_area.bind("<Control-Button-5>", self.adjust_font_size)
        self.text_area.bind("<<Modified>>", self.on_text_modified)
        self.text_area.edit_modified(False)

        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_file_as())
        self.root.bind("<Control-n>", lambda e: self.new_file())

    # --- Tray ---
    def setup_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw

            def create_image():
                if os.path.exists(self.icon_path):
                    try:
                        return Image.open(self.icon_path)
                    except Exception:
                        pass
                image = Image.new("RGB", (64, 64), color=(245, 245, 247))
                draw = ImageDraw.Draw(image)
                draw.rectangle((16, 16, 48, 48), fill="#0066CC")
                return image

            menu = pystray.Menu(
                pystray.MenuItem("Show Window", lambda: self.root.after(0, self.show_window)),
                pystray.MenuItem("Exit Application", lambda: self.root.after(0, self.quit_app)),
            )
            self.tray_icon = pystray.Icon("MinimalClipboard", create_image(), "Minimal Clipboard", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except ImportError:
            print("pystray or PIL not installed. Tray icon disabled.")

    # --- Settings ---
    def change_shortcut(self):
        new_hotkey = simpledialog.askstring(
            "Change Shortcut",
            "Enter a new shortcut\n(e.g., ctrl+shift+z, f12, alt+c):",
            initialvalue=self.current_hotkey,
        )
        if not (new_hotkey and new_hotkey.strip()):
            return

        new_hotkey = new_hotkey.lower()
        try:
            keyboard.remove_hotkey(self.current_hotkey)
            keyboard.add_hotkey(new_hotkey, self.toggle_window)
            self.current_hotkey = new_hotkey
            self.config["hotkey"] = new_hotkey
            save_config(self.config)
            self.menu.entryconfig(0, label=f"Hide Window (Shortcut: {new_hotkey})")
            messagebox.showinfo("Success", f"Global shortcut changed to: {new_hotkey}")
        except Exception as e:
            keyboard.add_hotkey(self.current_hotkey, self.toggle_window)
            messagebox.showerror("Error", f"Invalid shortcut or occupied by system!\n{e}")

    def change_font_size(self):
        new_size = simpledialog.askinteger(
            "Font Size",
            "Enter font size (8-72):",
            initialvalue=self.font_size,
            minvalue=8,
            maxvalue=72,
        )
        if not new_size:
            return
        self.font_size = new_size
        self.text_area.configure(font=(self.font_family, self.font_size))
        self.config["font_size"] = self.font_size
        save_config(self.config)
        self._setup_markdown_tags()
        self._schedule_highlight()

    def toggle_topmost(self):
        is_topmost = self.topmost_var.get()
        self.root.attributes("-topmost", is_topmost)
        self.config["always_on_top"] = is_topmost
        save_config(self.config)

    def toggle_autostart(self):
        is_enabled = self.autostart_var.get()
        self.config["autostart"] = is_enabled
        save_config(self.config)
        set_autostart(is_enabled)

    def adjust_font_size(self, event):
        if hasattr(event, "delta") and event.delta:
            if event.delta < 0:
                self.font_size = max(8, self.font_size - 2)
            else:
                self.font_size = min(72, self.font_size + 2)
        elif hasattr(event, "num"):
            if event.num == 5:
                self.font_size = max(8, self.font_size - 2)
            elif event.num == 4:
                self.font_size = min(72, self.font_size + 2)

        self.text_area.configure(font=(self.font_family, self.font_size))
        self.config["font_size"] = self.font_size
        save_config(self.config)
        self._setup_markdown_tags()
        self._schedule_highlight()
        return "break"

    # --- Unified content flow ---
    def _safe_copy_to_clipboard(self, text):
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            return False

    def _replace_editor_content(self, content, keep_cursor=True):
        cursor_pos = self.text_area.index(tk.INSERT) if keep_cursor else "1.0"
        self._programmatic_update = True
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", content)
        try:
            self.text_area.mark_set(tk.INSERT, cursor_pos)
        except Exception:
            pass
        self.text_area.edit_modified(False)
        self._programmatic_update = False

        self.last_editor_text = content
        self.editor_dirty = False
        self._schedule_highlight()

    def on_text_modified(self, _event=None):
        if self._programmatic_update:
            self.text_area.edit_modified(False)
            return
        if self.text_area.edit_modified():
            self.editor_dirty = True
            self.text_area.edit_modified(False)
            self._schedule_highlight()

    # --- File operations ---
    def _update_title(self):
        if self.current_file_path:
            name = os.path.basename(self.current_file_path)
            self.root.title(f"Minimalist Clipboard - {name}")
        else:
            self.root.title("Minimalist Clipboard")

    def new_file(self):
        self.current_file_path = None
        self._replace_editor_content("", keep_cursor=False)
        self.last_clipboard_text = ""
        self._safe_copy_to_clipboard("")
        self._update_title()

    def _read_text_file_with_fallback(self, file_path):
        for encoding in ("utf-8", "gbk"):
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def open_file(self):
        file_path = filedialog.askopenfilename(
            title="Read In File",
            filetypes=[
                ("Markdown/Text files", "*.md *.markdown *.mdown *.mkd *.txt"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            content = self._read_text_file_with_fallback(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file:\n{e}")
            return

        self.current_file_path = file_path
        self._replace_editor_content(content, keep_cursor=False)
        self.last_clipboard_text = content
        self._safe_copy_to_clipboard(content)
        self._update_title()

    def save_file(self):
        if self.current_file_path:
            self._write_file(self.current_file_path)
        else:
            self.save_file_as()

    def save_file_as(self):
        file_path = filedialog.asksaveasfilename(
            title="Save File",
            filetypes=[
                ("Markdown files", "*.md"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
            defaultextension=".md",
        )
        if not file_path:
            return
        self.current_file_path = file_path
        self._write_file(file_path)
        self._update_title()

    def _write_file(self, file_path):
        content = self.text_area.get("1.0", "end-1c")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file:\n{e}")

    # --- Markdown highlighting ---
    def _setup_markdown_tags(self):
        self.text_area.tag_configure(
            "md_h1",
            font=(self.font_family, self.font_size + 10, "bold"),
            foreground="#1a1a2e",
        )
        self.text_area.tag_configure(
            "md_h2",
            font=(self.font_family, self.font_size + 6, "bold"),
            foreground="#16213e",
        )
        self.text_area.tag_configure(
            "md_h3",
            font=(self.font_family, self.font_size + 3, "bold"),
            foreground="#0f3460",
        )
        self.text_area.tag_configure(
            "md_h4",
            font=(self.font_family, self.font_size + 1, "bold"),
            foreground="#533483",
        )
        self.text_area.tag_configure("md_bold", font=(self.font_family, self.font_size, "bold"))
        self.text_area.tag_configure("md_italic", font=(self.font_family, self.font_size, "italic"))
        self.text_area.tag_configure(
            "md_code",
            font=("Consolas", self.font_size),
            background="#E8E8E8",
            foreground="#D63384",
        )
        self.text_area.tag_configure(
            "md_codeblock",
            font=("Consolas", self.font_size),
            background="#E8E8E8",
            foreground="#1D1D1F",
        )
        self.text_area.tag_configure("md_link", foreground="#0066CC", underline=True)
        self.text_area.tag_configure("md_list", foreground="#0066CC")
        self.text_area.tag_configure("md_blockquote", foreground="#6C757D", lmargin1=20, lmargin2=20)
        self.text_area.tag_configure("md_hr", foreground="#ADB5BD")

    def _clear_markdown_tags(self):
        for tag in [
            "md_h1",
            "md_h2",
            "md_h3",
            "md_h4",
            "md_bold",
            "md_italic",
            "md_code",
            "md_codeblock",
            "md_link",
            "md_list",
            "md_blockquote",
            "md_hr",
        ]:
            self.text_area.tag_remove(tag, "1.0", tk.END)

    def _schedule_highlight(self):
        if self._highlight_after_id:
            self.root.after_cancel(self._highlight_after_id)
        self._highlight_after_id = self.root.after(HIGHLIGHT_DEBOUNCE_MS, self._apply_markdown_highlight)

    def _apply_markdown_highlight(self):
        self._highlight_after_id = None
        self._clear_markdown_tags()

        content = self.text_area.get("1.0", tk.END)
        lines = content.split("\n")
        in_code_block = False

        for i, line in enumerate(lines):
            line_num = i + 1
            line_start = f"{line_num}.0"
            line_end = f"{line_num}.end"

            if line.strip().startswith("```"):
                self.text_area.tag_add("md_codeblock", line_start, line_end)
                in_code_block = not in_code_block
                continue

            if in_code_block:
                self.text_area.tag_add("md_codeblock", line_start, line_end)
                continue

            h_match = re.match(r"^(#{1,6})\s", line)
            if h_match:
                level = len(h_match.group(1))
                self.text_area.tag_add(f"md_h{min(level, 4)}", line_start, line_end)
                continue

            if re.match(r"^(\*{3,}|-{3,}|_{3,})\s*$", line.strip()):
                self.text_area.tag_add("md_hr", line_start, line_end)
                continue

            if line.strip().startswith(">"):
                self.text_area.tag_add("md_blockquote", line_start, line_end)
                continue

            if re.match(r"^\s*([\-\*\+]|\d+\.)\s", line):
                bullet_match = re.match(r"^(\s*[\-\*\+]|\s*\d+\.)", line)
                if bullet_match:
                    self.text_area.tag_add("md_list", line_start, f"{line_num}.{bullet_match.end()}")

            for m in re.finditer(r"(\*\*|__)(.+?)\1", line):
                self.text_area.tag_add("md_bold", f"{line_num}.{m.start()}", f"{line_num}.{m.end()}")

            for m in re.finditer(r"(?<!\*)(\*|_)(?!\*)(.+?)(?<!\*)\1(?!\*)", line):
                self.text_area.tag_add("md_italic", f"{line_num}.{m.start()}", f"{line_num}.{m.end()}")

            for m in re.finditer(r"`([^`]+)`", line):
                self.text_area.tag_add("md_code", f"{line_num}.{m.start()}", f"{line_num}.{m.end()}")

            for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", line):
                self.text_area.tag_add("md_link", f"{line_num}.{m.start()}", f"{line_num}.{m.end()}")

    # --- Window control ---
    def show_context_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def toggle_window(self):
        if self.root.winfo_viewable():
            self.hide_window()
        else:
            self.show_window()

    def hide_window(self):
        self.root.withdraw()

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.text_area.focus_set()

    def quit_app(self):
        if self._highlight_after_id:
            self.root.after_cancel(self._highlight_after_id)
        if hasattr(self, "tray_icon"):
            self.tray_icon.stop()
        self.root.destroy()
        sys.exit()

    # --- Clipboard sync ---
    def sync_clipboard(self):
        try:
            current_clipboard = pyperclip.paste()
        except Exception:
            current_clipboard = self.last_clipboard_text

        if current_clipboard != self.last_clipboard_text:
            self._replace_editor_content(current_clipboard, keep_cursor=True)
            self.last_clipboard_text = current_clipboard
            self.current_file_path = None
            self._update_title()
        elif self.editor_dirty:
            current_editor = self.text_area.get("1.0", "end-1c")
            if current_editor != self.last_editor_text:
                self._safe_copy_to_clipboard(current_editor)
                self.last_clipboard_text = current_editor
                self.last_editor_text = current_editor
            self.editor_dirty = False

        self.root.after(SYNC_INTERVAL_MS, self.sync_clipboard)


if __name__ == "__main__":
    if os.name == "nt":
        import ctypes

        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "MinimalClipboardEditor_Mutex")
        if ctypes.windll.kernel32.GetLastError() == 183:
            tmp_root = tk.Tk()
            tmp_root.withdraw()
            messagebox.showwarning(
                "Already Running",
                "Minimalist Clipboard Editor is already running in the background!\n\n"
                "Please press your shortcut (default Alt+X) or check the system tray in the bottom right.",
            )
            sys.exit(0)

    app = ClipboardApp()
    app.root.mainloop()
