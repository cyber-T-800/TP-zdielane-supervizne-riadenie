import time
import openvr

from PyQt5.QtCore import QThread, pyqtSignal

POLL_SECONDS = 0.02
DEADZONE = 0.20


def button_mask(button_id: int) -> int:
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
            "Grip": "Grip_R",
        }
    elif role == "LEFT":
        mapping = {
            "A": "X",
            "ApplicationMenu": "Y",
            "Grip": "Grip_L",
        }
    else:
        mapping = {}
    return mapping.get(button_name, button_name)


def apply_deadzone(value: float, deadzone: float = DEADZONE) -> float:
    if abs(value) < deadzone:
        return 0.0
    return value


class VRInputThread(QThread):
    # RIGHT A  — prevzatie / uvoľnenie aktuálneho drona
    toggle_control = pyqtSignal()
    # RIGHT B  — ďalší dron (cyklovanie vpravo)
    next_drone = pyqtSignal()
    # RIGHT Grip — predchádzajúci dron (cyklovanie vľavo)
    prev_drone = pyqtSignal()
    # LEFT Grip — núdzové zastavenie (nuluje rýchlosti a uvoľní riadenie)
    emergency_stop = pyqtSignal()
    # pohybový signál: lin_x, lin_y, lin_z, ang_x, ang_y, ang_z
    # RIGHT joystick Y → lin_x (dopredu/dozadu)
    # RIGHT joystick X → lin_y (strafe vľavo/vpravo)
    # LEFT  joystick Y → lin_z (výška hore/dole)
    # LEFT  joystick X → ang_z (yaw vľavo/vpravo)
    motion_signal = pyqtSignal(float, float, float, float, float, float)
    status_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.previous_pressed = {}

        self.right_joy_x = 0.0
        self.right_joy_y = 0.0
        self.left_joy_x = 0.0
        self.left_joy_y = 0.0

    def stop(self):
        self.running = False
        self.wait()

    def _emit_motion(self):
        self.motion_signal.emit(
            self.right_joy_y,  # lin_x  — RIGHT joystick Y
            self.right_joy_x,  # lin_y  — RIGHT joystick X
            self.left_joy_y,   # lin_z  — LEFT  joystick Y
            0.0,               # ang_x  — nepoužíva sa
            0.0,               # ang_y  — nepoužíva sa
            self.left_joy_x,   # ang_z  — LEFT  joystick X
        )

    def run(self):
        try:
            openvr.init(openvr.VRApplication_Background)
            vr_system = openvr.VRSystem()
            self.status_message.emit("VR input beží")

            while self.running:
                joystick_changed = False

                for device_index in iter_controller_indices(vr_system):
                    ok, state = vr_system.getControllerState(device_index)
                    if not ok:
                        continue

                    role_name = controller_role_name(vr_system, device_index)
                    if role_name not in ("LEFT", "RIGHT"):
                        continue

                    pressed_mask = int(state.ulButtonPressed)

                    if device_index not in self.previous_pressed:
                        self.previous_pressed[device_index] = pressed_mask
                    else:
                        old_set = set(decode_buttons(self.previous_pressed[device_index]))
                        new_set = set(decode_buttons(pressed_mask))

                        for button_name in sorted(new_set - old_set):
                            normalized = normalize_button(role_name, button_name)

                            if normalized == "A":
                                self.toggle_control.emit()
                            elif normalized == "B":
                                self.next_drone.emit()
                            elif normalized == "Grip_R":
                                self.prev_drone.emit()
                            elif normalized == "Grip_L":
                                self.emergency_stop.emit()

                        self.previous_pressed[device_index] = pressed_mask

                    new_x = apply_deadzone(float(state.rAxis[0].x))
                    new_y = apply_deadzone(float(state.rAxis[0].y))

                    if role_name == "RIGHT":
                        if new_x != self.right_joy_x or new_y != self.right_joy_y:
                            self.right_joy_x = new_x
                            self.right_joy_y = new_y
                            joystick_changed = True
                    else:
                        if new_x != self.left_joy_x or new_y != self.left_joy_y:
                            self.left_joy_x = new_x
                            self.left_joy_y = new_y
                            joystick_changed = True

                if joystick_changed:
                    self._emit_motion()

                time.sleep(POLL_SECONDS)

        except Exception as e:
            self.status_message.emit(f"VR input chyba: {e}")

        finally:
            try:
                openvr.shutdown()
            except Exception:
                pass
            self.status_message.emit("VR input zastavený")
