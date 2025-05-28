import requests
import json

import time

timestamp = time.time()
print(timestamp)

# Il tuo dizionario Python (JSON)
"""data = {
    "Identifier": {
        "token": String,
        "id": String,
        "device": String,
        "model": String
    },
    "MovellaData": {
        "timestamp": Array<Long>,
        "DOT0":{ "roll":Array<Float>, "pitch":Array<Float>, "yaw":Array<Float>, "range": {"upper_bound": Float, "lower_bound": Float} },
        "DOT1":{ "roll":Array<Float>, "pitch":Array<Float>, "yaw":Array<Float>, "range": {"upper_bound": Float, "lower_bound": Float} },
        "DOT2":{ "roll":Array<Float>, "pitch":Array<Float>, "yaw":Array<Float>, "range": {"upper_bound": Float, "lower_bound": Float} },
        "DOT3":{ "roll":Array<Float>, "pitch":Array<Float>, "yaw":Array<Float>, "range": {"upper_bound": Float, "lower_bound": Float} },
        "DOT4":{ "roll":Array<Float>, "pitch":Array<Float>, "yaw":Array<Float>, "range": {"upper_bound": Float, "lower_bound": Float} }
    }
}"""

def initialize_json(token, id_, device, model):
    return {
        "Identifier": {
            "token": token,
            "id": id_,
            "device": device,
            "model": model
        },
        "MovellaData": {
            "timestamp": 0,
            "DOT0": {"roll": 0, "pitch": 0, "yaw": 0, "range": {"upper_bound": 0, "lower_bound": 0}},
            "DOT1": {"roll": 0, "pitch": 0, "yaw": 0, "range": {"upper_bound": 0, "lower_bound": 0}},
            "DOT2": {"roll": 0, "pitch": 0, "yaw": 0, "range": {"upper_bound": 0, "lower_bound": 0}},
            "DOT3": {"roll": 0, "pitch": 0, "yaw": 0, "range": {"upper_bound": 0, "lower_bound": 0}},
            "DOT4": {"roll": 0, "pitch": 0, "yaw": 0, "range": {"upper_bound": 0, "lower_bound": 0}}
        }
    }

def insert_data(json_data, dot_index, timestamp, roll, pitch, yaw):
    key = f"DOT{dot_index}"
    if key in json_data["MovellaData"]:
        json_data["MovellaData"]["timestamp"] = timestamp
        json_data["MovellaData"][key]["roll"] = roll
        json_data["MovellaData"][key]["pitch"]= pitch
        json_data["MovellaData"][key]["yaw"] = yaw
        print(f"Dati inseriti in {key}: R={roll:.2f}, P={pitch:.2f}, Y={yaw:.2f}")

# Converti il dizionario in una stringa JSON
concat_id = 0
json_data= initialize_json("example_token", concat_id, "MovellaDot", "Xsense MovellaDOTS" ) # id|id|id|id|id
json_string = json.dumps(json_data)

# URL a cui inviare la richiesta
url = "http://193.205.129.120:63435/publish/sensor_movella"

# Invia una POST con il JSON come stringa nel corpo della richiesta
response = requests.post(url, data=json_string, headers={"Content-Type": "application/json"})

# Stampa la risposta
print(response.status_code)
print(response.text)
