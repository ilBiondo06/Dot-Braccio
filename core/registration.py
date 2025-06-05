# esempio di esecuzione: python3 registration.py --filter_profile General --payload_mode custom4 --duration 10 --output_rate 30 --show show
#TODO inserire più messaggi di errore
#TODO lavorare sul plotting dei dati (ho un po' di domande...)
#TODO inserire una barra dei progressi nel caso della registrazione con durata
#TODO inserire quanti secondi sono passati dall' inizio della registrazione nel caso della registrazione senza durata 
#TODO sistemare l'output dei valori nella gui

#TODO spostare l'invio dei dati al di fuori dello show data


import argparse
import json
import time
from datetime import datetime
from xdpchandler import *
import os
import sys
import threading
from integration_movella import initialize_json, insert_data

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

def parse_args():
    parser = argparse.ArgumentParser(description="Movella DOT Recorder")
    parser.add_argument("--filter_profile", required=True, choices=["General", "Dynamic"], help="Filter profile to set")
    parser.add_argument("--payload_mode", required=True, choices=PAYLOAD_MODES.keys(), help="Payload mode")
    parser.add_argument("--duration", type=int, help="Duration in seconds (omit for indefinite)")
    parser.add_argument("--output_rate", type=int, required=True, help="Output rate in Hz")
    parser.add_argument("--show", choices=["show", "noshow"], default="noshow", help="Display orientation live")
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
    
    concat_id=""
    flag=False
    for device in xdpcHandler.connectedDots():
        filterProfiles = device.getAvailableFilterProfiles()
        available_labels = [f.label() for f in filterProfiles]
        print("Available filter profiles:", ", ".join(available_labels))    # Mostra i profili di filtro disponibili
        print(f"\nConfiguring device: {device.deviceTagName()}")
        print("id:", device.deviceId())
        if flag:
            concat_id = concat_id + "|"
        flag=True
        concat_id = concat_id + str(device.deviceId())

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
        #device.setLogOptions(movelladot_pc_sdk.XsLogOptions_QuaternionAndEuler)
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

