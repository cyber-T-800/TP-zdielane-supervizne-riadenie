import time
import tkinter as tk
from tkinter import ttk
import openvr

POLL_MS = 20
ANALOG_THRESHOLD = 0.20


def button_mask(button_id: int):
    return 1 << button_id


def iter_controller_indices(vr_system):
    for device_index in range(openvr.k_unMaxTrackedDeviceCount):
        if vr_system.getTrackedDeviceClass(device_index) == openvr.TrackedDeviceClass_Controller:
            yield device_index


def controller_role_name(vr_system, device_index: int) -> str:
    role = vr_system.getControllerRoleForTrackedDeviceIndex(device_index)
    if role == openvr.TrackedControllerRole_LeftHand:
        return "LEFT"
    if role == openvr.TrackedControllerRole_RightHand:
        return "RIGHT"
    return f"UNKNOWN({device_index})"


def get_button_map():
    return {
        openvr.k_EButton_System: "System",
        openvr.k_EButton_ApplicationMenu: "ApplicationMenu",
        openvr.k_EButton_Grip: "Grip",
        openvr.k_EButton_DPad_Left: "DPad_Left",
        openvr.k_EButton_DPad_Up: "DPad_Up",
        openvr.k_EButton_DPad_Right: "DPad_Right",
        openvr.k_EButton_DPad_Down: "DPad_Down",
        openvr.k_EButton_A: "A",
        openvr.k_EButton_ProximitySensor: "ProximitySensor",
        openvr.k_EButton_Axis0: "Axis0",
        openvr.k_EButton_Axis1: "Axis1",
        openvr.k_EButton_Axis2: "Axis2",
        openvr.k_EButton_Axis3: "Axis3",
        openvr.k_EButton_Axis4: "Axis4",
        openvr.k_EButton_SteamVR_Touchpad: "Touchpad",
        openvr.k_EButton_SteamVR_Trigger: "Trigger",
    }


BUTTON_MAP = get_button_map()


def decode_buttons(mask_value: int):
    names = []
    for button_id, name in BUTTON_MAP.items():
        if mask_value & button_mask(button_id):
            names.append(name)
    return names


def normalize_button(role: str, button_name: str) -> str:
    if role == "RIGHT":
        mapping = {
            "A": "A",
            "ApplicationMenu": "B",
            "Trigger": "RightTriggerClick",
            "Grip": "RightGripClick",
            "Axis2": "RightGripClick",
            "Touchpad": "RightThumbstickTouch",
            "Axis0": "RightThumbstick",
        }
    elif role == "LEFT":
        mapping = {
            "A": "X",
            "ApplicationMenu": "Y",
            "Trigger": "LeftTriggerClick",
            "Grip": "LeftGripClick",
            "Axis2": "LeftGripClick",
            "Touchpad": "LeftThumbstickTouch",
            "Axis0": "LeftThumbstick",
        }
    else:
        mapping = {}

    return mapping.get(button_name, button_name)


def axis_friendly_name(role: str, axis_index: int) -> str:
    if role == "LEFT":
        axis_names = {
            0: "LeftThumbstick",
            1: "LeftTrigger",
            2: "LeftGrip",
            3: "LeftAxis3",
            4: "LeftAxis4",
        }
    elif role == "RIGHT":
        axis_names = {
            0: "RightThumbstick",
            1: "RightTrigger",
            2: "RightGrip",
            3: "RightAxis3",
            4: "RightAxis4",
        }
    else:
        axis_names = {
            0: "Axis0",
            1: "Axis1",
            2: "Axis2",
            3: "Axis3",
            4: "Axis4",
        }

    return axis_names.get(axis_index, f"Axis{axis_index}")


def axes_snapshot(state):
    return [(float(state.rAxis[i].x), float(state.rAxis[i].y)) for i in range(5)]


