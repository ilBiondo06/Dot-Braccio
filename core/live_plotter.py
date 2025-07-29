import matplotlib.pyplot as plt
from collections import deque
import numpy as np

class LivePlotter:
    def __init__(self, device_names, sampling_rate, max_points=None):
        plt.ion()  # modalità interattiva
        self.device_names = device_names
        self.max_points = max_points
        self.dt = 1.0 / sampling_rate
        self.window = 5.0
        if max_points is None:
            self.max_points = int((self.window / self.dt))
        else:
            self.max_points = max_points
        self.fig, self.axes = plt.subplots(len(device_names), 1, figsize=(8, 4*len(device_names)))
        self.fig.subplots_adjust(hspace=0.5)
        if len(device_names) == 1:
            self.axes = [self.axes]

        self.data = {name: {'roll': deque(maxlen= self.max_points),
                            'pitch': deque(maxlen= self.max_points),
                            'yaw': deque(maxlen= self.max_points)} for name in device_names}

        self.lines = {}
        for ax, name in zip(self.axes, device_names):
            ax.set_title(name)
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Angle (°)")
            ax.set_ylim(-180, 180)
            ax.set_xlim(0, self.window)
            ax.grid(True)
            line_roll,   = ax.plot([], [], label='Roll')
            line_pitch,  = ax.plot([], [], label='Pitch')
            line_yaw,    = ax.plot([], [], label='Yaw')
            ax.legend(loc='upper right')
            self.lines[name] = (line_roll, line_pitch, line_yaw)

        self.fig.canvas.draw()
        self.backgrounds = {}
        for ax in self.axes:
            self.backgrounds[ax] = self.fig.canvas.copy_from_bbox(ax.bbox)

        self._draw_counter = 0
        self._draw_every = 2

    def update(self, device_name, roll, pitch, yaw):
        d = self.data[device_name]
        d['roll'].append(roll)
        d['pitch'].append(pitch)
        d['yaw'].append(yaw)

        self._draw_counter += 1
        if self._draw_counter >= self._draw_every:
            self._blit_draw()
            self._draw_counter = 0

    def _blit_draw(self):
        # Per ogni subplot:
        for ax, name in zip(self.axes, self.device_names):
            # 1) Ripristina lo sfondo statico
            self.fig.canvas.restore_region(self.backgrounds[ax])

            # 2) Aggiorna i dati delle linee
            d = self.data[name]
            x = np.arange(len(d['roll']))*self.dt
            for line, vals in zip(self.lines[name],
                                  (d['roll'], d['pitch'], d['yaw'])):
                line.set_data(x, list(vals))

            # 3) Disegna **solo** le linee nel loro bbox
            ax.draw_artist(self.lines[name][0])
            ax.draw_artist(self.lines[name][1])
            ax.draw_artist(self.lines[name][2])

            window = 10.0  # secondi da visualizzare
            t_end = len(d['roll']) * self.dt
            t_start = max(0, t_end - window)
            if t_end <= self.window:
                ax.set_xlim(0, self.window)
            else:
                ax.set_xlim(t_start, t_end)

            # 4) Blit dell’area aggiornata
            self.fig.canvas.blit(ax.bbox)

        # 5) flush events
        self.fig.canvas.flush_events()


    def draw(self):
        # aggiorna i dati e ridisegna
        for i, name in enumerate(self.device_names):
            d = self.data[name]
            x = np.arange(len(d['roll']))
            lines = self.lines[name]
            lines[0].set_data(x, list(d['roll']))
            lines[1].set_data(x, list(d['pitch']))
            lines[2].set_data(x, list(d['yaw']))
            ax = self.axes[i]
            ax.set_xlim(max(0, len(d['roll'])-self.max_points)*self.dt, len(d['roll'])*self.dt)
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.001)