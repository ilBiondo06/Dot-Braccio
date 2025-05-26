# esempio di esecuzione: python3 registration.py General custom4 10 30 show
# TODO cosa fare nel caso in cui fallisce la sincronizzazione? solitamente accade quando durante la sincronizzazione un dispositivo ha perso la connessione 
#      (da quel che ho capito), più aumenta il numero di DOT connessi più è probabile che succeda
# TODO interfaccia grafica (necessaria?)
# TODO altri parametri da aggiungere?

import argparse
import time
from datetime import datetime
from xdpchandler import *
import os
import sys

# Mapping stringa → PayloadMode_enum
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
    'freeAcc': movelladot_pc_sdk.XsPayloadMode_FreeAcceleration,
    'highFid': movelladot_pc_sdk.XsPayloadMode_HighFidelity,
    'highFidMag': movelladot_pc_sdk.XsPayloadMode_HighFidelitywMag,
    'dq': movelladot_pc_sdk.XsPayloadMode_DeltaQuantities,
    'dqMag': movelladot_pc_sdk.XsPayloadMode_DeltaQuantitieswMag,
    'rq': movelladot_pc_sdk.XsPayloadMode_RateQuantities,
    'rqMag': movelladot_pc_sdk.XsPayloadMode_RateQuantitieswMag,
    'mfm': movelladot_pc_sdk.XsPayloadMode_MFM
}

# utilizzo il modulo argparse per parsing dei parametri da linea di comando

def parse_args():
    parser = argparse.ArgumentParser(description="Movella DOT Recorder")
    parser.add_argument("filter_profile", choices=["General", "Dynamic"], help="Filter profile to set")
    parser.add_argument("payload_mode", choices=PAYLOAD_MODES.keys(), help="Payload mode (e.g., custom4)")
    parser.add_argument("duration", type=int, help="Duration of recording in seconds")
    parser.add_argument("output_rate", type=int, help="Output rate in Hz")
    parser.add_argument("show", nargs='?', default="noshow", choices=["show", "noshow"], help="Show roll, pitch, yaw in real-time")
    return parser.parse_args()



def initialize_and_connect(xdpcHandler):
    if not xdpcHandler.initialize():    # inizializzo xdpcHandler
        print("Initialization failed.")
        return False

    xdpcHandler.scanForDots()
    if len(xdpcHandler.detectedDots()) == 0: #Esegue la scansione dei dispositivi Movella DOT connessi
        print("No Movella DOT device(s) found.")
        return False

    xdpcHandler.connectDots()       # Prova a connettersi a quelli trovati
    if len(xdpcHandler.connectedDots()) == 0:
        print("Could not connect to any Movella DOT device(s).")
        return False

    return True


def configure_devices(xdpcHandler, profile, output_rate):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True) # Creo una cartella, se non esiste, chiamata logs

    for device in xdpcHandler.connectedDots():
        filterProfiles = device.getAvailableFilterProfiles()
        available_labels = [f.label() for f in filterProfiles]
        print("Available filter profiles:", ", ".join(available_labels))    # Mostra i profili di filtro disponibili
        print(f"\nConfiguring device: {device.deviceTagName()}")
        print("id:", device.deviceId())

        if device.setOnboardFilterProfile(profile):         # Imposta il filtro scelto
            print(f"Successfully set profile to {profile}")
        else:
            print("Setting filter profile failed!")

        if device.setOutputRate(output_rate):       # imposta il rate di misurazione
            print(f"Successfully set output rate to {output_rate} Hz")
        else:
            print("Setting output rate failed!")
            print("Current output rate:", device.outputRate())

        #TODO controllare se il codice funziona anche senza il setLogOptions
        device.setLogOptions(movelladot_pc_sdk.XsLogOptions_QuaternionAndEuler)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        deviceName = device.deviceTagName().replace(' ', '_')
        logFileName = os.path.join(log_dir, f"{deviceName}_{timestamp}.csv")          #Crea un nome file .csv per il log basato su nome del dispositivo e timestamp, inserito nella cartella logs

        print(f"Enable logging to: {logFileName}")
        if not device.enableLogging(logFileName):            # Attiva il logging sul dispositivo
            print(f"Failed to enable logging. Reason: {device.lastResultText()}")


def synchronize_devices(xdpcHandler):
    manager = xdpcHandler.manager()
    deviceList = xdpcHandler.connectedDots()

    if len(deviceList) <= 1:
        print("Only one device connected. Skipping synchronization.")
        return True

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


def stop_measurement_and_logging(xdpcHandler):
    for device in xdpcHandler.connectedDots():
        if not device.stopMeasurement():
            print(f"Failed to stop measurement for {device.deviceTagName()}")
        if not device.disableLogging():
            print(f"Failed to disable logging for {device.deviceTagName()}")

