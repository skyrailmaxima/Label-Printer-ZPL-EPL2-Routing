"""
Batch print GUI: choose a folder and a printer, send every label
file in the folder to that printer as a RAW job.

Run with:  pythonw zpl_batch.py
"""
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog

import zpl_core


class BatchApp:
    def __init__(self, root):
        self.root = root
        root.title("ZPL Batch Print")
        root.geometry("640x470")
        root.minsize(540, 400)

        pad = {"padx": 10, "pady": 5}

        # --- Printer row ---
        row = ttk.Frame(root)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Printer:").pack(side="left")
        self.printer_var = tk.StringVar()
        self.printer_cb = ttk.Combobox(
            row, textvariable=self.printer_var, state="readonly")
        self.printer_cb.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="Refresh",
                   command=self.refresh_printers).pack(side="left")

        # --- Folder row ---
        row = ttk.Frame(root)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Folder: ").pack(side="left")
        self.folder_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.folder_var).pack(
            side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="Browse...",
                   command=self.pick_folder).pack(side="left")

        # --- Options row ---
        row = ttk.Frame(root)
        row.pack(fill="x", **pad)
        self.recurse_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(row, text="Include subfolders",
                        variable=self.recurse_var).pack(side="left")
        ttk.Label(row, text="    Extensions:").pack(side="left")
        self.exts_var = tk.StringVar(value=".zpl .epl .epl2 .prn")
        ttk.Entry(row, textvariable=self.exts_var,
                  width=26).pack(side="left", padx=6)

        # --- Log ---
        self.log = tk.Text(root, height=14, wrap="word", state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=6)

        # --- Action row ---
        row = ttk.Frame(root)
        row.pack(fill="x", **pad)
        self.status = ttk.Label(row, text="Ready")
        self.status.pack(side="left")
        self.btn = ttk.Button(row, text="Print All", command=self.start)
        self.btn.pack(side="right")

        self.refresh_printers()

    # ---------- UI helpers (call only on main thread) ----------

    def _log(self, line):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _set_status(self, text):
        self.status.configure(text=text)

    def _enable_button(self):
        self.btn.configure(state="normal")

    def ui(self, fn, *args):
        """Schedule a UI mutation on the Tk main loop (thread-safe)."""
        self.root.after(0, fn, *args)

    # ---------- Actions ----------

    def refresh_printers(self):
        printers = zpl_core.list_printers()
        self.printer_cb["values"] = printers
        current = zpl_core.resolve_printer()
        if current and current in printers:
            self.printer_var.set(current)
        elif printers:
            self.printer_var.set(printers[0])

    def pick_folder(self):
        d = filedialog.askdirectory(title="Choose folder of label files")
        if d:
            self.folder_var.set(d)

    def collect(self, folder, exts, recurse):
        out = []
        if recurse:
            for base, _, files in os.walk(folder):
                for fn in files:
                    if os.path.splitext(fn)[1].lower() in exts:
                        out.append(os.path.join(base, fn))
        else:
            for fn in os.listdir(folder):
                p = os.path.join(folder, fn)
                if os.path.isfile(p) and os.path.splitext(fn)[1].lower() in exts:
                    out.append(p)
        return sorted(out)

    def start(self):
        folder = self.folder_var.get().strip()
        printer = self.printer_var.get().strip()
        if not folder or not os.path.isdir(folder):
            self._log("! Choose a valid folder first.")
            return
        if not printer:
            self._log("! Choose a printer first.")
            return

        exts = tuple(
            e if e.startswith(".") else "." + e
            for e in self.exts_var.get().lower().split()
        )
        files = self.collect(folder, exts, self.recurse_var.get())
        if not files:
            self._log(f"No matching files in {folder}")
            return

        self.btn.configure(state="disabled")
        self._log(f"--- Printing {len(files)} file(s) to '{printer}' ---")
        threading.Thread(
            target=self.run_jobs, args=(printer, files), daemon=True
        ).start()

    def run_jobs(self, printer, files):
        ok = fail = 0
        n = len(files)
        for i, path in enumerate(files, 1):
            name = os.path.basename(path)
            try:
                zpl_core.print_file(printer, path)
                ok += 1
                self.ui(self._log, f"[{i}/{n}] OK    {name}")
            except Exception as e:
                fail += 1
                self.ui(self._log, f"[{i}/{n}] FAIL  {name}  ({e})")
            self.ui(self._set_status, f"{i}/{n} processed")
        self.ui(self._log, f"--- Done: {ok} printed, {fail} failed ---")
        self.ui(self._set_status, f"Done: {ok} ok, {fail} failed")
        self.ui(self._enable_button)


if __name__ == "__main__":
    root = tk.Tk()
    BatchApp(root)
    root.mainloop()
