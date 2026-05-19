"""
Double-click worker: prints one label file to the configured printer.

The installer registers the Windows file association so that opening a
.zpl/.epl/.epl2 file runs:

    pythonw zpl_print.py "<path>"

Silent success; shows a message box on failure.
"""
import os
import sys

import zpl_core


def main():
    if len(sys.argv) < 2:
        zpl_core.error_box("No file specified.")
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.isfile(path):
        zpl_core.error_box(f"File not found:\n{path}")
        sys.exit(1)

    printer = zpl_core.resolve_printer()
    if not printer:
        zpl_core.error_box(
            "No printer configured and no system default found.\n\n"
            "Re-run install.py to choose a printer."
        )
        sys.exit(1)

    try:
        zpl_core.print_file(printer, path)
    except Exception as e:
        zpl_core.error_box(
            f"Print job failed.\n\n"
            f"File:    {os.path.basename(path)}\n"
            f"Printer: {printer}\n\n"
            f"{e}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