def show_data(xdpcHandler, duration):
    print(f"\nMain loop. Recording data for {duration} seconds.")
    print("-----------------------------------------")

    names = [d.deviceTagName() for d in xdpcHandler.connectedDots()]
    name_width = 40
    header = " ".join([f"{name:^{name_width}}" for name in names])
    print(header)

    start_time_ms = movelladot_pc_sdk.XsTimeStamp_nowMs()
    total_ms = duration * 1000
    progress_bar_length = 40  # lunghezza barra progressi
    prev_len = 0

    while True:
        elapsed_ms = movelladot_pc_sdk.XsTimeStamp_nowMs() - start_time_ms
        if elapsed_ms >= total_ms:
            break

        progress = elapsed_ms / total_ms
        filled_len = int(progress_bar_length * progress)
        bar = "=" * filled_len + "-" * (progress_bar_length - filled_len)
        elapsed_sec = int(elapsed_ms // 1000)

        # Preparo i dati orientazione in una stringa
        row = ""
        if xdpcHandler.packetsAvailable():
            for device in xdpcHandler.connectedDots():
                packet = xdpcHandler.getNextPacket(device.portInfo().bluetoothAddress())
                if packet.containsOrientation():
                    euler = packet.orientationEuler()
                    roll, pitch, yaw = euler.x(), euler.y(), euler.z()
                    formatted = f"Roll: {roll:6.2f}, Pitch: {pitch:6.2f}, Yaw: {yaw:6.2f}"
                    row += f"{formatted} | "

        # Ora costruisco la riga con i dati prima e la barra dopo
        line = f"{row}Progress: [{bar}] {elapsed_sec:3d}/{duration} sec"
        # Se la riga precedente era più lunga, pulisco con spazi extra
        if prev_len > len(line):
            line += " " * (prev_len - len(line))

        print(f"\r{line}", end="", flush=True)
        prev_len = len(line)
        time.sleep(0.1)

    # Alla fine, stampo i dati orientazione liberi (vuoti) e la barra COMPLETA con “DONE”
    full_bar = "=" * progress_bar_length
    # Se ci sono ancora pacchetti orientazione da leggere al termine, puoi includerli; altrimenti lascio solo DONE
    final_orientation = ""
    if xdpcHandler.packetsAvailable():
        for device in xdpcHandler.connectedDots():
            packet = xdpcHandler.getNextPacket(device.portInfo().bluetoothAddress())
            if packet.containsOrientation():
                euler = packet.orientationEuler()
                r, p, y = euler.x(), euler.y(), euler.z()
                final_orientation += f"Roll: {r:6.2f}, Pitch: {p:6.2f}, Yaw: {y:6.2f} | "

    final_line = f"{final_orientation}Progress: [{full_bar}] {duration:3d}/{duration} sec | DONE"
    if prev_len > len(final_line):
        final_line += " " * (prev_len - len(final_line))
    print(f"\r{final_line}", flush=True)

    print("\n-----------------------------------------")




def show_data_indefinite(xdpcHandler):
    print("\nMain loop. Recording data indefinitely. Press ENTER to stop.")
    print("-----------------------------------------")
    names = [d.deviceTagName() for d in xdpcHandler.connectedDots()]
    name_width = 40
    header = " ".join([f"{name:^{name_width}}" for name in names])
    print(header)

    start_time_ms = movelladot_pc_sdk.XsTimeStamp_nowMs()

    while not stop_flag.is_set():
        elapsed_ms = movelladot_pc_sdk.XsTimeStamp_nowMs() - start_time_ms
        elapsed_sec = elapsed_ms // 1000

        # Mostro tempo trascorso
        print(f"\rElapsed time: {elapsed_sec} seconds ", end="")

        if xdpcHandler.packetsAvailable():
            row = ""
            for device in xdpcHandler.connectedDots():
                packet = xdpcHandler.getNextPacket(device.portInfo().bluetoothAddress())
                if packet.containsOrientation():
                    euler = packet.orientationEuler()
                    roll, pitch, yaw = euler.x(), euler.y(), euler.z()
                    formatted = f"Roll: {roll:6.2f}, Pitch: {pitch:6.2f}, Yaw: {yaw:6.2f}"
                    row += f"{formatted:^{name_width}}| "
            print("\r" + row, end="")

        sys.stdout.flush()
        time.sleep(0.1)
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


stop_flag = threading.Event()

def wait_for_enter():
    input("\nPress ENTER to stop measurement...")
    stop_flag.set()

if __name__ == "__main__":
    args = parse_args()
    runtime_params = {
        'payload_mode': args.payload_mode,
        'duration': args.duration,
        'output_rate': args.output_rate,
        'show': args.show,
    }
    """concat_id=""

    #MODIFICARE QUI
    json_data = initialize_json(
        token="my_token",  # Sostituire con valori reali
        id_="user_id",
        device="device_name",
        model="DOT"
    )"""
    
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
            input("\nPress ENTER to start measurement...")
            stop_flag.clear()
            payload_mode_enum = PAYLOAD_MODES[runtime_params['payload_mode']]
            show_flag = runtime_params['show'] == "show"
            start_measurement(xdpcHandler, payload_mode_enum)
            if runtime_params['duration'] is None:
                thread = threading.Thread(target=wait_for_enter)
                thread.start()
                if show_flag:
                    show_data_indefinite(xdpcHandler)
                else:
                    start_time = time.time()
                    while not stop_flag.is_set():
                        elapsed = int(time.time() - start_time)
                        print(f"\rElapsed time: {elapsed} seconds", end="", flush=True)
                        time.sleep(1)
                    print()
                thread.join()
            else:
                if show_flag:
                    show_data(xdpcHandler, runtime_params['duration'])
                else:
                    # Barra di progresso durante la registrazione silenziosa
                    start_time = time.time()
                    duration = runtime_params['duration']
                    bar_len = 40
                    while True:
                        elapsed = time.time() - start_time
                        if elapsed >= duration:
                            break
                        progress = elapsed / duration
                        filled_len = int(bar_len * progress)
                        bar = '=' * filled_len + '-' * (bar_len - filled_len)
                        print(f"\rProgress: [{bar}] {int(elapsed):3d}/{duration} sec ", end="", flush=True)
                        time.sleep(0.1)
                    print()
            stop_measurement_and_logging(xdpcHandler)
            answer = input("\nRepeat measurement (r), modify parameters (m), or quit (q)? [r/m/q]: ").strip().lower()
            if answer == 'q':
                break
            elif answer == 'm':
                runtime_params = prompt_for_new_params(runtime_params)
                configure_devices(xdpcHandler, args.filter_profile, runtime_params['output_rate'])
    finally:
        reset_and_cleanup(xdpcHandler)


stop_flag = threading.Event()

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

        if duration is None:
            if show:
                thread = threading.Thread(target=wait_for_enter)
                thread.start()
                show_data_indefinite(handler)
                thread.join()
            else:
                while not stop_flag.is_set():
                    time.sleep(1)
        else:
            if show:
                show_data(handler, duration)
            else:
                time.sleep(duration)

        stop_measurement_and_logging(handler)
    finally:
        reset_and_cleanup(handler)
        builtins.print = orig_print