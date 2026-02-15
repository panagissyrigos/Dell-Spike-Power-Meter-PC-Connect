import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Configuration
SERIAL_PORT = '/dev/ttyACM0' 
BAUD_RATE = 115200

class PowerMeterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dell Power Meter - PC Connect")
        self.geometry("900x700")
        ctk.set_appearance_mode("dark")

        # Data Storage
        self.data_history = deque([0]*50, maxlen=50)
        self.is_connected = False

        # --- UI LAYOUT ---
        # 1. Status Bar
        self.status_frame = ctk.CTkFrame(self, height=40)
        self.status_frame.pack(fill="x", padx=10, pady=5)
        
        self.status_dot = ctk.CTkLabel(self.status_frame, text="●", text_color="red", font=("Arial", 20))
        self.status_dot.pack(side="left", padx=(10, 5))
        
        self.status_text = ctk.CTkLabel(self.status_frame, text="DISCONNECTED", font=("Arial", 12, "bold"))
        self.status_text.pack(side="left")

        # 2. Digital Readouts (3 Columns)
        self.readout_frame = ctk.CTkFrame(self)
        self.readout_frame.pack(fill="x", padx=10, pady=10)

        self.val_v = self.create_metric(self.readout_frame, "VOLTAGE", "0.00 V", "cyan")
        self.val_i = self.create_metric(self.readout_frame, "CURRENT", "0.00 mA", "lightgreen")
        self.val_p = self.create_metric(self.readout_frame, "POWER", "0.00 mW", "orange")

        # 3. Graph
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.fig.patch.set_facecolor('#1a1a1a')
        self.ax.set_facecolor('#1a1a1a')
        self.line, = self.ax.plot(range(50), self.data_history, color='orange', linewidth=2)
        
        self.ax.tick_params(colors='white')
        self.ax.grid(True, color='#444444')
        self.ax.set_ylim(0, 5000) # Adjust based on your Dell charger (e.g., 90000 for 90W)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # Start Serial Thread
        threading.Thread(target=self.serial_manager, daemon=True).start()

    def create_metric(self, parent, title, placeholder, color):
        frame = ctk.CTkFrame(parent)
        frame.pack(side="left", expand=True, fill="both", padx=5, pady=5)
        ctk.CTkLabel(frame, text=title, font=("Arial", 12)).pack(pady=(5, 0))
        lbl = ctk.CTkLabel(frame, text=placeholder, font=("Arial", 32, "bold"), text_color=color)
        lbl.pack(pady=(0, 10))
        return lbl

    def update_status(self, connected):
        self.is_connected = connected
        if connected:
            self.status_dot.configure(text_color="green")
            self.status_text.configure(text=f"CONNECTED: {SERIAL_PORT}")
        else:
            self.status_dot.configure(text_color="red")
            self.status_text.configure(text="DISCONNECTED (Searching...)")
            self.val_v.configure(text="0.00 V")
            self.val_i.configure(text="0.00 mA")
            self.val_p.configure(text="0.00 mW")

    def serial_manager(self):
        while True:
            try:
                with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1) as ser:
                    self.after(0, self.update_status, True)
                    while True:
                        line = ser.readline().decode('utf-8').strip()
                        if line:
                            parts = line.split(',')
                            if len(parts) == 3:
                                # Update UI (Voltage, Current, Power)
                                self.after(0, self.process_data, parts[0], parts[1], parts[2])
            except (serial.SerialException, FileNotFoundError):
                self.after(0, self.update_status, False)
                threading.Event().wait(2.0) # Retry every 2 seconds

    def process_data(self, v, i, p):
        # Update Labels
        self.val_v.configure(text=f"{v} V")
        self.val_i.configure(text=f"{i} mA")
        self.val_p.configure(text=f"{p} mW")
        
        # Update Graph (Using Power value)
        try:
            p_float = float(p)
            self.data_history.append(p_float)
            self.line.set_ydata(self.data_history)
            self.ax.relim()
            self.ax.autoscale_view(scalex=False, scaley=True)
            self.canvas.draw_idle()
        except ValueError:
            pass

if __name__ == "__main__":
    app = PowerMeterApp()
    app.mainloop()
