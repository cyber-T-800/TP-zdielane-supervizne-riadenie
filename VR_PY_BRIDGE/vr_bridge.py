from pathlib import Path
import traceback
import time
import os
import openvr

APP_KEY = "miro.vr_py_bridge"
ACTIONS_PATH = Path(__file__).resolve().parent / "actions.json"


def print_origin_info(vr_input, origin_handle, label):
    try:
        if origin_handle == 0:
            print(f"{label} origin info: origin_handle=0")
            return

        origin_info = vr_input.getOriginTrackedDeviceInfo(origin_handle)
        print(
            f"{label} origin info: "
            f"devicePath={origin_info.devicePath} "
            f"trackedDeviceIndex={origin_info.trackedDeviceIndex} "
            f"component='{origin_info.rchRenderModelComponentName}'"
        )
    except Exception as e:
        print(f"{label} origin info EXCEPTION: {e}")


def main():
    print("=== VR PY BRIDGE START ===")
    print("Actions path:", ACTIONS_PATH)
    print("Exists:", ACTIONS_PATH.exists())
    print("APP_KEY:", APP_KEY)

    if not ACTIONS_PATH.exists():
        print("ERROR: actions.json does not exist.")
        return

    focus_captured = False

    try:
        # Zatial nechaj BACKGROUND, lebo s nim sa ti appka ukazovala v bindings menu.
        openvr.init(openvr.VRApplication_Scene)
        print("OpenVR init OK")

        # --- App/process diagnostika ---
        apps = openvr.VRApplications()
        pid = os.getpid()

        try:
            identify_result = apps.identifyApplication(pid, APP_KEY)
            print("identifyApplication result:", identify_result)
        except Exception as e:
            print("identifyApplication EXCEPTION:", e)

        try:
            mapped_pid = apps.getApplicationProcessId(APP_KEY)
            print("GetApplicationProcessId:", mapped_pid)
        except Exception as e:
            print("GetApplicationProcessId EXCEPTION:", e)
            mapped_pid = None

        print("Current PID:", pid)

        # --- Input focus diagnostika ---
        vr_system = openvr.VRSystem()

        try:
            focus_taken_by_other = vr_system.isInputFocusCapturedByAnotherProcess()
            print("isInputFocusCapturedByAnotherProcess:", focus_taken_by_other)
        except Exception as e:
            print("isInputFocusCapturedByAnotherProcess EXCEPTION:", e)

        try:
            capture_ok = vr_system.captureInputFocus()
            focus_captured = bool(capture_ok)
            print("captureInputFocus:", capture_ok)
        except Exception as e:
            print("captureInputFocus EXCEPTION:", e)

        try:
            focus_taken_by_other_after = vr_system.isInputFocusCapturedByAnotherProcess()
            print("isInputFocusCapturedByAnotherProcess AFTER capture:", focus_taken_by_other_after)
        except Exception as e:
            print("isInputFocusCapturedByAnotherProcess AFTER capture EXCEPTION:", e)

        # --- SteamVR Input setup ---
        vr_input = openvr.VRInput()

        try:
            result = vr_input.setActionManifestPath(str(ACTIONS_PATH))
            print("setActionManifestPath result:", result)
        except Exception as e:
            print("setActionManifestPath EXCEPTION:", e)
            return

        try:
            action_set = vr_input.getActionSetHandle("/actions/main")
            left_stick = vr_input.getActionHandle("/actions/main/in/LeftStick")
            right_stick = vr_input.getActionHandle("/actions/main/in/RightStick")
            left_trigger = vr_input.getActionHandle("/actions/main/in/LeftTrigger")
            right_trigger = vr_input.getActionHandle("/actions/main/in/RightTrigger")
            test_click = vr_input.getActionHandle("/actions/main/in/TestClick")

            left_hand = vr_input.getInputSourceHandle("/user/hand/left")
            right_hand = vr_input.getInputSourceHandle("/user/hand/right")
        except Exception as e:
            print("Handle acquisition EXCEPTION:", e)
            traceback.print_exc()
            return

        print("\n=== HANDLES ===")
        print("action_set   =", action_set)
        print("left_stick   =", left_stick)
        print("right_stick  =", right_stick)
        print("left_trigger =", left_trigger)
        print("right_trigger=", right_trigger)
        print("test_click   =", test_click)
        print("left_hand    =", left_hand)
        print("right_hand   =", right_hand)

        print("\nMove sticks / press triggers / A button. Ctrl+C to stop.\n")

        active_action_set = openvr.VRActiveActionSet_t()
        active_action_set.ulActionSet = action_set
        active_action_set.ulRestrictedToDevice = openvr.k_ulInvalidInputValueHandle
        active_action_set.ulSecondaryActionSet = openvr.k_ulInvalidActionSetHandle
        active_action_set.unPadding = 0

        # Dolezite:
        # OpenVR header spomina experimental overlay input override priority range.
        # Pri background appke nechajme 0.
        active_action_set.nPriority = 0

        loop_idx = 0

        while True:
            loop_idx += 1

            try:
                vr_input.updateActionState([active_action_set])
            except Exception as e:
                print("updateActionState EXCEPTION:", e)
                traceback.print_exc()
                break

            try:
                left_stick_data = vr_input.getAnalogActionData(
                    left_stick, openvr.k_ulInvalidInputValueHandle
                )
                right_stick_data = vr_input.getAnalogActionData(
                    right_stick, openvr.k_ulInvalidInputValueHandle
                )
                left_trigger_data = vr_input.getAnalogActionData(
                    left_trigger, openvr.k_ulInvalidInputValueHandle
                )
                right_trigger_data = vr_input.getAnalogActionData(
                    right_trigger, openvr.k_ulInvalidInputValueHandle
                )
                test_click_data = vr_input.getDigitalActionData(
                    test_click, openvr.k_ulInvalidInputValueHandle
                )
            except Exception as e:
                print("Action data read EXCEPTION:", e)
                traceback.print_exc()
                break

            print(f"=== VR INPUT TEST #{loop_idx} ===")
            print(
                f"Left Stick   active={left_stick_data.bActive} "
                f"origin={left_stick_data.activeOrigin} "
                f"x={left_stick_data.x:.4f} y={left_stick_data.y:.4f} "
                f"dx={left_stick_data.deltaX:.4f} dy={left_stick_data.deltaY:.4f}"
            )
            print(
                f"Right Stick  active={right_stick_data.bActive} "
                f"origin={right_stick_data.activeOrigin} "
                f"x={right_stick_data.x:.4f} y={right_stick_data.y:.4f} "
                f"dx={right_stick_data.deltaX:.4f} dy={right_stick_data.deltaY:.4f}"
            )
            print(
                f"Left Trigger active={left_trigger_data.bActive} "
                f"origin={left_trigger_data.activeOrigin} "
                f"x={left_trigger_data.x:.4f} dx={left_trigger_data.deltaX:.4f}"
            )
            print(
                f"Right Trigger active={right_trigger_data.bActive} "
                f"origin={right_trigger_data.activeOrigin} "
                f"x={right_trigger_data.x:.4f} dx={right_trigger_data.deltaX:.4f}"
            )
            print(
                f"Test Click   active={test_click_data.bActive} "
                f"origin={test_click_data.activeOrigin} "
                f"state={test_click_data.bState} changed={test_click_data.bChanged}"
            )

            # Kazdych ~10 cyklov vypiseme znovu diagnostiku procesu/focusu
            if loop_idx % 10 == 0:
                try:
                    mapped_pid_now = apps.getApplicationProcessId(APP_KEY)
                    print("DIAG mapped PID now:", mapped_pid_now)
                except Exception as e:
                    print("DIAG mapped PID EXCEPTION:", e)

                try:
                    focus_now = vr_system.isInputFocusCapturedByAnotherProcess()
                    print("DIAG focus captured by another process:", focus_now)
                except Exception as e:
                    print("DIAG focus check EXCEPTION:", e)

            # Ked sa objavi valid origin, skus vypisat detail
            if left_stick_data.activeOrigin != 0:
                print_origin_info(vr_input, left_stick_data.activeOrigin, "Left Stick")
            if right_stick_data.activeOrigin != 0:
                print_origin_info(vr_input, right_stick_data.activeOrigin, "Right Stick")
            if left_trigger_data.activeOrigin != 0:
                print_origin_info(vr_input, left_trigger_data.activeOrigin, "Left Trigger")
            if right_trigger_data.activeOrigin != 0:
                print_origin_info(vr_input, right_trigger_data.activeOrigin, "Right Trigger")
            if test_click_data.activeOrigin != 0:
                print_origin_info(vr_input, test_click_data.activeOrigin, "Test Click")

            print()
            time.sleep(0.2)

    except KeyboardInterrupt:
        print("Stopped by user.")
    except Exception as e:
        print("EXCEPTION:", e)
        traceback.print_exc()
    finally:
        try:
            if focus_captured:
                try:
                    openvr.VRSystem().releaseInputFocus()
                    print("releaseInputFocus OK")
                except Exception as e:
                    print("releaseInputFocus EXCEPTION:", e)

            openvr.shutdown()
            print("OpenVR shutdown OK")
        except Exception:
            pass


if __name__ == "__main__":
    main()