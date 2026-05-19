"""
Shared core for the ZPL print tools: printer discovery, config, raw I/O.

Both zpl_print.py (double-click worker) and zpl_batch.py (folder GUI)
import this. config.json lives next to this file so all three agree on
which printer is selected.
"""
import os
import json
import ctypes
import win32print

_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_HERE, "config.json")


def list_printers():
    """Names of all local printers and network printer connections."""
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return [p[2] for p in win32print.EnumPrinters(flags)]


def default_printer():
    """The system default printer name, or None."""
    try:
        return win32print.GetDefaultPrinter()
    except Exception:
        return None


def load_printer():
    """Configured printer name from config.json, or None if unset/missing."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("printer") or None
    except Exception:
        return None


def save_printer(name):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"printer": name}, f, indent=2)


def resolve_printer():
    """Configured printer, falling back to the system default."""
    return load_printer() or default_printer()


def send_raw(printer_name, data, job_name="ZPL Job"):
    """Push bytes straight to the spooler using the RAW datatype.

    RAW bypasses driver processing entirely, which is what the old
    `net use` + `copy /b` chain effectively did.
    """
    h = win32print.OpenPrinter(printer_name)
    try:
        win32print.StartDocPrinter(h, 1, (job_name, None, "RAW"))
        win32print.StartPagePrinter(h)
        win32print.WritePrinter(h, data)
        win32print.EndPagePrinter(h)
        win32print.EndDocPrinter(h)
    finally:
        win32print.ClosePrinter(h)


def print_file(printer_name, path):
    with open(path, "rb") as f:
        data = f.read()
    send_raw(printer_name, data, os.path.basename(path))


def error_box(msg, title="ZPL Print Error"):
    ctypes.windll.user32.MessageBoxW(0, msg, title, 0x10)
