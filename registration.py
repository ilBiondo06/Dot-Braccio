import argparse
import time
from datetime import datetime
from xdpchandler import *

# Mapping stringa → PayloadMode enum
PAYLOAD_MODES = {
    'custom1': movelladot_pc_sdk.XsPayloadMode_CustomMode1,
    'custom2': movelladot_pc_sdk.XsPayloadMode_CustomMode2,
    'custom3': movelladot_pc_sdk.XsPayloadMode_CustomMode3,
    'custom4': movelladot_pc_sdk.XsPayloadMode_CustomMode4,
    'custom5': movelladot_pc_sdk.XsPayloadMode_CustomMode5,
    'orientQuat': movelladot_pc_sdk.XsPayloadMode_OrientationQuaternion,
    'completeQuat': movelladot_pc_sdk.XsPayloadMode_CompleteQuaternion,
    'extQuat': movelladot_pc_sdk.XsPayloadMode_ExtendedQuaternion,
    'orientEul': movelladot_pc_sdk.XsPayloadMode_OrientationEuler,
    'completeEul': movelladot_pc_sdk.XsPayloadMode_CompleteEuler,
    'extEul': movelladot_pc_sdk.XsPayloadMode_ExtendedEuler,
    'freeAcc': movelladot_pc_sdk.XsPayloadMode_FreeAccelleration,
    'highFid': movelladot_pc_sdk.XsPayloadMode_HighFidelity,
    'highFidMag': movelladot_pc_sdk.XsPayloadMode_HighFidelitywMag,
    'dq':  movelladot_pc_sdk.XsPayloadMode_DeltaQuantities,
    'dqMag': movelladot_pc_sdk.XsPayloadMode_DeltaQuantitieswMag,
    'rq': movelladot_pc_sdk.XsPayloadMode_RateQuantities,
    'rqMag': movelladot_pc_sdk.XsPayloadMode_RateQuantitieswMag,
    'mfm': movelladot_pc_sdk.XsPayloadMode_MFM

}


def parse_args():
    parser = argparse.ArgumentParser(description="Movella DOT Recorder")
    parser.add_argument("filter_profile", choices=["General", "Dynamic"], help="Filter profile to set")
    parser.add_argument("payload_mode", choices=PAYLOAD_MODES.keys(), help="Payload mode (e.g., custom4)")
    parser.add_argument("duration", type=int, help="Duration of recording in seconds")
    parser.add_argument("output_rate", type=int, help="Output rate in Hz, available values: 1, 4, 10, 12, 15, 20, 30, 60, 120")
    parser.add_argument("show", nargs='?', default="noshow", choices=["show", "noshow"], help="Show roll, pitch, yaw data in real-time")
    return parser.parse_args()


def initialize_and_connect(xdpcHandler):
    if not xdpcHandler.initialize():
        print("Initialization failed.")
        return False

    xdpcHandler.scanForDots()
    if len(xdpcHandler.detectedDots()) == 0:
        print("No Movella DOT device(s) found.")
        return False

    xdpcHandler.connectDots()
    if len(xdpcHandler.connectedDots()) == 0:
        print("Could not connect to any Movella DOT device(s).")
        return False

    return True


def configure_devices(xdpcHandler, profile, output_rate):
    for device in xdpcHandler.connectedDots():
        print(f"\nConfiguring device: {device.deviceTagName()}")

        filterProfiles = device.getAvailableFilterProfiles()
        available_labels = [f.label() for f in filterProfiles]
        print("Available filter profiles:", ", ".join(available_labels))

        if device.setOnboardFilterProfile(profile):
            print(f"Successfully set profile to {profile}")
        else:
            print("Setting filter profile failed!")

        if device.setOutputRate(output_rate):
            print(f"Successfully set output rate to {output_rate} Hz")
        else:
            print("Setting output rate failed!")
            print("Current output rate:", device.outputRate())

        device.setLogOptions(movelladot_pc_sdk.XsLogOptions_QuaternionAndEuler)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        deviceName = device.deviceTagName().replace(' ', '_')
        logFileName = f"{deviceName}_{timestamp}.csv"

        print(f"Enable logging to: {logFileName}")
        if not device.enableLogging(logFileName):
            print(f"Failed to enable logging. Reason: {device.lastResultText()}")


