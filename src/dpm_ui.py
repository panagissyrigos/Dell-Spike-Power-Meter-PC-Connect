import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os

class PowerMeterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Dell Power Meter - 7-Segment Clone")
        self.geometry("920x980")
        ctk.set_appearance_mode("dark")

        # --- 1. FONT LOADING ---
        self.font_name = "Arial"
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            font_path = os.path.join(script_dir, "digital-7.ttf")
            if os.path.exists(font_path):
                ctk.FontManager.load_font(font_path)
                self.font_name = "Digital-7"
            else:
                print(f"Font file not found at: {font_path}")
        except Exception as e:
            print(f"Font error: {e}")

        # Data & Control State
        self.history_v = deque([0.0]*50, maxlen=50)
        self.history_i = deque([0.0]*50, maxlen=50)
        self.history_p = deque([0.0]*50, maxlen=50)
        self.max_current = 0.0
        self.ser = None
        self.running = False
        self.is_held = False

        # --- 2. UI LAYOUT ---
        self.conn_frame = ctk.CTkFrame(self)
        self.conn_frame.pack(fill="x", padx=10, pady=5)
        self.port_var = ctk.StringVar(value="Select Port")
        self.port_menu = ctk.CTkOptionMenu(self.conn_frame, variable=self.port_var, values=self.get_ports())
        self.port_menu.pack(side="left", padx=10, pady=10)
        self.refresh_btn = ctk.CTkButton(self.conn_frame, text="Refresh", width=60, command=self.refresh_ports)
        self.refresh_btn.pack(side="left", padx=5)
        self.connect_btn = ctk.CTkButton(self.conn_frame, text="Connect", fg_color="green", command=self.toggle_connection)
        self.connect_btn.pack(side="left", padx=10)
        self.status_dot = ctk.CTkLabel(self.conn_frame, text="●", text_color="red", font=("Arial", 24))
        self.status_dot.pack(side="right", padx=10)

        # --- 3. RECREATED DIGITAL DISPLAY ---
        #lcd_blue_bg = "#001e3c"
        #lcd_text_color = "#82caff"
        lcd_blue_bg = "#82caff"
        lcd_text_color = "#001e3c"
        self.display_container = ctk.CTkFrame(self, fg_color="#333", border_width=4, border_color="#555")
        self.display_container.pack(fill="x", padx=20, pady=10)
        self.lcd_frame = ctk.CTkFrame(self.display_container, fg_color=lcd_blue_bg, corner_radius=0)
        self.lcd_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.lcd_frame.grid_columnconfigure((0, 1), weight=1)
        self.lcd_frame.grid_rowconfigure((0, 1), weight=1)

        self.v_slots = self.create_lcd_quadrant(0, 0, "VOLTAGE", 5, "V", lcd_text_color, dot_idx=2)
        self.i_slots = self.create_lcd_quadrant(0, 1, "CURRENT", 5, "A", lcd_text_color, dot_idx=2)
        self.p_slots = self.create_lcd_quadrant(1, 0, "POWER", 5, "W", lcd_text_color, dot_idx=3)
        self.max_slots = self.create_lcd_quadrant(1, 1, "MAX CURRENT", 5, "MAX", lcd_text_color, dot_idx=2)

        self.update_slots(self.v_slots, "00.00")
        self.update_slots(self.i_slots, "00.00")
        self.update_slots(self.p_slots, "000.0")
        self.update_slots(self.max_slots, "00.00")

        # --- 4. CONTROLS & GRAPH ---
        self.ctrl_frame = ctk.CTkFrame(self)
        self.ctrl_frame.pack(fill="x", padx=10, pady=5)
        self.show_v = ctk.BooleanVar(value=False)
        self.show_i = ctk.BooleanVar(value=True)
        self.show_p = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(self.ctrl_frame, text="Show V", variable=self.show_v, progress_color="cyan").pack(side="left", padx=10)
        ctk.CTkSwitch(self.ctrl_frame, text="Show I", variable=self.show_i, progress_color="lightgreen").pack(side="left", padx=10)
        ctk.CTkSwitch(self.ctrl_frame, text="Show W", variable=self.show_p, progress_color="orange").pack(side="left", padx=10)
        self.reset_btn = ctk.CTkButton(self.ctrl_frame, text="RESET MAX", fg_color="#922b21", command=self.reset_max)
        self.reset_btn.pack(side="right", padx=10)
        self.hold_btn = ctk.CTkButton(self.ctrl_frame, text="HOLD GRAPH", fg_color="#5d6d7e", command=self.toggle_hold)
        self.hold_btn.pack(side="right", padx=10)

        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.fig.patch.set_facecolor('#1a1a1a')
        self.ax.set_facecolor('#1a1a1a')
        self.line_v, = self.ax.plot(range(50), list(self.history_v), color='cyan', visible=False)
        self.line_i, = self.ax.plot(range(50), list(self.history_i), color='lightgreen', visible=True)
        self.line_p, = self.ax.plot(range(50), list(self.history_p), color='orange', visible=False)
        self.ax.tick_params(colors='white')
        self.ax.grid(True, color='#333333')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=5)
        self.raw_data_lbl = ctk.CTkLabel(self, text="Ready", font=("Courier", 12))
        self.raw_data_lbl.pack(pady=5)

    def create_lcd_quadrant(self, r, c, label_text, num_slots, unit_text, color, dot_idx):
        f = ctk.CTkFrame(self.lcd_frame, fg_color="transparent")
        f.grid(row=r, column=c, sticky="nsew", padx=20, pady=20)
        top_row = ctk.CTkFrame(f, fg_color="transparent")
        top_row.pack()
        slots_container = ctk.CTkFrame(top_row, fg_color="transparent")
        slots_container.pack(side="left")
        labels = []
        for i in range(num_slots):
            is_dot = (i == dot_idx)
            w = 0 if is_dot else 65
            lbl = ctk.CTkLabel(slots_container, text="-", font=(self.font_name, 110), text_color=color, width=w)
            lbl.pack(side="left")
            labels.append(lbl)
        u_lbl = ctk.CTkLabel(top_row, text=unit_text, font=("Arial", 30, "bold"), text_color=color)
        u_lbl.pack(side="left", padx=10, pady=(45, 0))
        l_lbl = ctk.CTkLabel(f, text=label_text, font=("Arial", 24, "bold"), text_color=color)
        l_lbl.pack()
        return labels

    def update_slots(self, slots_list, value_str):
        for i, char in enumerate(value_str):
            if i < len(slots_list):
                slots_list[i].configure(text=char)

    def reset_max(self):
        self.max_current = 0.0
        self.update_slots(self.max_slots, "00.00")

    def toggle_hold(self):
        self.is_held = not self.is_held
        self.hold_btn.configure(text="RESUME" if self.is_held else "HOLD GRAPH", fg_color="orange" if self.is_held else "#5d6d7e")

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
            v, i, p = float(v_str), float(i_str), float(p_str)
            self.update_slots(self.v_slots, f"{v:05.2f}")
            self.update_slots(self.i_slots, f"{i:05.2f}")
            self.update_slots(self.p_slots, f"{p:05.1f}")

            if i > self.max_current:
                self.max_current = i
                self.update_slots(self.max_slots, f"{self.max_current:05.2f}")

            if self.is_held: return
            
            self.history_v.append(v)
            self.history_i.append(i)
            self.history_p.append(p)

            # Update line visibility and data
            self.line_v.set_visible(self.show_v.get())
            self.line_i.set_visible(self.show_i.get())
            self.line_p.set_visible(self.show_p.get())
            
            if self.show_v.get(): self.line_v.set_ydata(list(self.history_v))
            if self.show_i.get(): self.line_i.set_ydata(list(self.history_i))
            if self.show_p.get(): self.line_p.set_ydata(list(self.history_p))

            # --- AUTO SCALING LOGIC ---
            self.ax.relim()
            visible_data = []
            if self.show_v.get(): visible_data.extend(list(self.history_v))
            if self.show_i.get(): visible_data.extend(list(self.history_i))
            if self.show_p.get(): visible_data.extend(list(self.history_p))
            
            if visible_data and max(visible_data) > 0:
                self.ax.set_ylim(0, max(visible_data) * 1.1)
            else:
                self.ax.set_ylim(0, 10) # Fallback scale

            self.canvas.draw_idle()
        except: pass

if __name__ == "__main__":
    app = PowerMeterApp()
    app.mainloop()
