import tkinter as tk
from tkinter import ttk
import math
import time
import numpy as np

class PWMOscilloscope:
    def __init__(self, root):
        self.root = root
        self.root.title("PWM Oscilloscope")
        self.root.geometry("1200x700")
        
        # PWM parameters
        self.frequency = 1.0  # Start at 1Hz
        self.duty_cycle = 50  # Start at 50%
        self.period = 1.0 / self.frequency
        
        # Oscilloscope parameters
        self.canvas_width = 800
        self.canvas_height = 300
        self.time_window = 3.0  # Show 3 seconds
        self.animation_speed = 1.0
        self.current_time = 0
        
        # Measurement parameters
        self.peak_high = 5.0
        self.peak_low = 0.0
        self.last_measurements = {"high": [], "low": [], "period": []}
        
        # Drawing state
        self.draw_points = []
        
        # Colors
        self.bg_color = "#0a0a0a"
        self.grid_color = "#003300"
        self.signal_high_color = "#00ff00"
        self.signal_low_color = "#ff4444"
        self.trace_color = "#00ffff"
        self.text_color = "#ffffff"
        self.peak_color = "#ffff00"
        
        self.setup_ui()
        self.setup_bindings()
        self.animate()
    
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Oscilloscope Controls", padding="10")
        control_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Frequency control
        ttk.Label(control_frame, text="Frequency (Hz):").grid(row=0, column=0, padx=(0, 5))
        self.freq_var = tk.DoubleVar(value=self.frequency)
        self.freq_scale = ttk.Scale(
            control_frame, 
            from_=0.1, 
            to=5.0, 
            orient=tk.HORIZONTAL,
            length=200,
            variable=self.freq_var,
            command=self.update_frequency
        )
        self.freq_scale.grid(row=0, column=1, padx=(0, 10))
        self.freq_label = ttk.Label(control_frame, text=f"{self.frequency:.1f} Hz")
        self.freq_label.grid(row=0, column=2, padx=(0, 20))
        
        # Duty cycle control
        ttk.Label(control_frame, text="Duty Cycle (%):").grid(row=0, column=3, padx=(0, 5))
        self.duty_var = tk.DoubleVar(value=self.duty_cycle)
        self.duty_scale = ttk.Scale(
            control_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=200,
            variable=self.duty_var,
            command=self.update_duty_cycle
        )
        self.duty_scale.grid(row=0, column=4, padx=(0, 10))
        self.duty_label = ttk.Label(control_frame, text=f"{self.duty_cycle:.0f}%")
        self.duty_label.grid(row=0, column=5, padx=(0, 20))
        
        # Time base control
        ttk.Label(control_frame, text="Time/Div:").grid(row=0, column=6, padx=(0, 5))
        self.timebase_var = tk.DoubleVar(value=self.time_window)
        self.timebase_scale = ttk.Scale(
            control_frame,
            from_=1.0,
            to=10.0,
            orient=tk.HORIZONTAL,
            length=150,
            variable=self.timebase_var,
            command=self.update_timebase
        )
        self.timebase_scale.grid(row=0, column=7, padx=(0, 10))
        self.timebase_label = ttk.Label(control_frame, text=f"{self.time_window:.1f}s")
        self.timebase_label.grid(row=0, column=8)
        
        # Main display area
        display_frame = ttk.Frame(main_frame)
        display_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Oscilloscope screen
        scope_frame = ttk.LabelFrame(display_frame, text="Oscilloscope Display", padding="10")
        scope_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        self.canvas = tk.Canvas(
            scope_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg=self.bg_color,
            highlightthickness=2,
            highlightbackground="#666666"
        )
        self.canvas.grid(row=0, column=0)
        
        # Measurements panel
        measurements_frame = ttk.LabelFrame(display_frame, text="Measurements", padding="10")
        measurements_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Peak measurements
        ttk.Label(measurements_frame, text="Peak Detection:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(measurements_frame, text="High Peak:").grid(row=1, column=0, sticky=tk.W)
        self.peak_high_label = ttk.Label(measurements_frame, text="0.00 V", foreground="green")
        self.peak_high_label.grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(measurements_frame, text="Low Peak:").grid(row=2, column=0, sticky=tk.W)
        self.peak_low_label = ttk.Label(measurements_frame, text="0.00 V", foreground="red")
        self.peak_low_label.grid(row=2, column=1, sticky=tk.W)
        
        ttk.Label(measurements_frame, text="Peak-to-Peak:").grid(row=3, column=0, sticky=tk.W)
        self.peak_pp_label = ttk.Label(measurements_frame, text="0.00 V", foreground="yellow")
        self.peak_pp_label.grid(row=3, column=1, sticky=tk.W)
        
        # Timing measurements
        ttk.Separator(measurements_frame, orient='horizontal').grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        ttk.Label(measurements_frame, text="Timing:", font=("Arial", 10, "bold")).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(measurements_frame, text="Period:").grid(row=6, column=0, sticky=tk.W)
        self.period_label = ttk.Label(measurements_frame, text="0.00 s")
        self.period_label.grid(row=6, column=1, sticky=tk.W)
        
        ttk.Label(measurements_frame, text="Frequency:").grid(row=7, column=0, sticky=tk.W)
        self.freq_measured_label = ttk.Label(measurements_frame, text="0.00 Hz")
        self.freq_measured_label.grid(row=7, column=1, sticky=tk.W)
        
        ttk.Label(measurements_frame, text="Pulse Width:").grid(row=8, column=0, sticky=tk.W)
        self.pulse_width_label = ttk.Label(measurements_frame, text="0.00 s")
        self.pulse_width_label.grid(row=8, column=1, sticky=tk.W)
        
        ttk.Label(measurements_frame, text="Duty Cycle:").grid(row=9, column=0, sticky=tk.W)
        self.duty_measured_label = ttk.Label(measurements_frame, text="0.0%")
        self.duty_measured_label.grid(row=9, column=1, sticky=tk.W)
        

        
        # Light bulb display
        bulb_frame = ttk.LabelFrame(display_frame, text="PWM Output", padding="10")
        bulb_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.bulb_canvas = tk.Canvas(
            bulb_frame,
            width=150,
            height=100,
            bg="#2a2a2a",
            highlightthickness=1,
            highlightbackground="#666666"
        )
        self.bulb_canvas.grid(row=0, column=0, padx=(0, 20))
        
        self.brightness_label = ttk.Label(bulb_frame, text=f"Brightness: {self.duty_cycle:.0f}%", font=("Arial", 12))
        self.brightness_label.grid(row=0, column=1)
        
        # Instructions
        instructions = ttk.Label(
            main_frame,
            text="Use sliders to control frequency and duty cycle. PWM signal operates at 5V with 0-10V display range.",
            font=("Arial", 9),
            foreground="gray"
        )
        instructions.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        self.draw_oscilloscope_grid()
        self.draw_light_bulb()
    
    def setup_bindings(self):
        # Make sure the window can receive focus for any future keyboard shortcuts
        self.root.focus_set()
    
    def draw_oscilloscope_grid(self):
        """Draw oscilloscope-style grid"""
        self.canvas.delete("grid")
        
        # Major grid lines (bright)
        major_divisions = 10
        for i in range(major_divisions + 1):
            # Vertical lines (time)
            x = i * self.canvas_width / major_divisions
            color = "#006600" if i == major_divisions // 2 else self.grid_color
            width = 2 if i == major_divisions // 2 else 1
            self.canvas.create_line(x, 0, x, self.canvas_height, fill=color, width=width, tags="grid")
            
            # Horizontal lines (voltage)
            y = i * self.canvas_height / major_divisions
            color = "#006600" if i == major_divisions // 2 else self.grid_color
            width = 2 if i == major_divisions // 2 else 1
            self.canvas.create_line(0, y, self.canvas_width, y, fill=color, width=width, tags="grid")
        
        # Minor grid lines
        minor_divisions = 50
        for i in range(minor_divisions + 1):
            if i % 5 != 0:  # Skip major grid positions
                x = i * self.canvas_width / minor_divisions
                y = i * self.canvas_height / minor_divisions
                self.canvas.create_line(x, 0, x, self.canvas_height, fill="#001100", tags="grid")
                self.canvas.create_line(0, y, self.canvas_width, y, fill="#001100", tags="grid")
        
        # Voltage scale labels (0V to 10V)
        for i in range(11):
            voltage = 10.0 - i * 1.0
            y = i * self.canvas_height / 10
            self.canvas.create_text(15, y, text=f"{voltage:.0f}V", fill=self.text_color, tags="grid", font=("Arial", 8))
        
        # Time scale labels
        time_per_div = self.time_window / 10
        for i in range(11):
            time_val = i * time_per_div
            x = i * self.canvas_width / 10
            self.canvas.create_text(x, self.canvas_height - 10, text=f"{time_val:.1f}s", fill=self.text_color, tags="grid", font=("Arial", 8))
    
    def update_frequency(self, value):
        self.frequency = float(value)
        self.period = 1.0 / self.frequency
        self.freq_label.config(text=f"{self.frequency:.1f} Hz")
    
    def update_duty_cycle(self, value):
        self.duty_cycle = float(value)
        self.duty_label.config(text=f"{self.duty_cycle:.0f}%")
        self.brightness_label.config(text=f"Brightness: {self.duty_cycle:.0f}%")
    
    def update_timebase(self, value):
        self.time_window = float(value)
        self.timebase_label.config(text=f"{self.time_window:.1f}s")
        self.draw_oscilloscope_grid()
    

    
    def generate_pwm_signal(self, start_time, end_time, points=2000):
        """Generate PWM signal points"""
        times = np.linspace(start_time, end_time, points)
        voltages = []
        
        for t in times:
            t_in_period = (t % self.period) / self.period
            if t_in_period < (self.duty_cycle / 100.0):
                voltages.append(5.0)  # HIGH
            else:
                voltages.append(0.0)  # LOW
        
        return times, np.array(voltages)
    
    def draw_waveform(self):
        """Draw the PWM waveform with oscilloscope styling"""
        self.canvas.delete("waveform")
        self.canvas.delete("peaks")
        
        # Generate signal data
        start_time = self.current_time - self.time_window * 0.1
        end_time = start_time + self.time_window
        times, voltages = self.generate_pwm_signal(start_time, end_time, 2000)
        
        # Convert to canvas coordinates
        points = []
        peak_points_high = []
        peak_points_low = []
        
        for t, v in zip(times, voltages):
            x = self.canvas_width * (t - start_time) / self.time_window
            y = self.canvas_height * (1 - v / 10.0)  # Scale to 10V range
            points.extend([x, y])
            
            # Track peaks
            if v > 4.5:  # High peak
                peak_points_high.append((x, y))
            elif v < 0.5:  # Low peak
                peak_points_low.append((x, y))
        
        # Draw the main trace
        if len(points) >= 4:
            # Draw with phosphor-like effect
            self.canvas.create_line(points, fill=self.trace_color, width=2, tags="waveform")
            # Add glow effect
            self.canvas.create_line(points, fill="#004444", width=4, tags="waveform")
        
        # Mark peaks
        for x, y in peak_points_high[::20]:  # Sample every 20th point
            self.canvas.create_oval(x-2, y-2, x+2, y+2, fill=self.peak_color, outline="", tags="peaks")
        
        for x, y in peak_points_low[::20]:
            self.canvas.create_oval(x-2, y-2, x+2, y+2, fill=self.peak_color, outline="", tags="peaks")
        
        # Update measurements
        self.update_measurements(voltages)
        self.draw_light_bulb()
    
    def update_measurements(self, voltages):
        """Update measurement displays"""
        if len(voltages) == 0:
            return
        
        # Peak measurements
        high_peak = np.max(voltages)
        low_peak = np.min(voltages)
        peak_to_peak = high_peak - low_peak
        
        self.peak_high_label.config(text=f"{high_peak:.2f} V")
        self.peak_low_label.config(text=f"{low_peak:.2f} V")
        self.peak_pp_label.config(text=f"{peak_to_peak:.2f} V")
        
        # Timing measurements
        measured_period = self.period
        measured_freq = self.frequency
        pulse_width = (self.duty_cycle / 100.0) * measured_period
        
        self.period_label.config(text=f"{measured_period:.3f} s")
        self.freq_measured_label.config(text=f"{measured_freq:.2f} Hz")
        self.pulse_width_label.config(text=f"{pulse_width:.3f} s")
        self.duty_measured_label.config(text=f"{self.duty_cycle:.1f}%")
    
    def draw_light_bulb(self):
        """Draw simplified light bulb"""
        self.bulb_canvas.delete("all")
        
        brightness = self.duty_cycle / 100.0
        
        # Calculate color
        r = int(255 * (0.1 + 0.9 * brightness))
        g = int(255 * (0.1 + 0.9 * brightness))
        b = int(50 + 150 * brightness)
        bulb_color = f"#{r:02x}{g:02x}{b:02x}"
        
        # Draw bulb
        self.bulb_canvas.create_oval(40, 20, 110, 80, fill=bulb_color, outline="#666666", width=2)
        
        # Glow effect
        if brightness > 0.1:
            glow_size = int(10 * brightness)
            glow_color = f"#{int(255*brightness//3):02x}{int(255*brightness//3):02x}00"
            self.bulb_canvas.create_oval(
                40-glow_size, 20-glow_size, 110+glow_size, 80+glow_size,
                fill=glow_color, outline=""
            )
            # Redraw bulb on top
            self.bulb_canvas.create_oval(40, 20, 110, 80, fill=bulb_color, outline="#666666", width=2)
        
        # Base
        self.bulb_canvas.create_rectangle(60, 80, 90, 95, fill="#888888", outline="#666666")
    
    def animate(self):
        """Animation loop"""
        current_real_time = time.time()
        if not hasattr(self, 'start_real_time'):
            self.start_real_time = current_real_time
        
        elapsed_real_time = current_real_time - self.start_real_time
        self.current_time = elapsed_real_time * self.animation_speed
        
        self.draw_waveform()
        
        # Update at ~30 FPS for smooth oscilloscope display
        self.root.after(33, self.animate)

def main():
    root = tk.Tk()
    app = PWMOscilloscope(root)
    
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    
    root.mainloop()

if __name__ == "__main__":
    main()