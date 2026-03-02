
# Minimalist Clipboard Editor

A lightweight, distraction-free text editor that seamlessly and instantly synchronizes with your system clipboard in both directions. Built with Python and Tkinter.

##  Features

-   **Two-Way Real-Time Synchronization**:
    
    -   Copy any text outside the app, and it instantly appears in the editor.
        
    -   Type or edit text within the app, and it is instantly saved to your system clipboard. Just `Ctrl+V` anywhere!
        
-   **Global Shortcut**: Press `Alt + X` (default) anywhere, anytime to toggle (hide/show) the editor window instantly.
    
-   **Customizable Settings (New!)**:
    
    -   **Change Shortcut**: Customize the global hotkey to fit your workflow.
        
    -   **Adjust Font Size**: Change it via the menu or by holding `Ctrl` and scrolling the mouse wheel.
        
    -   **Always on Top**: Toggle this off if you want normal `Alt+Tab` / screen switching behavior without the app blocking other windows.
        
    -   **Start with Windows**: Easily toggle autostart behavior.
        
-   **Persistent Configuration**: All settings are automatically saved locally (`~/.minimal_clipboard_config.json`) and persist across app restarts.
    
-   **Distraction-Free UI**: Clean editing space with a pleasing typography setup.
    

## 🛠 Prerequisites

-   **Python 3.x**
    
-   Dependencies: `pyperclip`, `keyboard`
    

Install the required Python packages:

```
pip install pyperclip keyboard
```

##  Running the Script

You can run the script directly from your terminal:

```
python clipboard_editor.py
```

##  Building a Standalone Executable (Windows)

To run this tool completely in the background without any console windows popping up, you can compile it into a `.exe` file using `PyInstaller`.

1.  Install PyInstaller:
    
    ```
    pip install pyinstaller
    ```
    
2.  Build the executable:
    
    ```
    pyinstaller --noconsole --onefile clipboard_editor.py
    ```
    
3.  Locate the `clipboard_editor.exe` inside the generated `dist` folder. Double-click it to run. It will manage its autostart behavior seamlessly based on your settings.
    

## 📖 How to Use

1.  Launch the app. A minimalist window will appear.
    
2.  The app will quietly run in the background if you close the window via the "X" button.
    
3.  **Hide/Show**: Press your configured shortcut (default `Alt + X`).
    
4.  **Edit**: Modify text in the window; the system clipboard updates automatically. No need to select and copy!
    
5.  **Settings**: Use the top-left "Settings" menu to customize shortcuts, font size, and window behaviors.
    
6.  **Exit**: Right-click anywhere in the text area and select "Exit Application".
    

## 📄 License

This project is open-source and available under the [MIT License](https://www.google.com/search?q=LICENSE "null"). Feel free to fork, modify, and use it in your daily workflow!