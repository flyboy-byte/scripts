import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Slider, Button
import matplotlib.patches as patches

class PhasorPMVisualizer:
    def __init__(self):
        # Parameters
        self.carrier_freq = 2.0  # Hz
        self.message_freq = 0.5  # Hz
        self.modulation_index = 1.0
        self.time = 0
        self.dt = 0.05
        self.is_playing = True
        
        # Setup figure
        self.fig = plt.figure(figsize=(14, 6))
        self.fig.suptitle('Interactive Phase Modulation Visualizer', fontsize=16, fontweight='bold')
        
        # Create subplots
        self.ax_phasor = plt.subplot(1, 2, 1)
        self.ax_waveform = plt.subplot(1, 2, 2)
        
        # Adjust layout for sliders
        plt.subplots_adjust(left=0.1, bottom=0.35, right=0.95, top=0.9)
        
        self.setup_phasor_plot()
        self.setup_waveform_plot()
        self.setup_controls()
        
        # Animation
        self.anim = FuncAnimation(self.fig, self.update, interval=50, blit=False)
        
    def setup_phasor_plot(self):
        self.ax_phasor.set_xlim(-1.5, 1.5)
        self.ax_phasor.set_ylim(-1.5, 1.5)
        self.ax_phasor.set_aspect('equal')
        self.ax_phasor.grid(True, alpha=0.3)
        self.ax_phasor.set_title('Rotating Phasor', fontsize=12, fontweight='bold')
        self.ax_phasor.axhline(y=0, color='k', linewidth=0.5)
        self.ax_phasor.axvline(x=0, color='k', linewidth=0.5)
        
        # Draw unit circle
        circle = patches.Circle((0, 0), 1.0, fill=False, linestyle='--', 
                               color='gray', linewidth=2, alpha=0.5)
        self.ax_phasor.add_patch(circle)
        
        # Add angle labels
        angles = [0, 90, 180, 270]
        for angle in angles:
            rad = np.radians(angle)
            x = 1.2 * np.cos(rad)
            y = 1.2 * np.sin(rad)
            self.ax_phasor.text(x, y, f'{angle}°', ha='center', va='center', 
                              fontsize=10, color='gray')
        
        # Initialize phasor elements
        self.phasor_line, = self.ax_phasor.plot([], [], 'b-', linewidth=3, label='Phasor')
        self.phasor_point, = self.ax_phasor.plot([], [], 'ro', markersize=8)
        self.proj_x, = self.ax_phasor.plot([], [], 'r--', linewidth=1, alpha=0.5)
        self.proj_y, = self.ax_phasor.plot([], [], 'r--', linewidth=1, alpha=0.5)
        
        # Text for phase info
        self.phase_text = self.ax_phasor.text(0.02, 0.98, '', transform=self.ax_phasor.transAxes,
                                             verticalalignment='top', fontsize=9,
                                             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
    def setup_waveform_plot(self):
        self.ax_waveform.set_xlim(0, 3)
        self.ax_waveform.set_ylim(-1.5, 1.5)
        self.ax_waveform.grid(True, alpha=0.3)
        self.ax_waveform.set_title('Time Domain Waveform', fontsize=12, fontweight='bold')
        self.ax_waveform.set_xlabel('Time (s)', fontsize=10)
        self.ax_waveform.set_ylabel('Amplitude', fontsize=10)
        self.ax_waveform.axhline(y=0, color='k', linewidth=0.5)
        
        # Initialize waveform elements
        self.pm_line, = self.ax_waveform.plot([], [], 'b-', linewidth=2, label='PM Signal')
        self.msg_line, = self.ax_waveform.plot([], [], 'g-', linewidth=2, 
                                               alpha=0.6, label='Message Signal')
        self.current_marker, = self.ax_waveform.plot([], [], 'ro', markersize=8)
        self.time_marker = self.ax_waveform.axvline(x=0, color='r', linewidth=2, alpha=0.7)
        
        self.ax_waveform.legend(loc='upper right', fontsize=9)
        
    def setup_controls(self):
        # Slider axes
        ax_carrier = plt.axes([0.15, 0.25, 0.3, 0.03])
        ax_message = plt.axes([0.15, 0.20, 0.3, 0.03])
        ax_mod_idx = plt.axes([0.15, 0.15, 0.3, 0.03])
        ax_speed = plt.axes([0.15, 0.10, 0.3, 0.03])
        
        # Create sliders
        self.slider_carrier = Slider(ax_carrier, 'Carrier (Hz)', 0.5, 10.0, 
                                    valinit=self.carrier_freq, valstep=0.1)
        self.slider_message = Slider(ax_message, 'Message (Hz)', 0.1, 2.0, 
                                    valinit=self.message_freq, valstep=0.05)
        self.slider_mod_idx = Slider(ax_mod_idx, 'Mod Index', 0.0, 5.0, 
                                    valinit=self.modulation_index, valstep=0.1)
        self.slider_speed = Slider(ax_speed, 'Speed', 0.1, 3.0, 
                                  valinit=1.0, valstep=0.1)
        
        # Connect sliders
        self.slider_carrier.on_changed(self.update_carrier)
        self.slider_message.on_changed(self.update_message)
        self.slider_mod_idx.on_changed(self.update_mod_idx)
        
        # Buttons
        ax_play = plt.axes([0.6, 0.15, 0.1, 0.04])
        ax_reset = plt.axes([0.75, 0.15, 0.1, 0.04])
        
        self.btn_play = Button(ax_play, 'Pause', color='lightblue', hovercolor='skyblue')
        self.btn_reset = Button(ax_reset, 'Reset', color='lightcoral', hovercolor='salmon')
        
        self.btn_play.on_clicked(self.toggle_play)
        self.btn_reset.on_clicked(self.reset)
        
    def update_carrier(self, val):
        self.carrier_freq = val
        
    def update_message(self, val):
        self.message_freq = val
        
    def update_mod_idx(self, val):
        self.modulation_index = val
        
    def toggle_play(self, event):
        self.is_playing = not self.is_playing
        self.btn_play.label.set_text('Play' if not self.is_playing else 'Pause')
        
    def reset(self, event):
        self.time = 0
        
    def update(self, frame):
        if self.is_playing:
            speed = self.slider_speed.val
            self.time += self.dt * speed
        
        # Calculate current phase
        message_signal = np.sin(2 * np.pi * self.message_freq * self.time)
        phase = 2 * np.pi * self.carrier_freq * self.time + \
                self.modulation_index * message_signal
        
        # Update phasor
        x = np.cos(phase)
        y = np.sin(phase)
        
        self.phasor_line.set_data([0, x], [0, y])
        self.phasor_point.set_data([x], [y])
        self.proj_x.set_data([x, x], [0, y])
        self.proj_y.set_data([0, x], [y, y])
        
        # Update phase text
        phase_deg = np.degrees(phase) % 360
        self.phase_text.set_text(f'Phase: {phase:.2f} rad\nAngle: {phase_deg:.1f}°')
        
        # Update waveform
        time_window = 3.0
        t_start = max(0, self.time - time_window)
        t_array = np.linspace(t_start, self.time, 500)
        
        # Message signal
        msg_signal = np.sin(2 * np.pi * self.message_freq * t_array)
        self.msg_line.set_data(t_array - t_start, msg_signal * 0.7)
        
        # PM signal
        phase_array = 2 * np.pi * self.carrier_freq * t_array + \
                     self.modulation_index * np.sin(2 * np.pi * self.message_freq * t_array)
        pm_signal = np.sin(phase_array)
        self.pm_line.set_data(t_array - t_start, pm_signal)
        
        # Current marker
        current_value = np.sin(phase)
        self.current_marker.set_data([time_window], [current_value])
        self.time_marker.set_xdata([time_window])
        
        # Update x-axis for scrolling effect
        self.ax_waveform.set_xlim(0, time_window)
        
        return (self.phasor_line, self.phasor_point, self.proj_x, self.proj_y,
                self.pm_line, self.msg_line, self.current_marker, self.phase_text)

# Run the visualizer
if __name__ == '__main__':
    visualizer = PhasorPMVisualizer()
    plt.show()