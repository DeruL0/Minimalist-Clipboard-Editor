import tkinter as tk
from tkinter import simpledialog, messagebox
import pyperclip
import keyboard
import sys
import os
import json
import threading

# --- Configuration Management ---
CONFIG_FILE = os.path.expanduser("~/.minimal_clipboard_config.json")
DEFAULT_CONFIG = {
    "font_size": 14,
    "hotkey": "alt+x",
    "autostart": True,
    "always_on_top": True  # Added setting for Always on Top
}


def load_config():
    """Load local cached configuration"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Fill in any missing default configuration keys
                for k, v in DEFAULT_CONFIG.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save configuration to local cache"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Failed to save config: {e}")


def set_autostart(enable=True):
    """Configure Windows autostart (supports enabling and disabling)"""
    if os.name == 'nt':
        import winreg as reg
        try:
            key = reg.HKEY_CURRENT_USER
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            open_key = reg.OpenKey(key, key_path, 0, reg.KEY_ALL_ACCESS)

            if enable:
                # Get the path of the currently running script or packaged exe
                file_path = os.path.realpath(sys.argv[0])
                if file_path.endswith('.py'):
                    python_exe = sys.executable
                    command = f'"{python_exe}" "{file_path}"'
                else:
                    command = f'"{file_path}"'
                reg.SetValueEx(open_key, "MinimalClipboardEditor", 0, reg.REG_SZ, command)
            else:
                # Disable autostart
                try:
                    reg.DeleteValue(open_key, "MinimalClipboardEditor")
                except FileNotFoundError:
                    pass
            reg.CloseKey(open_key)
        except Exception as e:
            print(f"Failed to configure autostart: {e}")


class ClipboardApp:
    def __init__(self):
        # 1. Load local config and apply autostart settings
        self.config = load_config()
        set_autostart(self.config['autostart'])

        self.root = tk.Tk()
        self.root.title("Minimalist Clipboard")
        self.root.geometry("800x600")
        self.root.configure(bg="#F5F5F7")

        # --- 新增：加载自定义窗口图标 ---
        # 支持在本地运行和 PyInstaller 打包后的路径读取
        self.icon_path = "app_icon.ico"
        if hasattr(sys, '_MEIPASS'):
            self.icon_path = os.path.join(sys._MEIPASS, "app_icon.ico")

        if os.path.exists(self.icon_path):
            try:
                self.root.iconbitmap(self.icon_path)
            except Exception as e:
                print(f"Failed to load window icon: {e}")
        # -----------------------------

        # Apply the always-on-top setting (Fixes the screen switching issue)
        self.root.attributes("-topmost", self.config['always_on_top'])

        self.font_size = self.config['font_size']
        self.font_family = "Segoe UI"  # Changed to an English-friendly default font

        # 2. Create top menu bar
        self.menubar = tk.Menu(self.root)
        self.settings_menu = tk.Menu(self.menubar, tearoff=0)

        self.autostart_var = tk.BooleanVar(value=self.config['autostart'])
        self.topmost_var = tk.BooleanVar(value=self.config['always_on_top'])

        self.settings_menu.add_command(label="Change Shortcut...", command=self.change_shortcut)
        self.settings_menu.add_command(label="Change Font Size...", command=self.change_font_size)
        self.settings_menu.add_separator()
        self.settings_menu.add_checkbutton(label="Always on Top", variable=self.topmost_var,
                                           command=self.toggle_topmost)
        self.settings_menu.add_checkbutton(label="Start with Windows", variable=self.autostart_var,
                                           command=self.toggle_autostart)

        self.menubar.add_cascade(label="Settings", menu=self.settings_menu)
        self.root.config(menu=self.menubar)

        # 3. Build main UI (Text area + Scrollbar)
        self.main_frame = tk.Frame(self.root, bg="#F5F5F7")
        self.main_frame.pack(fill="both", expand=True)

        self.scrollbar = tk.Scrollbar(self.main_frame)
        self.scrollbar.pack(side="right", fill="y")

        self.text_area = tk.Text(
            self.main_frame,
            font=(self.font_family, self.font_size),
            bg="#F5F5F7", fg="#1D1D1F", bd=0, highlightthickness=0,
            padx=40, pady=40, wrap="word", insertbackground="#0066CC",
            yscrollcommand=self.scrollbar.set
        )
        self.text_area.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.text_area.yview)

        # 4. Right-click context menu
        self.menu = tk.Menu(self.root, tearoff=0)
        self.menu.add_command(label=f"Hide Window (Shortcut: {self.config['hotkey']})", command=self.hide_window)
        self.menu.add_separator()
        self.menu.add_command(label="Exit Application", command=self.quit_app)
        self.text_area.bind("<Button-3>", self.show_context_menu)

        # Catch window close button to hide instead of quit
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)

        # 5. Register global shortcut
        self.current_hotkey = self.config['hotkey']
        try:
            keyboard.add_hotkey(self.current_hotkey, self.toggle_window)
        except Exception as e:
            messagebox.showerror("Shortcut Error",
                                 f"Cannot bind shortcut {self.current_hotkey}. Please change it in Settings.\n{e}")

        # Mouse wheel zoom events
        self.text_area.bind("<Control-MouseWheel>", self.adjust_font_size)
        self.text_area.bind("<Control-Button-4>", self.adjust_font_size)
        self.text_area.bind("<Control-Button-5>", self.adjust_font_size)

        self.last_clipboard_text = ""
        self.last_editor_text = ""

        self.sync_clipboard()

        welcome_text = (
            "Welcome to the Minimalist Clipboard!\n\n"
            "• New: You can now configure the hotkey, font size, Always on Top, and Windows autostart via the 'Settings' menu in the top-left corner.\n"
            "• Fix: If Alt+Tab / screen switching felt broken, simply uncheck 'Always on Top' in the Settings.\n"
            "• Settings are automatically saved locally and will persist on your next launch.\n"
            "• Automatic Two-Way Sync: Copy externally -> Shows up here; Edit here -> Ready to paste externally.\n"
        )
        self.text_area.insert("1.0", welcome_text)
        self.last_editor_text = self.text_area.get("1.0", "end-1c")

        # 6. Initialize System Tray Icon (Windows bottom-right navigation bar)
        self.setup_tray()

    # --- System Tray Functionality ---
    def setup_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw

            def create_image():
                # --- 修改：优先尝试加载生成的 app_icon.ico 作为托盘图标 ---
                if os.path.exists(self.icon_path):
                    try:
                        return Image.open(self.icon_path)
                    except Exception:
                        pass

                # 如果没有 ico 文件，则回退到动态绘制一个蓝底白字/简单方块
                image = Image.new('RGB', (64, 64), color=(245, 245, 247))
                d = ImageDraw.Draw(image)
                d.rectangle((16, 16, 48, 48), fill="#0066CC")
                return image

            # System tray right-click menu
            menu = pystray.Menu(
                pystray.MenuItem('Show Window', lambda: self.root.after(0, self.show_window)),
                pystray.MenuItem('Exit Application', lambda: self.root.after(0, self.quit_app))
            )

            self.tray_icon = pystray.Icon("MinimalClipboard", create_image(), "Minimal Clipboard", menu)

            # Run tray icon in a separate thread so it doesn't block tkinter mainloop
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except ImportError:
            print("pystray or PIL not installed. Tray icon disabled. Please run: pip install pystray pillow")

    # --- Settings Functionality ---
    def change_shortcut(self):
        new_hotkey = simpledialog.askstring("Change Shortcut",
                                            "Enter a new shortcut\n(e.g., ctrl+shift+z, f12, alt+c):",
                                            initialvalue=self.current_hotkey)
        if new_hotkey and new_hotkey.strip():
            new_hotkey = new_hotkey.lower()
            try:
                # Try unregistering the old one, and register the new one
                keyboard.remove_hotkey(self.current_hotkey)
                keyboard.add_hotkey(new_hotkey, self.toggle_window)

                # Save config
                self.current_hotkey = new_hotkey
                self.config['hotkey'] = new_hotkey
                save_config(self.config)

                # Update context menu text
                self.menu.entryconfig(0, label=f"Hide Window (Shortcut: {new_hotkey})")
                messagebox.showinfo("Success", f"Global shortcut changed to: {new_hotkey}")
            except Exception as e:
                # Rollback on failure
                keyboard.add_hotkey(self.current_hotkey, self.toggle_window)
                messagebox.showerror("Error", f"Invalid shortcut or occupied by system!\n{e}")

    def change_font_size(self):
        new_size = simpledialog.askinteger("Font Size", "Enter font size (8-72):", initialvalue=self.font_size,
                                           minvalue=8, maxvalue=72)
        if new_size:
            self.font_size = new_size
            self.text_area.configure(font=(self.font_family, self.font_size))
            self.config['font_size'] = self.font_size
            save_config(self.config)

    def toggle_topmost(self):
        """Toggle Always on Top behavior"""
        is_topmost = self.topmost_var.get()
        self.root.attributes("-topmost", is_topmost)
        self.config['always_on_top'] = is_topmost
        save_config(self.config)

    def toggle_autostart(self):
        is_enabled = self.autostart_var.get()
        self.config['autostart'] = is_enabled
        save_config(self.config)
        set_autostart(is_enabled)

    def adjust_font_size(self, event):
        """Handle Ctrl+MouseWheel to adjust font size and auto-save"""
        if hasattr(event, 'delta') and event.delta:
            if event.delta < 0:
                self.font_size = max(8, self.font_size - 2)
            else:
                self.font_size = min(72, self.font_size + 2)
        elif hasattr(event, 'num'):
            if event.num == 5:
                self.font_size = max(8, self.font_size - 2)
            elif event.num == 4:
                self.font_size = min(72, self.font_size + 2)

        self.text_area.configure(font=(self.font_family, self.font_size))

        # Save to local config file immediately after wheel adjustment
        self.config['font_size'] = self.font_size
        save_config(self.config)
        return "break"

    # --- Window and Background Control ---
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
        # Stop the tray icon before destroying the window
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.root.destroy()
        sys.exit()

    # --- Core Clipboard Listener ---
    def sync_clipboard(self):
        try:
            current_clipboard = pyperclip.paste()
        except Exception:
            current_clipboard = self.last_clipboard_text

        current_editor = self.text_area.get("1.0", "end-1c")

        # Scenario A: External clipboard updated
        if current_clipboard != self.last_clipboard_text:
            cursor_pos = self.text_area.index(tk.INSERT)
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", current_clipboard)
            try:
                self.text_area.mark_set(tk.INSERT, cursor_pos)
            except:
                pass

            self.last_clipboard_text = current_clipboard
            self.last_editor_text = current_clipboard

        # Scenario B: Internal editor updated
        elif current_editor != self.last_editor_text:
            pyperclip.copy(current_editor)
            self.last_clipboard_text = current_editor
            self.last_editor_text = current_editor

        # Polling check
        self.root.after(200, self.sync_clipboard)


if __name__ == "__main__":
    # Prevent multiple instances running simultaneously (Windows)
    if os.name == 'nt':
        import ctypes

        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "MinimalClipboardEditor_Mutex")
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            tmp_root = tk.Tk()
            tmp_root.withdraw()
            messagebox.showwarning(
                "Already Running",
                "Minimalist Clipboard Editor is already running in the background!\n\n"
                "Please press your shortcut (default Alt+X) or check the system tray in the bottom right."
            )
            sys.exit(0)

    app = ClipboardApp()
    app.root.mainloop()