"""
One-time installer for the ZPL print tools.

  1. Copies the tool files to a stable per-user location.
  2. Detects available printers and lets you pick one (writes config.json).
  3. Registers .zpl/.epl/.epl2 so double-clicking a file prints it.
  4. Optionally drops a desktop shortcut for the batch GUI.

Run it from the folder that contains all the .py files:

    pip install pywin32
    python install.py

Re-run any time to change the printer or repair the association. No
admin rights needed -- everything is per-user (HKCU + LOCALAPPDATA).
"""
import os
import sys
import json
import shutil
import winreg

import win32print

TOOL_FILES = ("zpl_core.py", "zpl_print.py", "zpl_batch.py")

DEFAULT_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "zpl-tools"
)

ASSOCIATIONS = (
    (".zpl",  "ZPLFile",  "ZPL Label File"),
    (".epl",  "EPLFile",  "EPL Label File"),
    (".epl2", "EPL2File", "EPL2 Label File"),
)


def pick_pythonw():
    """pythonw.exe (no console flash) next to the running interpreter."""
    cand = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return cand if os.path.isfile(cand) else sys.executable


def choose_install_dir():
    print(f"\nInstall location [{DEFAULT_DIR}]")
    ans = input("Press Enter to accept, or type a different path: ").strip()
    return os.path.abspath(ans) if ans else DEFAULT_DIR


def list_printers():
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return [p[2] for p in win32print.EnumPrinters(flags)]


def choose_printer(existing):
    printers = list_printers()
    if not printers:
        print("No printers detected. Connect the printer and re-run.")
        sys.exit(1)
    try:
        default = win32print.GetDefaultPrinter()
    except Exception:
        default = None

    print("\nDetected printers:")
    for i, name in enumerate(printers, 1):
        tags = []
        if name == existing:
            tags.append("current config")
        if name == default:
            tags.append("system default")
        suffix = f"   [{', '.join(tags)}]" if tags else ""
        print(f"  {i}. {name}{suffix}")

    while True:
        raw = input("\nChoose a printer by number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(printers):
            return printers[int(raw) - 1]
        print("Invalid choice.")


def install_files(dest):
    os.makedirs(dest, exist_ok=True)
    src_dir = os.path.dirname(os.path.abspath(__file__))
    for fn in TOOL_FILES:
        src = os.path.join(src_dir, fn)
        if not os.path.isfile(src):
            print(f"Missing source file: {fn}")
            print("Run install.py from the folder that contains all the .py files.")
            sys.exit(1)
        target = os.path.join(dest, fn)
        if os.path.abspath(src) == os.path.abspath(target):
            continue  # installing in place; nothing to copy
        shutil.copy2(src, target)
    print(f"Installed tool files to {dest}")


def write_config(dest, printer):
    with open(os.path.join(dest, "config.json"), "w", encoding="utf-8") as f:
        json.dump({"printer": printer}, f, indent=2)
    print(f"Configured printer: {printer}")


def register(dest):
    pythonw = pick_pythonw()
    worker = os.path.join(dest, "zpl_print.py")
    cmd = f'"{pythonw}" "{worker}" "%1"'
    for ext, prog_id, desc in ASSOCIATIONS:
        with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{ext}") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, prog_id)
        with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER, f"Software\\Classes\\{prog_id}") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, desc)
        with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER,
                f"Software\\Classes\\{prog_id}\\shell\\open\\command") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, cmd)
    print("Registered associations: " +
          ", ".join(e for e, _, _ in ASSOCIATIONS))


def desktop_dir(shell):
    """
    Real Desktop path, honoring OneDrive Known Folder Move.

    ~\\Desktop is wrong when the corporate profile redirects Desktop
    into OneDrive, so ask Windows directly and fall back in order:
      1. WScript.Shell SpecialFolders("Desktop")  (redirect-aware)
      2. User Shell Folders registry value (env-expanded)
      3. ~\\Desktop  (last resort)
    Returns a path that actually exists, or None.
    """
    candidates = []
    try:
        candidates.append(shell.SpecialFolders("Desktop"))
    except Exception:
        pass
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion"
            r"\Explorer\User Shell Folders",
        ) as k:
            raw, _ = winreg.QueryValueEx(k, "Desktop")
            candidates.append(os.path.expandvars(raw))
    except Exception:
        pass
    candidates.append(os.path.join(os.path.expanduser("~"), "Desktop"))

    for c in candidates:
        if c and os.path.isdir(c):
            return c
    return None


def make_shortcut(dest):
    try:
        import win32com.client
    except Exception:
        return
    ans = input(
        "\nCreate a desktop shortcut for the batch tool? [y/N]: "
    ).strip().lower()
    if ans != "y":
        return

    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        desktop = desktop_dir(shell)
        if not desktop:
            print("Could not locate a Desktop folder; skipping shortcut.")
            print(f"  Launch the batch tool manually with:\n"
                  f'  pythonw "{os.path.join(dest, "zpl_batch.py")}"')
            return
        lnk = os.path.join(desktop, "ZPL Batch Print.lnk")
        sc = shell.CreateShortcut(lnk)
        sc.TargetPath = pick_pythonw()
        sc.Arguments = f'"{os.path.join(dest, "zpl_batch.py")}"'
        sc.WorkingDirectory = dest
        sc.Save()
        print(f"Created shortcut: {lnk}")
    except Exception as e:
        # A cosmetic shortcut must never fail the install.
        print(f"Could not create desktop shortcut ({e}); skipping.")
        print(f"  Launch the batch tool manually with:\n"
              f'  pythonw "{os.path.join(dest, "zpl_batch.py")}"')


def main():
    print("=== ZPL Tools Installer ===")
    dest = choose_install_dir()

    existing = None
    cfg = os.path.join(dest, "config.json")
    if os.path.isfile(cfg):
        try:
            with open(cfg, encoding="utf-8") as f:
                existing = json.load(f).get("printer")
        except Exception:
            pass

    install_files(dest)
    printer = choose_printer(existing)
    write_config(dest, printer)
    register(dest)
    make_shortcut(dest)

    print("\nDone.")
    print(f"  Double-click any .zpl/.epl/.epl2 file -> prints to '{printer}'.")
    print(f"  Batch tool: pythonw \"{os.path.join(dest, 'zpl_batch.py')}\"")
    print("\nIf double-click opens the wrong app, set it once via:")
    print("  right-click a .zpl > Open with > Choose another app > "
          "Browse to pythonw.exe > Always.")


if __name__ == "__main__":
    main()
