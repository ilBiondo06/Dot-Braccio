# esempio di esecuzione: python3 registration.py --filter_profile General --payload_mode custom4 --duration 10 --output_rate 30 --show show
#TODO inserire il send al server anche in show data
#TODO sistemare start-stop-start (non vede i movella dopo)
#TODO inserire la possibilità di decidere se salvare un csv con l'eventuale cambio di nome
#TODO implementare live plot

import argparse
import json
import time
from datetime import datetime
from xdpchandler import *
import os
import sys
import threading
from live_plotter import LivePlotter 
import requests
import csv
import queue

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

    # Stampa i nomi centrati sopra ogni colonna di dati
    names = [d.deviceTagName() for d in xdpcHandler.connectedDots()]
    name_width = 40
    header = " ".join([f"{name:^{name_width}}" for name in names])
    print(header)

    start_time_ms = movelladot_pc_sdk.XsTimeStamp_nowMs()
    total_ms = duration * 1000
    progress_bar_length = 40  # lunghezza barra progressi

    while True:
        elapsed_ms = movelladot_pc_sdk.XsTimeStamp_nowMs() - start_time_ms
        if elapsed_ms > total_ms:
            break

        # Barra di progresso
        progress = elapsed_ms / total_ms
        filled_len = int(progress_bar_length * progress)
        bar = '=' * filled_len + '-' * (progress_bar_length - filled_len)
        elapsed_sec = elapsed_ms / 1000
        sys.stdout.flush()

        # Mostro barra e tempo trascorso
        sys.stdout.write(f"\rProgress: [{bar}] {elapsed_sec:3.0f}/{duration} sec ")
        
        # Dati orientazione se disponibili
        if xdpcHandler.packetsAvailable():
            row = ""
            for device in xdpcHandler.connectedDots():
                packet = xdpcHandler.getNextPacket(device.portInfo().bluetoothAddress())
                if packet.containsOrientation():
                    euler = packet.orientationEuler()
                    roll, pitch, yaw = euler.x(), euler.y(), euler.z()
                    formatted = f"Roll: {roll:6.2f}, Pitch: {pitch:6.2f}, Yaw: {yaw:6.2f}"
                    row += f"{formatted:^{name_width}}| "
            sys.stdout.write(row)

        sys.stdout.flush()
        time.sleep(0.1)
    print("\n-----------------------------------------")

stop_event = threading.Event()
json_queue = queue.Queue()

def send_post_data(stop_event, json_queue):
    while not stop_event.is_set() or not json_queue.empty():
        try:
            data = json_queue.get(timeout=0.01)  # Attende dati dalla coda
            url = "http://193.205.129.120:63435/publish/sensor_movella"
            print("Sending POST to Server...")
            response = requests.post(url, json=data, headers={"Content-Type": "application/json"})
            print("Status code:", response.status_code)
            print("Server response:", response.text)
            print(f"Wait to close the app. The queue is not empty. Items left:{json_queue.qsize()}")
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Errore nell'invio dei dati: {e}")
    print("Now the queue is empty. You can close the application if you want.")