class VRGui:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenVR Controller Test")
        self.root.geometry("900x650")

        self.running = True
        self.vr_system = None

        self.status_var = tk.StringVar(value="Initializing OpenVR...")
        self.left_pressed_var = tk.StringVar(value="-")
        self.left_touched_var = tk.StringVar(value="-")
        self.right_pressed_var = tk.StringVar(value="-")
        self.right_touched_var = tk.StringVar(value="-")

        self.left_axis_vars = [tk.StringVar(value="0.000, 0.000") for _ in range(5)]
        self.right_axis_vars = [tk.StringVar(value="0.000, 0.000") for _ in range(5)]

        self.build_ui()
        self.init_vr()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        if self.vr_system:
            self.update_loop()

    def build_ui(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="VR Controller Test", font=("Arial", 16, "bold")).pack(anchor="w")
        ttk.Label(top, textvariable=self.status_var, foreground="blue").pack(anchor="w", pady=(5, 0))

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        left_frame = ttk.LabelFrame(main, text="LEFT Controller", padding=10)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right_frame = ttk.LabelFrame(main, text="RIGHT Controller", padding=10)
        right_frame.pack(side="left", fill="both", expand=True, padx=(5, 0))

        self.build_controller_panel(left_frame, "LEFT")
        self.build_controller_panel(right_frame, "RIGHT")

        log_frame = ttk.LabelFrame(self.root, text="Live Log", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log_text = tk.Text(log_frame, height=14, wrap="word")
        self.log_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def build_controller_panel(self, parent, role):
        pressed_var = self.left_pressed_var if role == "LEFT" else self.right_pressed_var
        touched_var = self.left_touched_var if role == "LEFT" else self.right_touched_var
        axis_vars = self.left_axis_vars if role == "LEFT" else self.right_axis_vars

        ttk.Label(parent, text="Pressed buttons:", font=("Arial", 10, "bold")).pack(anchor="w")
        ttk.Label(parent, textvariable=pressed_var, wraplength=380).pack(anchor="w", pady=(0, 10))

        ttk.Label(parent, text="Touched buttons:", font=("Arial", 10, "bold")).pack(anchor="w")
        ttk.Label(parent, textvariable=touched_var, wraplength=380).pack(anchor="w", pady=(0, 10))

        ttk.Label(parent, text="Axes:", font=("Arial", 10, "bold")).pack(anchor="w")

        grid = ttk.Frame(parent)
        grid.pack(fill="x", pady=(5, 0))

        for i in range(5):
            axis_name = axis_friendly_name(role, i)
            ttk.Label(grid, text=f"{axis_name}:").grid(row=i, column=0, sticky="w", padx=(0, 10), pady=2)
            ttk.Label(grid, textvariable=axis_vars[i]).grid(row=i, column=1, sticky="w", pady=2)

    def init_vr(self):
        try:
            openvr.init(openvr.VRApplication_Background)
            self.vr_system = openvr.VRSystem()
            self.status_var.set("OpenVR initialized. Move controllers / press buttons.")
            self.log("OpenVR initialized.")
        except Exception as e:
            msg = str(e)
            if "NoServerForBackgroundApp" in msg or "301" in msg:
                self.status_var.set("Chyba: Najprv spusti SteamVR, potom tento skript.")
                self.log("ERROR: SteamVR nebeží. Spusti ho pred skriptom.")
            else:
                self.status_var.set(f"Failed to initialize OpenVR: {e}")
                self.log(f"ERROR: {e}")

    def log(self, message: str):
        ts = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"{ts} | {message}\n")
        self.log_text.see("end")

    def update_controller_ui(self, role_name, pressed_names, touched_names, axes):
        pressed_text = ", ".join(pressed_names) if pressed_names else "-"
        touched_text = ", ".join(touched_names) if touched_names else "-"

        if role_name == "LEFT":
            self.left_pressed_var.set(pressed_text)
            self.left_touched_var.set(touched_text)
            vars_list = self.left_axis_vars
        elif role_name == "RIGHT":
            self.right_pressed_var.set(pressed_text)
            self.right_touched_var.set(touched_text)
            vars_list = self.right_axis_vars
        else:
            return

        for i in range(5):
            x, y = axes[i]
            if i in (1, 2):
                vars_list[i].set(f"{x:.3f}")
            else:
                vars_list[i].set(f"{x:.3f}, {y:.3f}")

    def update_loop(self):
        if not self.running or not self.vr_system:
            return

        detected_roles = set()

        try:
            for device_index in iter_controller_indices(self.vr_system):
                ok, state = self.vr_system.getControllerState(device_index)
                if not ok:
                    continue

                role_name = controller_role_name(self.vr_system, device_index)
                detected_roles.add(role_name)

                pressed_mask = int(state.ulButtonPressed)
                touched_mask = int(state.ulButtonTouched)
                axes = axes_snapshot(state)

                pressed_names = [normalize_button(role_name, b) for b in decode_buttons(pressed_mask)]
                touched_names = [normalize_button(role_name, b) for b in decode_buttons(touched_mask)]

                self.update_controller_ui(role_name, pressed_names, touched_names, axes)

            if "LEFT" not in detected_roles:
                self.left_pressed_var.set("not detected")
                self.left_touched_var.set("not detected")
                for var in self.left_axis_vars:
                    var.set("-")

            if "RIGHT" not in detected_roles:
                self.right_pressed_var.set("not detected")
                self.right_touched_var.set("not detected")
                for var in self.right_axis_vars:
                    var.set("-")

        except Exception as e:
            self.status_var.set(f"Runtime error: {e}")

        self.root.after(POLL_MS, self.update_loop)

    def on_close(self):
        self.running = False
        try:
            openvr.shutdown()
        except Exception:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = VRGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()