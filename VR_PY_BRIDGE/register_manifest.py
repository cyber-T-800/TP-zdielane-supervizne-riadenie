from pathlib import Path
import traceback
import openvr

MANIFEST_PATH = Path(__file__).resolve().parent / "vr_inputbridge.vrmanifest"
APP_KEY = "miro.vr_py_bridge"

def main():
    print("=== REGISTER MANIFEST ===")
    print("Manifest path:", MANIFEST_PATH)
    print("Exists:", MANIFEST_PATH.exists())

    if not MANIFEST_PATH.exists():
        print("ERROR: vr_inputbridge.vrmanifest does not exist.")
        return

    try:
        openvr.init(openvr.VRApplication_Utility)
        print("OpenVR init OK")

        apps = openvr.VRApplications()

        result = apps.addApplicationManifest(str(MANIFEST_PATH), False)
        print("addApplicationManifest raw result:", result)

        installed = apps.isApplicationInstalled(APP_KEY)
        print("isApplicationInstalled:", installed)

        if installed:
            print("SUCCESS: App is registered in SteamVR.")
        else:
            print("WARNING: App does not appear installed yet.")
            print("Try restarting SteamVR and run this script again.")

    except Exception as e:
        print("EXCEPTION:", e)
        traceback.print_exc()
    finally:
        try:
            openvr.shutdown()
            print("OpenVR shutdown OK")
        except Exception:
            pass

if __name__ == "__main__":
    main()