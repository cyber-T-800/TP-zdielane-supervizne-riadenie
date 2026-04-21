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
            "Grip": "X",   # ak sa u teba X fyzicky mapuje inak, toto zmeníme
        }
    elif role == "LEFT":
        mapping = {
            "A": "X",
            "ApplicationMenu": "Y",
        }
    else:
        mapping = {}

    return mapping.get(button_name, button_name)


def apply_deadzone(value: float, deadzone: float = DEADZONE) -> float:
    if abs(value) < deadzone:
        return 0.0
    return value


class VRInputThread(QThread):
    select_next = pyqtSignal()          # A
    mode_next = pyqtSignal()            # B
    confirm_selection = pyqtSignal()    # X
    joystick_changed = pyqtSignal(float, float)
    status_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.previous_pressed = {}
        self.last_joy_x = 0.0
        self.last_joy_y = 0.0

    def stop(self):
        self.running = False
        self.wait()

    def run(self):
        try:
            openvr.init(openvr.VRApplication_Background)
            vr_system = openvr.VRSystem()
            self.status_message.emit("VR input beží")

            while self.running:
                for device_index in iter_controller_indices(vr_system):
                    ok, state = vr_system.getControllerState(device_index)
                    if not ok:
                        continue

                    role_name = controller_role_name(vr_system, device_index)

                    # berieme len RIGHT controller
                    if role_name != "RIGHT":
                        continue

                    pressed_mask = int(state.ulButtonPressed)

                    if device_index not in self.previous_pressed:
                        self.previous_pressed[device_index] = pressed_mask
                    else:
                        old_mask = self.previous_pressed[device_index]

                        old_set = set(decode_buttons(old_mask))
                        new_set = set(decode_buttons(pressed_mask))
                        newly_pressed = sorted(new_set - old_set)

                        for button_name in newly_pressed:
                            normalized = normalize_button(role_name, button_name)

                            if normalized == "A":
                                self.select_next.emit()

                            elif normalized == "B":
                                self.mode_next.emit()

                            elif normalized == "X":
                                self.confirm_selection.emit()

                        self.previous_pressed[device_index] = pressed_mask

                    # joystick / thumbstick
                    # najčastejšie býva na Axis0, ale ak by nereagoval, otestujeme Axis1
                    joy_x = apply_deadzone(float(state.rAxis[0].x))
                    joy_y = apply_deadzone(float(state.rAxis[0].y))

                    # emit len ak sa niečo reálne zmenilo
                    if joy_x != self.last_joy_x or joy_y != self.last_joy_y:
                        self.last_joy_x = joy_x
                        self.last_joy_y = joy_y
                        self.joystick_changed.emit(joy_x, joy_y)

                time.sleep(POLL_SECONDS)

        except Exception as e:
            self.status_message.emit(f"VR input chyba: {e}")

        finally:
            try:
                openvr.shutdown()
            except Exception:
                pass
            self.status_message.emit("VR input zastavený")