def show_data_indefinite(xdpcHandler, send_flag):
    print("\nMain loop. Recording data indefinitely. Press ENTER to stop.")
    print("-----------------------------------------")
    names = [d.deviceTagName()[8:8+4] for d in xdpcHandler.connectedDots()]
    names.sort()
    name_width = 40
    header = " ".join([f"{name:^{name_width}}" for name in names])
    print(header)

    id_all = ""
    for name_pos in range(len(names)-1):
        id_all+=names[name_pos]+"|"
    id_all +=names[len(names)-1]

    start_time_ms = movelladot_pc_sdk.XsTimeStamp_nowMs()
    
    upper_bound =  180
    lower_bound = -180
    
    values_in_json_sended_to_IoE_Server = {
        "Identifier": {
            "id": id_all,
            "device": "Sensor",
            "model": "Movella Xsens Dot"
        },
        "MovellaData":{
            "timestamp":time.time(),
            "DOT0":{"roll":0,"pitch":0,"yaw":0,"range":{"upper_bound": upper_bound, "lower_bound":lower_bound}},
            "DOT1":{"roll":0,"pitch":0,"yaw":0,"range":{"upper_bound": upper_bound, "lower_bound":lower_bound}},
            "DOT2":{"roll":0,"pitch":0,"yaw":0,"range":{"upper_bound": upper_bound, "lower_bound":lower_bound}},
            "DOT3":{"roll":0,"pitch":0,"yaw":0,"range":{"upper_bound": upper_bound, "lower_bound":lower_bound}},
            "DOT4":{"roll":0,"pitch":0,"yaw":0,"range":{"upper_bound": upper_bound, "lower_bound":lower_bound}}
        }
    }
    
    if send_flag:
        t = threading.Thread(target=send_post_data, args=(stop_event, json_queue))
        t.daemon = True  # il thread si chiude quando il main thread termina
        t.start()

        t2= threading.Thread(target=send_post_data, args=(stop_event, json_queue))
        t2.daemon = True  # il thread si chiude quando il main thread termina
        t2.start()

        t3= threading.Thread(target=send_post_data, args=(stop_event, json_queue))
        t3.daemon = True  # il thread si chiude quando il main thread termina
        t3.start()

    while not stop_flag.is_set():
        elapsed_ms = movelladot_pc_sdk.XsTimeStamp_nowMs() - start_time_ms
        elapsed_sec = elapsed_ms / 1000
        sys.stdout.flush()

        # Mostro tempo trascorso
        sys.stdout.write(f"\rElapsed time: {elapsed_sec} seconds ")

        if xdpcHandler.packetsAvailable():

            row = ""
            for device in xdpcHandler.connectedDots():
                packet = xdpcHandler.getNextPacket(device.portInfo().bluetoothAddress())
                name = device.deviceTagName()[8:8+4]
                if packet.containsOrientation():
                    euler = packet.orientationEuler()
                    roll, pitch, yaw = euler.x(), euler.y(), euler.z()
                    formatted = f"Roll: {roll:6.2f}, Pitch: {pitch:6.2f}, Yaw: {yaw:6.2f}"
                    row += f"{formatted:^{name_width}}| "
                    values_in_json_sended_to_IoE_Server["MovellaData"][name]["roll"]=roll
                    values_in_json_sended_to_IoE_Server["MovellaData"][name]["pitch"]=pitch
                    values_in_json_sended_to_IoE_Server["MovellaData"][name]["yaw"]=yaw

            sys.stdout.write(row)

            values_in_json_sended_to_IoE_Server["MovellaData"]["timestamp"]=time.time()
            if send_flag:
                json_queue.put(values_in_json_sended_to_IoE_Server.copy())


        sys.stdout.flush()
        time.sleep(0.1)

    if send_flag:
        stop_event.set()
        t.join()
        t2.join()
        t3.join()
    
    print("\n-----------------------------------------")

