import sys, os, winreg as reg

def add_to_startup():
    exe_path = os.path.abspath("dist\\Delta Manager.exe")
    key = reg.OpenKey(
        reg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0, reg.KEY_SET_VALUE
    )
    reg.SetValueEx(key, "DeltaManager", 0, reg.REG_SZ, f'"{exe_path}"')
    reg.CloseKey(key)
    print("Added Delta Manager EXE to startup.")

"""
    Install PyInstaller (if you haven’t already):

    pip install pyinstaller
    Generate a one‑file EXE:

    cd path\to\your\project
    pyinstaller --onefile --windowed raphael_manager.py
    --onefile packs everything into a single EXE.

    --windowed suppresses the console window (you can omit it if you want to see stdout).

    After it runs, you’ll find dist\raphael_manager.exe.
"""