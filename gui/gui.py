import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from registration import run, PAYLOAD_MODES

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Movella DOT Recorder GUI")
        # permetti ridimensionamento
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        frm = ttk.Frame(self, padding=10)
        frm.grid(row=0, column=0, sticky="nsew")
        # configura grid interna
        for i in range(7): frm.grid_rowconfigure(i, weight=0)
        frm.grid_rowconfigure(6, weight=1)
        frm.grid_columnconfigure(1, weight=1)

        ttk.Label(frm, text="Filter Profile").grid(row=0, column=0, sticky="w")
        self.filt = ttk.Combobox(frm, values=["General","Dynamic"])
        self.filt.grid(row=0, column=1, sticky="ew")
        self.filt.set("General")

        ttk.Label(frm, text="Payload Mode").grid(row=1, column=0, sticky="w")
        self.mode = ttk.Combobox(frm, values=list(PAYLOAD_MODES.keys()))
        self.mode.grid(row=1, column=1, sticky="ew")
        self.mode.set("custom4")

        ttk.Label(frm, text="Duration (s)").grid(row=2, column=0, sticky="w")
        self.dur = ttk.Entry(frm)
        self.dur.insert(0, "10")
        self.dur.grid(row=2, column=1, sticky="ew")

        ttk.Label(frm, text="Rate (Hz)").grid(row=3, column=0, sticky="w")
        # combobox per rate limitati
        allowed_rates = ["1","4","10","12","15","20","30","60","120"]
        self.rate = ttk.Combobox(frm, values=allowed_rates)
        self.rate.grid(row=3, column=1, sticky="ew")
        self.rate.set("30")

        self.show = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Live Display", variable=self.show).grid(row=4, column=0, columnspan=2, sticky="w")

        self.btn = ttk.Button(frm, text="Start", command=self.start)
        self.btn.grid(row=5, column=0, columnspan=2, pady=5, sticky="ew")

        self.log = scrolledtext.ScrolledText(frm)
        self.log.grid(row=6, column=0, columnspan=2, sticky="nsew")

    def start(self):
        self.btn.config(state="disabled")
        self.log.delete("1.0", tk.END)

        class Stream:
            def write(_, txt):
                self.log.insert(tk.END, txt)
                self.log.see(tk.END)
            def flush(_): pass

        args = (
            self.filt.get(),
            self.mode.get(),
            int(self.dur.get()),
            int(self.rate.get()),
            self.show.get(),
            Stream()
        )
        threading.Thread(target=self._run, args=args, daemon=True).start()

    def _run(self, *args):
        try:
            run(*args)
        finally:
            self.btn.config(state="normal")

if __name__ == "__main__":
    App().mainloop()