import customtkinter as ctk
import serial
import threading

# Configure Serial Port (Adjust /dev/ttyACM0 if needed)
SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 115200

class PowerMeterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dell Power Meter")
        self.geometry("400x300")

        # UI Elements
        self.label_v = ctk.CTkLabel(self, text="Voltage: 0.00 V", font=("Arial", 24))
        self.label_v.pack(pady=10)

        self.label_i = ctk.CTkLabel(self, text="Current: 0.00 mA", font=("Arial", 24))
        self.label_i.pack(pady=10)

        self.label_p = ctk.CTkLabel(self, text="Power: 0.00 mW", font=("Arial", 24), text_color="orange")
        self.label_p.pack(pady=10)

        # Start background thread to read Serial
        self.running = True
        self.thread = threading.Thread(target=self.read_serial, daemon=True)
        self.thread.start()

    def read_serial(self):
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                while self.running:
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        parts = line.split(',')
                        if len(parts) == 3:
                            self.update_ui(parts[0], parts[1], parts[2])
        except Exception as e:
            print(f"Serial Error: {e}")

    def update_ui(self, v, i, p):
        self.label_v.configure(text=f"Voltage: {v} V")
        self.label_i.configure(text=f"Current: {i} mA")
        self.label_p.configure(text=f"Power: {p} mW")

if __name__ == "__main__":
    app = PowerMeterApp()
    app.mainloop()
