import customtkinter as ctk
import serial
import threading
from collections import deque

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

class PowerMeterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dell Power Meter - Engineering Mode")
        self.geometry("900x500")
        
        # Readouts
        self.val_v = self.create_metric("VOLTAGE", "cyan")
        self.val_i = self.create_metric("CURRENT", "lightgreen")
        self.val_p = self.create_metric("POWER", "orange")
        
        # Debug Label for Shunt Voltage
        self.debug_lbl = ctk.CTkLabel(self, text="Shunt Voltage: 0.0000 mV", font=("Courier", 14))
        self.debug_lbl.pack(pady=10)

        threading.Thread(target=self.serial_thread, daemon=True).start()

    def create_metric(self, title, color):
        lbl = ctk.CTkLabel(self, text=f"{title}: 0.00", font=("Arial", 30, "bold"), text_color=color)
        lbl.pack(pady=15)
        return lbl

    def serial_thread(self):
        while True:
            try:
                with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1) as ser:
                    while True:
                        line = ser.readline().decode('utf-8').strip()
                        if line:
                            parts = line.split(',')
                            if len(parts) >= 4:
                                self.after(0, self.update_ui, parts[0], parts[1], parts[2], parts[3])
            except:
                pass

    def update_ui(self, v, i, p, shunt):
        self.val_v.configure(text=f"VOLTAGE: {v} V")
        self.val_i.configure(text=f"CURRENT: {i} mA")
        self.val_p.configure(text=f"POWER: {p} mW")
        self.debug_lbl.configure(text=f"Shunt Drop: {shunt} mV (If 0.0, check wiring)")

if __name__ == "__main__":
    app = PowerMeterApp()
    app.mainloop()
