import matplotlib.pyplot as plt
from collections import deque
import numpy as np

class LivePlotter:
    def __init__(self, device_names, max_points=100):
        plt.ion()  # modalità interattiva
        self.device_names = device_names
        self.max_points = max_points
        self.fig, self.axes = plt.subplots(len(device_names), 1, figsize=(8, 4*len(device_names)))
        if len(device_names) == 1:
            self.axes = [self.axes]

        self.data = {name: {'roll': deque(maxlen=max_points),
                            'pitch': deque(maxlen=max_points),
                            'yaw': deque(maxlen=max_points)} for name in device_names}

        self.lines = {}
        for ax, name in zip(self.axes, device_names):
            ax.set_title(name)
            ax.set_ylim(-180, 180)
            ax.set_xlim(0, max_points)
            ax.grid(True)
            line_roll,   = ax.plot([], [], label='Roll')
            line_pitch,  = ax.plot([], [], label='Pitch')
            line_yaw,    = ax.plot([], [], label='Yaw')
            ax.legend(loc='upper right')
            self.lines[name] = (line_roll, line_pitch, line_yaw)

    def update(self, device_name, roll, pitch, yaw):
        d = self.data[device_name]
        d['roll'].append(roll)
        d['pitch'].append(pitch)
        d['yaw'].append(yaw)

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
            ax.set_xlim(max(0, len(d['roll'])-self.max_points), len(d['roll']))
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        plt.pause(0.001)

