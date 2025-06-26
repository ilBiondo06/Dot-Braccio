import json
import time
import requests



class MovellaDataPublisher:
    SEND_URL = "http://193.205.129.120:63435/publish/sensor_movella"
    def __init__(self, url=SEND_URL):
        self.url = url

    def build_payload(self, id_all, device_names, orientation_data):
        # Build the JSON structure
        payload = {
            "Identifier": {
                "id": id_all,
                "device": "Sensor",
                "model": "Movella Xsens Dot"
            },
            "MovellaData": { "timestamp": time.time() }
        }
        # Insert each device's roll, pitch, yaw, and range
        for name in device_names:
            roll, pitch, yaw = orientation_data.get(name, (0,0,0))
            payload["MovellaData"][name] = {
                "roll": roll,
                "pitch": pitch,
                "yaw": yaw,
                "range": {"upper_bound": 180, "lower_bound": -180}
            }
        return payload

    def publish(self, id_all, device_names, orientation_data):
        payload = self.build_payload(id_all, device_names, orientation_data)
        try:
            response = requests.post(self.url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            print(f"Published data: {payload}")
            print(f"Status code: {response.status_code}")
        except requests.RequestException as e:
            print(f"Failed to publish data: {e}")
