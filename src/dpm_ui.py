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
        self.geometry("900x850")
        ctk.set_appearance_mode("dark")

        # Data & Serial State
        self.data_history = deque([0]*50, maxlen=50)
        self.ser = None
        self.running = False

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
        self.val_i = self.create_metric(self.readout_frame, "CURRENT", "0.000 A", "lightgreen")
        self.val_p = self.create_metric(self.readout_frame, "POWER", "0.00 W", "orange")

        # 3. Graph
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.fig.patch.set_facecolor('#1a1a1a')
        self.ax.set_facecolor('#1a1a1a')
        self.line, = self.ax.plot(range(50), self.data_history, color='orange', linewidth=2)
        self.ax.tick_params(colors='white')
        self.ax.grid(True, color='#444444')
        self.ax.set_ylabel("Power (Watts)", color="white")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)

        # 4. Debug Monitor
        self.debug_frame = ctk.CTkFrame(self, height=80)
        self.debug_frame.pack(fill="x", padx=10, pady=10)
        self.raw_data_lbl = ctk.CTkLabel(self.debug_frame, text="Select a port and click Connect", font=("Courier", 12))
        self.raw_data_lbl.pack(fill="x", padx=10, pady=10)

    def create_metric(self, parent, title, placeholder, color):
        frame = ctk.CTkFrame(parent)
        frame.pack(side="left", expand=True, fill="both", padx=5, pady=5)
        ctk.CTkLabel(frame, text=title, font=("Arial", 12)).pack(pady=(5,0))
        lbl = ctk.CTkLabel(frame, text=placeholder, font=("Arial", 32, "bold"), text_color=color)
        lbl.pack(pady=(0, 10))
        return lbl

    def get_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        return ports if ports else ["No Ports Found"]

    def refresh_ports(self):
        new_ports = self.get_ports()
        self.port_menu.configure(values=new_ports)
        if new_ports: self.port_var.set(new_ports[0])

    def toggle_connection(self):
        if not self.running:
            port = self.port_var.get()
            if port == "No Ports Found" or port == "Select Port": return
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
            except:
                break

    def process_data(self, v, i, p):
        try:
            self.val_v.configure(text=f"{float(v):.2f} V")
            self.val_i.configure(text=f"{float(i):.3f} A")
            self.val_p.configure(text=f"{float(p):.2f} W")
            self.data_history.append(float(p))
            self.line.set_ydata(self.data_history)
            self.ax.relim(); self.ax.autoscale_view(); self.canvas.draw_idle()
        except: pass

if __name__ == "__main__":
    app = PowerMeterApp()
    app.mainloop()
