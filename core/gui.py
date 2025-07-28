import threading
import tkinter as tk
from tkinter import ttk
from registration import run, PAYLOAD_MODES, stop_flag, cleanup_all
import queue
import re  # per estrarre percentuale e orientazione
from live_plotter import LivePlotter


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.title("Movella DOT Recorder GUI")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.sensor_labels = {} # Dizionario per le label dei sensori
        self.plotter = None
        self._plotter_initialized = False

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
            if not txt:
                continue

            #intercetta la lista sensori
            if txt.startswith("SENSOR_LIST:"):
                names_str = txt.split(":", 1)[1].strip()
                names = [n.strip() for n in names_str.split(",") if n.strip()]
                self.create_sensor_label(names)
                if not self._plotter_initialized:
                    self.plotter = LivePlotter(names, max_points=100)
                    self._plotter_initialized = True
                continue

            # intercetta il tempo trascorso
            if txt.startswith("Elapsed time:"):
                # Estrae il tempo trascorso in secondi
                m = re.search(r"Elapsed time:\s*([\d.]+)\s*seconds", txt)
                if m:
                    elapsed_sec = float(m.group(1))
                    self.elapsed_lbl.config(text=f"Elapsed: {elapsed_sec:.1f}s")
                continue

            # Parsing valori sensori (es: DOT3: Roll: 12.34, Pitch: 56.78, Yaw: 90.12)
            m = re.match(r"([A-Za-z0-9_]+):\s*Roll:\s*([-\d.]+),\s*Pitch:\s*([-\d.]+),\s*Yaw:\s*([-\d.]+)", txt)
            if m:
                nome, roll, pitch, yaw = m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4))
                self.update_sensors_value(nome, roll, pitch, yaw)
                if self.plotter:
                    self.plotter.update(nome, roll, pitch, yaw)
                    self.plotter.draw()
                continue  # Non aggiungere questa riga al log
            
            # Parsing della barra di progresso e stato
            if txt.startswith("Progress:"):
                m = re.search(r"Progress:\s*\[([=\-]+)\]\s*([\d.]+)/([\d.]+)\s*sec", txt)
                if m:
                    elapsed, dur = float(m.group(2)), float(m.group(3))
                    percent = int((elapsed / dur) * 100)
                    self.progress_var.set(percent)
                continue
            else:
                # Qualunque altra linea (es. messaggi di connessione) la appendiamo su log_testo
                self.log_testo.configure(state="normal")
                self.log_testo.insert(tk.END, txt + "\n")
                self.log_testo.configure(state="disabled")
                self.log_testo.see(tk.END)

        self.after(100, self._poll_log_queue)

    

    def _on_close(self):
        stop_flag.set()
        cleanup_all()
        self.destroy()


    def _build(self):
        frm = ttk.Frame(self, padding=10)
        frm.grid(row=0, column=0, sticky="nsew")
        for r in range(7):
            frm.rowconfigure(r, weight=0)
        frm.rowconfigure(7, weight=1)
        for c in range(2):
            frm.columnconfigure(c, weight=1)

        # — Area 1: Parametri di registrazione —
        param_frame = ttk.LabelFrame(frm, text="Registration Parameters", padding=8)
        param_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,5))
        param_frame.columnconfigure( 0, weight=1)
        param_frame.columnconfigure( 1, weight=1)


        ttk.Label(param_frame, text="Filter Profile").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.filt = ttk.Combobox(param_frame, values=["General","Dynamic"])
        self.filt.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.filt.set("General")

        ttk.Label(param_frame, text="Payload Mode").grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.mode = ttk.Combobox(param_frame, values=list(PAYLOAD_MODES.keys()))
        self.mode.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        self.mode.set("custom4")

        ttk.Label(param_frame, text="Duration (s)").grid(row=2, column=0, sticky="w", padx=5, pady=2)
        self.dur = ttk.Entry(param_frame)
        self.dur.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(param_frame, text="Rate (Hz)").grid(row=3, column=0, sticky="w", padx=5, pady=2)
        self.rate = ttk.Combobox(param_frame, values=["1","4","10","12","15","20","30","60","120"])
        self.rate.grid(row=3, column=1, sticky="ew", padx=5, pady=2)
        self.rate.set("30")

        # — Area 2: Opzioni di run —
        options_frame = ttk.LabelFrame(frm, text="Run Options", padding=8)
        options_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0,5))
        options_frame.columnconfigure(0, weight=1)
        options_frame.columnconfigure(1, weight=1)
        options_frame.columnconfigure(2, weight=1)

        self.save_csv   = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Save on CSV", variable=self.save_csv, command=self._toggle_filename).grid(row=0, column=0, sticky="w", padx=5)

        self.send_flag  = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Send to Server", variable=self.send_flag).grid(row=1, column=0, sticky="w", padx=5)

        self.sync_flag  = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Synchronize", variable=self.sync_flag).grid(row=1, column=1, sticky="w", padx=5)

        self.show = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Live Display", variable=self.show).grid(row=2, column=0, sticky="w", padx=5)

        # abilitare/disabilitare il campo filename
        self.filename_entry = ttk.Entry(options_frame)
        self.filename_entry.grid(row=0, column=1, columnspan=3, sticky="ew", padx=5, pady=(2,5))
        self.filename_entry.config(state="disabled")

        # — Area 3: Controlli e progresso —
        ctrl_frame = ttk.LabelFrame(frm, text="Registration Control", padding=8)
        ctrl_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0,5))
        ctrl_frame.columnconfigure((0,1), weight=1)

        self.start_btn = ttk.Button(ctrl_frame, text="Start", command=self.start)
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0,5))
        self.stop_btn  = ttk.Button(ctrl_frame, text="Stop",  command=self.stop, state="disabled")
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=(5,0))

        self.elapsed_lbl = ttk.Label(ctrl_frame, text="Elapsed: 0.0s")
        self.elapsed_lbl.grid(row=1, column=0, columnspan=2, sticky="w", pady=(5,2))

        self.progress_var = tk.IntVar()
        self.progress     = ttk.Progressbar(ctrl_frame, orient="horizontal",
                                            mode="determinate", maximum=100,
                                            variable=self.progress_var)
        self.progress.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0,2))

        # — Area 4: Sensor display —
        sensor_frame = ttk.LabelFrame(frm, text="Sensors Data", padding=8)
        sensor_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0,5))
        self.sensors_frame = sensor_frame  # user in create_sensor_label

        # — Area 5: Log —
        log_frame = ttk.LabelFrame(frm, text="Log", padding=8)
        log_frame.grid(row=4, column=0, columnspan=2, sticky="nsew")
        frm.rowconfigure(4, weight=1)
        self.log_testo = tk.Text(log_frame, height=8, state="disabled")
        self.log_testo.pack(fill="both", expand=True)


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
        self.log_testo.configure(state="normal")
        self.log_testo.delete("1.0", tk.END)
        self.log_testo.configure(state="disabled")
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
        print("Registration stopped by user.")
        self.stop_btn.config(state="disabled")
        self.start_btn.config(state="normal")

    def _run(self, *args):
        try:
            run(*args)
        finally:
            # Quando termina, ripristino i bottoni
            if not stop_flag.is_set():
                self.log_queue.put("Registration completed successfully.")
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

if __name__ == "__main__":
    App().mainloop()