def synchronize_devices(xdpcHandler):
    manager = xdpcHandler.manager()
    deviceList = xdpcHandler.connectedDots()

    print(f"\nStarting sync... Root node: {deviceList[-1].deviceTagName()}")
    print("This takes at least 14 seconds")

    if not manager.startSync(deviceList[-1].bluetoothAddress()):
        print(f"Could not start sync. Reason: {manager.lastResultText()}")
        print("Stopping sync and retrying...")
        manager.stopSync()
        time.sleep(1)

        if not manager.startSync(deviceList[-1].bluetoothAddress()):
            print(f"Retry failed. Reason: {manager.lastResultText()}")
            return False
    return True


def start_measurement(xdpcHandler, payload_mode):
    for device in xdpcHandler.connectedDots():
        if not device.startMeasurement(payload_mode):
            print(f"Could not start measurement for {device.deviceTagName()}. Reason: {device.lastResultText()}")


def show_data(xdpcHandler, duration):
    print(f"\nMain loop. Recording data for {duration} seconds.")
    print("-----------------------------------------")
    print(" ".join([f"{d.deviceTagName():>42}" for d in xdpcHandler.connectedDots()]))

    startTime = movelladot_pc_sdk.XsTimeStamp_nowMs()
    while movelladot_pc_sdk.XsTimeStamp_nowMs() - startTime <= duration * 1000:
        if xdpcHandler.packetsAvailable():
            s = ""
            for device in xdpcHandler.connectedDots():
                packet = xdpcHandler.getNextPacket(device.portInfo().bluetoothAddress())
                if packet.containsOrientation():
                    euler = packet.orientationEuler()
                    s += f"Roll:{euler.x():7.2f}, Pitch:{euler.y():7.2f}, Yaw:{euler.z():7.2f}| "
            print(f"{s}\r", end="", flush=True)
    print("\n-----------------------------------------")


def reset_and_cleanup(xdpcHandler):
    for device in xdpcHandler.connectedDots():
        print(f"\nResetting heading for {device.deviceTagName()}: ", end="")
        if device.resetOrientation(movelladot_pc_sdk.XRM_DefaultAlignment):
            print("OK")
        else:
            print(f"NOK: {device.lastResultText()}")

    print("\nStopping measurement and logging...")
    for device in xdpcHandler.connectedDots():
        if not device.stopMeasurement():
            print(f"Failed to stop measurement for {device.deviceTagName()}")
        if not device.disableLogging():
            print(f"Failed to disable logging for {device.deviceTagName()}")

    print("Stopping sync...")
    if not xdpcHandler.manager().stopSync():
        print("Failed to stop sync.")

    xdpcHandler.cleanup()
    print("Cleanup complete.")


if __name__ == "__main__":
    args = parse_args()

    payload_mode_str = args.payload_mode
    payload_mode_enum = PAYLOAD_MODES[payload_mode_str]
    show_flag = args.show == "show"
    duration = args. duration

    xdpcHandler = XdpcHandler()

    try:
        if not initialize_and_connect(xdpcHandler):
            xdpcHandler.cleanup()
            exit(-1)

        configure_devices(xdpcHandler, args.filter_profile, args.output_rate)

        if not synchronize_devices(xdpcHandler):
            print("Synchronization failed. You can try again later.")
            xdpcHandler.cleanup()
            exit(-1)

        start_measurement(xdpcHandler, payload_mode_enum)

        if show_flag:
            show_data(xdpcHandler, args.duration)
        else:
            print(f"Recording silently for {duration} seconds...")
            time.sleep(duration)

    finally:
        reset_and_cleanup(xdpcHandler)