# Mostra in tempo reale (se abilitato) roll, pitch e yaw per ciascun dispositivo
def show_data(xdpcHandler, duration):
    print(f"\nMain loop. Recording data for {duration} seconds.")
    print("-----------------------------------------")

    # Stampa i nomi centrati sopra ogni colonna di dati
    names = [d.deviceTagName() for d in xdpcHandler.connectedDots()]
    name_width = 40
    header = " ".join([f"{name:^{name_width}}" for name in names])
    print(header)

    startTime = movelladot_pc_sdk.XsTimeStamp_nowMs()
    while movelladot_pc_sdk.XsTimeStamp_nowMs() - startTime <= duration * 1000:
        if xdpcHandler.packetsAvailable():
            row = ""
            for device in xdpcHandler.connectedDots():
                packet = xdpcHandler.getNextPacket(device.portInfo().bluetoothAddress())
                if packet.containsOrientation():
                    euler = packet.orientationEuler()
                    formatted = f"Roll: {euler.x():6.2f}, Pitch: {euler.y():6.2f}, Yaw: {euler.z():6.2f}"
                    row += f"{formatted:^{name_width}}| "
            print(f"{row}\r", end="", flush=True)
    print("\n-----------------------------------------")



def reset_and_cleanup(xdpcHandler):
    print("\nResetting heading before stopping measurement and logging...")
    for device in xdpcHandler.connectedDots():
        print(f"Resetting heading for {device.deviceTagName()}: ", end="")
        if device.resetOrientation(movelladot_pc_sdk.XRM_DefaultAlignment):
            print("OK")
        else:
            print(f"NOK: {device.lastResultText()}")

    print("\nStopping measurement and logging...")
    stop_measurement_and_logging(xdpcHandler)

    print("Stopping sync...")
    if not xdpcHandler.manager().stopSync():
        print("Failed to stop sync.")

    xdpcHandler.cleanup()
    print("Cleanup complete.")


# Permette all’utente di modificare i parametri durante l'esecuzione
def prompt_for_new_params(current):
    print("\n--- Modify Parameters ---")
    print("Press ENTER to keep the current value.")

    new_payload = input(f"Payload mode [{current['payload_mode']}]: ").strip()
    if new_payload and new_payload in PAYLOAD_MODES:
        current['payload_mode'] = new_payload
    elif new_payload:
        print("Invalid payload. Keeping the current one.")

    try:
        new_dur = input(f"Duration (s) [{current['duration']}]: ").strip()
        if new_dur:
            current['duration'] = int(new_dur)
    except ValueError:
        print("Invalid duration. Keeping the current one.")

    try:
        new_rate = input(f"Output rate (Hz) [{current['output_rate']}]: ").strip()
        if new_rate:
            current['output_rate'] = int(new_rate)
    except ValueError:
        print("Invalid output rate. Keeping the current one.")

    new_show = input(f"Show data? (show/noshow) [{current['show']}]: ").strip().lower()
    if new_show in ("show", "noshow"):
        current['show'] = new_show

    return current


if __name__ == "__main__":
    args = parse_args()
    runtime_params = {
        'payload_mode': args.payload_mode,
        'duration': args.duration,
        'output_rate': args.output_rate,
        'show': args.show,
    }
    xdpcHandler = XdpcHandler()
    try:
        if not initialize_and_connect(xdpcHandler):
            xdpcHandler.cleanup()
            exit(-1)
        configure_devices(xdpcHandler, args.filter_profile, runtime_params['output_rate'])
        if not synchronize_devices(xdpcHandler):
            print("Synchronization failed. You can try again later.")
            xdpcHandler.cleanup()
            exit(-1)
        while True:
            payload_mode_enum = PAYLOAD_MODES[runtime_params['payload_mode']]
            show_flag = runtime_params['show'] == "show"
            start_measurement(xdpcHandler, payload_mode_enum)
            if show_flag:
                show_data(xdpcHandler, runtime_params['duration'])
            else:
                print(f"Recording silently for {runtime_params['duration']} seconds...")
                time.sleep(runtime_params['duration'])
            stop_measurement_and_logging(xdpcHandler)
            answer = input("\nRepeat measurement (r), modify parameters (m), or quit (q)? [r/m/q]: ").strip().lower()
            if answer == 'q':
                break
            elif answer == 'm':
                runtime_params = prompt_for_new_params(runtime_params)
                configure_devices(xdpcHandler, args.filter_profile, runtime_params['output_rate'])
    finally:
        reset_and_cleanup(xdpcHandler)

# run function for GUI

def run(filter_profile, payload_mode, duration, output_rate, show, output_stream=sys.stdout):
    import builtins
    orig_print = builtins.print
    def gui_print(*args, **kwargs):
        orig_print(*args, **kwargs, file=output_stream)
        output_stream.flush()
    builtins.print = gui_print
    handler = XdpcHandler()
    try:
        if not initialize_and_connect(handler): return
        configure_devices(handler, filter_profile, output_rate)
        if not synchronize_devices(handler): return
        start_measurement(handler, PAYLOAD_MODES[payload_mode])
        if show:
            show_data(handler, duration)
        else:
            time.sleep(duration)
        stop_measurement_and_logging(handler)
    finally:
        reset_and_cleanup(handler)
        builtins.print = orig_print