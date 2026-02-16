import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class PowerMeterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dell Power Meter - Cross-Platform")
        self.geometry("1000x950")
        ctk.set_appearance_mode("dark")

        # Data & Control State
        self.history_v = deque([0.0]*50, maxlen=50)
        self.history_i = deque([0.0]*50, maxlen=50)
        self.history_p = deque([0.0]*50, maxlen=50)
        self.ser = None
        self.running = False
        self.is_held = False  # Hold toggle flag

        # --- UI LAYOUT ---
        # 1. Connection Header
        self.conn_frame = ctk.CTkFrame(self)
        self.conn_frame.pack(fill="x", padx=10, pady=5)
        self.port_var = ctk.StringVar(value="Select Port")
        self.port_menu = ctk.CTkOptionMenu(self.conn_frame, variable=self.port_var, values=self.get_ports())
        self.port_menu.pack(side="left", padx=10, pady=10)
        self.refresh_btn = ctk.CTkButton(self.conn_frame, text="Refresh", width=60, command=self.refresh_ports)
        self.refresh_btn.pack(side="left", padx=5)
        self.connect_btn = ctk.CTkButton(self.conn_frame, text="Connect", fg_color="green", command=self.toggle_connection)
        self.connect_btn.pack(side="left", padx=10)
        self.status_dot = ctk.CTkLabel(self.conn_frame, text="●", text_color="red", font=("Arial", 20))
        self.status_dot.pack(side="right", padx=10)

        # 2. Digital Readouts
        self.readout_frame = ctk.CTkFrame(self)
        self.readout_frame.pack(fill="x", padx=10, pady=10)
        self.val_v = self.create_metric(self.readout_frame, "VOLTAGE", "0.00 V", "cyan")
        self.val_i = self.create_metric(self.readout_frame, "CURRENT", "0.00 A", "lightgreen")
        self.val_p = self.create_metric(self.readout_frame, "POWER", "0.0 W", "orange")

        # 3. Chart Controls & Hold Button
        self.toggle_frame = ctk.CTkFrame(self)
        self.toggle_frame.pack(fill="x", padx=10, pady=5)
        
        self.show_v = ctk.BooleanVar(value=False)
        self.show_i = ctk.BooleanVar(value=True)
        self.show_p = ctk.BooleanVar(value=False)

        ctk.CTkSwitch(self.toggle_frame, text="Show Voltage", variable=self.show_v, progress_color="cyan").pack(side="left", padx=15)
        ctk.CTkSwitch(self.toggle_frame, text="Show Current", variable=self.show_i, progress_color="lightgreen").pack(side="left", padx=15)
        ctk.CTkSwitch(self.toggle_frame, text="Show Wattage", variable=self.show_p, progress_color="orange").pack(side="left", padx=15)

        # NEW: Hold Button
        self.hold_btn = ctk.CTkButton(self.toggle_frame, text="Hold Graph", fg_color="gray", command=self.toggle_hold)
        self.hold_btn.pack(side="right", padx=20)

        # 4. Graph Setup
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.fig.patch.set_facecolor('#1a1a1a')
        self.ax.set_facecolor('#1a1a1a')
        self.line_v, = self.ax.plot(range(50), self.history_v, color='cyan', visible=False)
        self.line_i, = self.ax.plot(range(50), self.history_i, color='lightgreen', visible=True)
        self.line_p, = self.ax.plot(range(50), self.history_p, color='orange', visible=False)
        self.ax.tick_params(colors='white')
        self.ax.grid(True, color='#444444')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)

        self.debug_frame = ctk.CTkFrame(self, height=80)
        self.debug_frame.pack(fill="x", padx=10, pady=10)
        self.raw_data_lbl = ctk.CTkLabel(self.debug_frame, text="Ready", font=("Courier", 12))
        self.raw_data_lbl.pack(fill="x", padx=10, pady=10)

    def toggle_hold(self):
        self.is_held = not self.is_held
        if self.is_held:
            self.hold_btn.configure(text="RESUME", fg_color="orange")
        else:
            self.hold_btn.configure(text="Hold Graph", fg_color="gray")

    def create_metric(self, parent, title, placeholder, color):
        frame = ctk.CTkFrame(parent)
        frame.pack(side="left", expand=True, fill="both", padx=5, pady=5)
        ctk.CTkLabel(frame, text=title, font=("Arial", 12)).pack(pady=(5,0))
        lbl = ctk.CTkLabel(frame, text=placeholder, font=("Arial", 32, "bold"), text_color=color)
        lbl.pack(pady=(0, 10))
        return lbl

    def get_ports(self):
        return [p.device for p in serial.tools.list_ports.comports()] or ["No Ports Found"]

    def refresh_ports(self):
        new_ports = self.get_ports()
        self.port_menu.configure(values=new_ports)
        if new_ports: self.port_var.set(new_ports[0])

    def toggle_connection(self):
        if not self.running:
            port = self.port_var.get()
            if port in ["No Ports Found", "Select Port"]: return
            try:
                self.ser = serial.Serial(port, 115200, timeout=0.1)
                self.running = True
                self.connect_btn.configure(text="Disconnect", fg_color="red")
                self.status_dot.configure(text_color="green")
                threading.Thread(target=self.listen_serial, daemon=True).start()
            except Exception as e:
                self.raw_data_lbl.configure(text=f"Error: {e}")
        else:
            self.running = False
            if self.ser: self.ser.close()
            self.connect_btn.configure(text="Connect", fg_color="green")
            self.status_dot.configure(text_color="red")

    def listen_serial(self):
        while self.running:
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.after(0, lambda l=line: self.raw_data_lbl.configure(text=l))
                        parts = line.split(',')
                        if len(parts) >= 3:
                            self.after(0, self.process_data, parts[0], parts[1], parts[2])
            except: break

    def process_data(self, v_str, i_str, p_str):
        try:
            # 1. Digital Readout (Always Updates)
            v, i, p = max(0.0, float(v_str)), max(0.0, float(i_str)), max(0.0, float(p_str))
            self.val_v.configure(text=f"{v:.2f} V")
            self.val_i.configure(text=f"{i:.2f} A")
            self.val_p.configure(text=f"{p:.1f} W")

            # 2. Skip Graph Logic if "Hold" is Active
            if self.is_held:
                return

            # 3. Update History
            self.history_v.append(v)
            self.history_i.append(i)
            self.history_p.append(p)

            # 4. Update Lines
            self.line_v.set_visible(self.show_v.get())
            self.line_i.set_visible(self.show_i.get())
            self.line_p.set_visible(self.show_p.get())

            if self.show_v.get(): self.line_v.set_ydata(self.history_v)
            if self.show_i.get(): self.line_i.set_ydata(self.history_i)
            if self.show_p.get(): self.line_p.set_ydata(self.history_p)

            # 5. FIXED SCALING: Find Max visible value
            visible_data = []
            if self.show_v.get(): visible_data.extend(list(self.history_v))
            if self.show_i.get(): visible_data.extend(list(self.history_i))
            if self.show_p.get(): visible_data.extend(list(self.history_p))
            
            self.ax.relim()
            if visible_data and max(visible_data) > 0:
                ymax = max(visible_data)
                self.ax.set_ylim(0, ymax * 1.1) # Bottom locked at 0, Top padded 10%
            else:
                self.ax.set_ylim(0, 0.1) # Default tiny range if 0
                
            self.canvas.draw_idle()
        except: pass

if __name__ == "__main__":
    app = PowerMeterApp()
    app.mainloop()
