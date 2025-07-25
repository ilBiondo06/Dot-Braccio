import threading
import tkinter as tk
from tkinter import ttk
from registration import run, PAYLOAD_MODES, stop_flag
import queue
import re  # per estrarre percentuale e orientazione

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Movella DOT Recorder GUI")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.sensor_labels = {} # Dizionario per le label dei sensori

        # Coda per i messaggi di stato
        self.log_queue = queue.Queue()
        self._build()
        self._poll_log_queue()

    def _poll_log_queue(self):
        """
        Ogni 100 ms controlla se la coda ha nuovi messaggi.
        Se arriva una riga di stato, la parsifica:
         - Estrae i dati Roll/Pitch/Yaw
         - Estrae il valore di progresso
         - Aggiorna la Label e la Progressbar
        """
        while not self.log_queue.empty():
            txt = self.log_queue.get_nowait().strip()

            #intercetta la lista sensori
            if txt.startswith("SENSOR_LIST:"):
                names_str = txt.split(":", 1)[1].strip()
                names = [n.strip() for n in names_str.split(",") if n.strip()]
                self.create_sensor_label(names)
                continue

            # Parsing valori sensori (es: DOT3: Roll: 12.34, Pitch: 56.78, Yaw: 90.12)
            m = re.match(r"([A-Za-z0-9_]+):\s*Roll:\s*([-\d.]+),\s*Pitch:\s*([-\d.]+),\s*Yaw:\s*([-\d.]+)", txt)
            if m:
                nome, roll, pitch, yaw = m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4))
                self.update_sensors_value(nome, roll, pitch, yaw)
                continue  # Non aggiungere questa riga al log

            if "Progress:" in txt:
                m = re.search(
                    r"^(?P<orient>.*)\|\s*Progress:\s*\[(?P<bar>[=\-]+)\]\s*(?P<elapsed>\d+)/(?P<dur>\d+)\s*sec.*", 
                    txt
                )
                if m:
                    orient = m.group("orient").strip()
                    elapsed = int(m.group("elapsed"))
                    dur = int(m.group("dur"))
                    # Calcolo percentuale
                    percent = int((elapsed / dur) * 100)
                    # Aggiorna la Label col testo di orientazione (o indicatore "DONE")
                    if "DONE" in txt:
                        self.status_lbl.config(text=orient + " | DONE")
                        self.progress_var.set(100)
                    else:
                        self.status_lbl.config(text=orient)
                        self.progress_var.set(percent)
                else:
                    # Un altro formato (es. "Recording stopped by user.")
                    self.status_lbl.config(text=txt)
            else:
                # Qualunque altra linea (es. messaggi di connessione) la appendiamo su log_testo
                self.log_testo.configure(state="normal")
                self.log_testo.insert(tk.END, txt + "\n")
                self.log_testo.configure(state="disabled")
                self.log_testo.see(tk.END)

        self.after(100, self._poll_log_queue)

    def _build(self):
        frm = ttk.Frame(self, padding=10)
        frm.grid(row=0, column=0, sticky="nsew")
        for i in range(11):
            frm.grid_rowconfigure(i, weight=0)
        frm.grid_rowconfigure(11, weight=1)
        for col in range(3):
            frm.grid_columnconfigure(col, weight=1)

        # ==== Row 0: Filter Profile ====
        ttk.Label(frm, text="Filter Profile").grid(row=0, column=0, sticky="w")
        self.filt = ttk.Combobox(frm, values=["General", "Dynamic"])
        self.filt.grid(row=0, column=1, sticky="ew")
        self.filt.set("General")

        # ==== Row 1: Payload Mode ====
        ttk.Label(frm, text="Payload Mode").grid(row=1, column=0, sticky="w")
        self.mode = ttk.Combobox(frm, values=list(PAYLOAD_MODES.keys()))
        self.mode.grid(row=1, column=1, sticky="ew")
        self.mode.set("custom4")

        # ==== Row 2: Duration ====
        ttk.Label(frm, text="Duration (s, blank=indefinite)").grid(row=2, column=0, sticky="w")
        self.dur = ttk.Entry(frm)
        self.dur.grid(row=2, column=1, sticky="ew")

        # ==== Row 3: Rate ====
        ttk.Label(frm, text="Rate (Hz)").grid(row=3, column=0, sticky="w")
        allowed_rates = ["1", "4", "10", "12", "15", "20", "30", "60", "120"]
        self.rate = ttk.Combobox(frm, values=allowed_rates)
        self.rate.grid(row=3, column=1, sticky="ew")
        self.rate.set("30")

        # ==== Row 4: Save on CSV + File Name ====
        self.save_csv = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Save on CSV", variable=self.save_csv, command=self._toggle_filename
        ).grid(row=4, column=0, sticky="w")

        self.filename_entry = ttk.Entry(frm)
        self.filename_entry.grid(row=4, column=1, sticky="ew")
        self.filename_entry.insert(0, "")  # vuoto = nome di default
        self.filename_entry.config(state="normal" if self.save_csv.get() else "disabled")

        # ==== Row 5: Live Display + Sending Checkbox ====
        self.show = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Live Display", variable=self.show
        ).grid(row=5, column=0, sticky="w")

        self.send_flag = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Send to Server", variable=self.send_flag
        ).grid(row=5, column=1, sticky="w")

        # ==== Row 6: Synchronize Checkbox ====
        self.sync_flag = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Synchronize", variable=self.sync_flag
        ).grid(row=6, column=0, sticky="w")

        # ==== Row 7: Pulsanti Start/Stop + Label + Progressbar + Log ====
        # Frame interno per pulsanti
        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=(10, 5), sticky="ew")
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        self.start_btn = ttk.Button(btn_frame, text="Start", command=self.start)
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(5,0))

        # Sensor Values (initially empty)
        self.sensors_frame = ttk.Frame(frm)
        self.sensors_frame.grid(row=8, column=0, columnspan=2, sticky="ew", pady=(10, 5))

        # Progressbar
        self.progress_var = tk.IntVar(value=0)
        self.progress = ttk.Progressbar(frm, orient="horizontal", mode="determinate",
                                        maximum=100, variable=self.progress_var)
        self.progress.grid(row=9, column=0, columnspan=2, sticky="ew", pady=(2,5))

        #Status Label
        self.status_lbl = ttk.Label(frm, text="—")
        self.status_lbl.grid(row=10, column=0, columnspan=2, sticky="ew")

        # ScrolledText per eventuali messaggi di log generici
        self.log_testo = tk.Text(frm, height=12, state="disabled")
        self.log_testo.grid(row=11, column=0, columnspan=2, sticky="nsew")

    def create_sensor_label(self, names):
        # Rimuovi vecchie label
        for lbl in self.sensor_labels.values():
            lbl.destroy()
        self.sensor_labels.clear()
        for i, name in enumerate(names):
            lbl = ttk.Label(self.sensors_frame, text=f"{name}: Roll=--- Pitch=--- Yaw=---", font=("Courier", 11))
            lbl.grid(row=i, column=0, sticky="w")
            self.sensor_labels[name] = lbl

    def update_sensors_value(self, nome, roll, pitch, yaw):
        if nome in self.sensor_labels:
            self.sensor_labels[nome].config(
                text=f"{nome}: Roll={roll:6.2f} Pitch={pitch:6.2f} Yaw={yaw:6.2f}"
            )

    def _toggle_filename(self):
            if self.save_csv.get():
                self.filename_entry.config(state="normal")
            else:
                self.filename_entry.config(state="disabled")

    def start(self):
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        # Pulisce log_testo e status_lbl/progress
        self.log_testo.configure(state="normal")
        self.log_testo.delete("1.0", tk.END)
        self.log_testo.configure(state="disabled")
        self.status_lbl.config(text="—")
        self.progress_var.set(0)

        class Stream:
            def write(_, txt):
                # Qualunque stringa arrivi, la metto in coda
                self.log_queue.put(txt)
            def flush(_): pass

        dur_text = self.dur.get().strip()
        dur_val = int(dur_text) if dur_text else None

        save_csv_val = self.save_csv.get()
        filename_val = self.filename_entry.get().strip() or None

        args = (
            self.filt.get(),
            self.mode.get(),
            dur_val,
            int(self.rate.get()),
            self.show.get(),
            self.send_flag.get(),
            self.sync_flag.get(),
            save_csv_val,    
            filename_val,    
            Stream()
        )
        stop_flag.clear()
        self.thread = threading.Thread(target=self._run, args=args, daemon=True)
        self.thread.start()

    def stop(self):
        stop_flag.set()
        self.stop_btn.config(state="disabled")
        self.start_btn.config(state="normal")

    def _run(self, *args):
        try:
            run(*args)
        finally:
            # Quando termina, ripristino i bottoni
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

if __name__ == "__main__":
    App().mainloop()