def sample_data_for_json(xdpcHandler):  # <-- Json used to train a FCNN (Fully Connected Neural Network).
    print("\nMain loop. Recording data indefinitely. Press ENTER to stop.")
    print("-----------------------------------------")
    names = [d.deviceTagName()[8:8+4] for d in xdpcHandler.connectedDots()]
    names.sort()
    name_width = 40
    header = " ".join([f"{name:^{name_width}}" for name in names])
    print(header)

    id_all = ""
    for name_pos in range(len(names)-1):
        id_all+=names[name_pos]+"|"
    id_all +=names[len(names)-1]

    start_time_ms = movelladot_pc_sdk.XsTimeStamp_nowMs()
    
    row_in_csv = []

    upper_bound =  180
    lower_bound = -180
    
    values_in_json_sended_to_IoE_Server = {
        "Identifier": {
            "id": id_all,
            "device": "Sensor",
            "model": "Movella Xsens Dot"
        },
        "MovellaData":{
            "timestamp":time.time(),
            "DOT0":{"roll":0,"pitch":0,"yaw":0,"range":{"upper_bound": upper_bound, "lower_bound":lower_bound}},
            "DOT1":{"roll":0,"pitch":0,"yaw":0,"range":{"upper_bound": upper_bound, "lower_bound":lower_bound}},
            "DOT2":{"roll":0,"pitch":0,"yaw":0,"range":{"upper_bound": upper_bound, "lower_bound":lower_bound}},
            "DOT3":{"roll":0,"pitch":0,"yaw":0,"range":{"upper_bound": upper_bound, "lower_bound":lower_bound}},
            "DOT4":{"roll":0,"pitch":0,"yaw":0,"range":{"upper_bound": upper_bound, "lower_bound":lower_bound}}
        }
    }

    """t = threading.Thread(target=send_post_data, args=(stop_event, json_queue))
    t.daemon = True  # il thread si chiude quando il main thread termina
    t.start()"""

    while not stop_flag.is_set():
        elapsed_ms = movelladot_pc_sdk.XsTimeStamp_nowMs() - start_time_ms
        elapsed_sec = elapsed_ms / 1000
        sys.stdout.flush()

        # Mostro tempo trascorso
        sys.stdout.write(f"\rElapsed time: {elapsed_sec} seconds ")

        if xdpcHandler.packetsAvailable():
            limit = 20000
            values = [0,0,0,  0,0,0,  50]

            row = ""
            for device in xdpcHandler.connectedDots():
                packet = xdpcHandler.getNextPacket(device.portInfo().bluetoothAddress())
                name = device.deviceTagName()[8:8+4]
                if packet.containsOrientation():
                    euler = packet.orientationEuler()
                    roll, pitch, yaw = euler.x(), euler.y(), euler.z()
                    formatted = f"Roll: {roll:6.2f}, Pitch: {pitch:6.2f}, Yaw: {yaw:6.2f}"
                    row += f"{formatted:^{name_width}}| "
                    if "DOT3" in name:
                        values[0]=roll
                        values[1]=pitch
                        values[2]=yaw
                    elif "DOT2" in name: #device.deviceTagName():
                        values[3]=roll
                        values[4]=pitch
                        values[5]=yaw
                    values_in_json_sended_to_IoE_Server["MovellaData"][name]["roll"]=roll
                    values_in_json_sended_to_IoE_Server["MovellaData"][name]["pitch"]=pitch
                    values_in_json_sended_to_IoE_Server["MovellaData"][name]["yaw"]=yaw

                    
            row = row + "  | "+ str(len(row_in_csv))+"/"+str(limit) +"|  "+ str(len(row_in_csv)*100/limit)+"%"
            if len(row_in_csv) > limit:
                break
            sys.stdout.write(row)
            row_in_csv.append(values)

            values_in_json_sended_to_IoE_Server["MovellaData"]["timestamp"]=time.time()
            # URL del server a cui inviare i dati
            print("prima della post")
            """url = "http://193.205.129.120:63435/publish/sensor_movella"
            # Invio del JSON con POST
            response = requests.post(url, json=values_in_json_sended_to_IoE_Server, headers={"Content-Type": "application/json"})"""
            #json_queue.put(values_in_json_sended_to_IoE_Server.copy())
            print("dopo la post")
            # Controllo della risposta

        sys.stdout.flush()
        time.sleep(0.1)

    with open('dati_open_gabriele.csv',mode='w',newline='') as file:
        writer = csv.writer(file)
        writer.writerows(row_in_csv)

    """stop_event.set()
    t.join()"""
    
    
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
                        time.sleep(0.1)
                    print()
                thread.join()
            else:
                if show_flag:
                    show_data(xdpcHandler, runtime_params['duration'])
                else:
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


def run(filter_profile, payload_mode, duration, output_rate, show, send_flag, synch_flag, output_stream=sys.stdout):
    import builtins
    orig_print = builtins.print
    def gui_print(*args, **kwargs):
        kwargs.pop('file', None)
        orig_print(*args, **kwargs, file=output_stream)
        output_stream.flush()
    builtins.print = gui_print

    handler = XdpcHandler()
    try:
        if not initialize_and_connect(handler): return
        configure_devices(handler, filter_profile, output_rate)
        if synch_flag:
            if not synchronize_devices(handler):
                return
        else:
            print("Synchronization skipped by user request.")
        start_measurement(handler, PAYLOAD_MODES[payload_mode])

        if duration is None:
            if show:
                thread = threading.Thread(target=wait_for_enter)
                thread.start()
                show_data_indefinite(handler,send_flag)
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