import time
import openvr

POLL_SECONDS = 0.02
ANALOG_THRESHOLD = 0.20
ANALOG_DELTA_THRESHOLD = 0.08


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
    # Podľa tvojich testov:
    # RIGHT: A=A, ApplicationMenu=B
    # LEFT:  A=X, ApplicationMenu=Y
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
    return [
        (float(state.rAxis[i].x), float(state.rAxis[i].y))
        for i in range(5)
    ]


def now_str():
    return time.strftime("%H:%M:%S")


def print_event(role_name: str, device_index: int, event_type: str, payload: str):
    print(f"{now_str()} [{role_name}] dev={device_index} {event_type:<8} {payload}")


def diff_buttons(old_mask: int, new_mask: int):
    old_set = set(decode_buttons(old_mask))
    new_set = set(decode_buttons(new_mask))
    newly_on = sorted(new_set - old_set)
    newly_off = sorted(old_set - new_set)
    return newly_on, newly_off


def axis_changed_enough(old_axes, new_axes, axis_index: int) -> bool:
    old_x, old_y = old_axes[axis_index]
    new_x, new_y = new_axes[axis_index]
    return (
        abs(new_x - old_x) >= ANALOG_DELTA_THRESHOLD
        or abs(new_y - old_y) >= ANALOG_DELTA_THRESHOLD
    )


def should_report_axis(old_xy, new_xy) -> bool:
    old_x, old_y = old_xy
    new_x, new_y = new_xy

    return (
        abs(new_x) >= ANALOG_THRESHOLD
        or abs(new_y) >= ANALOG_THRESHOLD
        or abs(old_x) >= ANALOG_THRESHOLD
        or abs(old_y) >= ANALOG_THRESHOLD
    )


def format_axis_payload(role_name: str, axis_index: int, x: float, y: float) -> str:
    friendly = axis_friendly_name(role_name, axis_index)

    if axis_index in (1, 2):
        return f"{friendly}={x:.3f}"
    return f"{friendly}=({x:.3f},{y:.3f})"


def main():
    openvr.init(openvr.VRApplication_Scene)
    previous = {}

    try:
        vr_system = openvr.VRSystem()

        print("Watching controller events...")
        print("Mapped buttons:")
        print("  RIGHT: A=A, B=ApplicationMenu")
        print("  LEFT : X=A, Y=ApplicationMenu")
        print("  axis1=Trigger, axis2=Grip, axis0=Thumbstick/Touchpad")
        print("Ctrl+C to stop.\n")

        while True:
            for device_index in iter_controller_indices(vr_system):
                ok, state = vr_system.getControllerState(device_index)
                if not ok:
                    continue

                role_name = controller_role_name(vr_system, device_index)
                pressed_mask = int(state.ulButtonPressed)
                touched_mask = int(state.ulButtonTouched)
                axes = axes_snapshot(state)

                if device_index not in previous:
                    previous[device_index] = {
                        "pressed": pressed_mask,
                        "touched": touched_mask,
                        "axes": axes,
                    }
                    print_event(role_name, device_index, "INIT", "controller detected")
                    continue

                old = previous[device_index]

                # PRESS / RELEASE
                newly_pressed, newly_released = diff_buttons(old["pressed"], pressed_mask)

                if newly_pressed:
                    normalized = [normalize_button(role_name, b) for b in newly_pressed]
                    print_event(role_name, device_index, "PRESS", ", ".join(normalized))

                if newly_released:
                    normalized = [normalize_button(role_name, b) for b in newly_released]
                    print_event(role_name, device_index, "RELEASE", ", ".join(normalized))

                # TOUCH / UNTOUCH
                newly_touched, newly_untouched = diff_buttons(old["touched"], touched_mask)

                if newly_touched:
                    normalized = [normalize_button(role_name, b) for b in newly_touched]
                    print_event(role_name, device_index, "TOUCH", ", ".join(normalized))

                if newly_untouched:
                    normalized = [normalize_button(role_name, b) for b in newly_untouched]
                    print_event(role_name, device_index, "UNTOUCH", ", ".join(normalized))

                # AXIS changes
                for axis_index in range(5):
                    if axis_changed_enough(old["axes"], axes, axis_index):
                        old_xy = old["axes"][axis_index]
                        new_xy = axes[axis_index]

                        if should_report_axis(old_xy, new_xy):
                            x, y = new_xy
                            payload = format_axis_payload(role_name, axis_index, x, y)
                            print_event(role_name, device_index, "AXIS", payload)

                previous[device_index] = {
                    "pressed": pressed_mask,
                    "touched": touched_mask,
                    "axes": axes,
                }

            time.sleep(POLL_SECONDS)

    finally:
        try:
            openvr.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()