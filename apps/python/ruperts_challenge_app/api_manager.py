import threading
import ac
import time
import os
import sys 
import platform
import json
import math

PATH_APP = os.path.dirname(__file__)
path_stdlib=''
if platform.architecture()[0] == '64bit':
    path_stdlib = os.path.join(PATH_APP, 'stdlib64')
else:
    path_stdlib = os.path.join(PATH_APP, 'stdlib')
sys.path.insert(0, path_stdlib)
sys.path.insert(0, os.path.join(PATH_APP, 'third_party'))

os.environ['PATH'] = os.environ['PATH'] + ';.'

import requests

domain = "http://rupertsracing.com"

leaderboard_request_route = "{}/api/v1/challenges?".format(domain)
telemetry_request_route = "{}/api/v1/telemetry".format(domain)

def laptime_to_readable(laptime):
    minutes = math.floor(laptime / (1000 * 60))
    laptime -= 1000 * 60 * minutes
    seconds = math.floor(laptime / (1000))
    laptime -= 1000 * seconds
    milli = "{}".format(round(laptime / 10))
    return "{}:{}.{}".format(minutes, seconds, milli)

class ApiManager:
    def __init__(self, telemetry_utility, telemetry_update_period):
        self.telemetry_utility = telemetry_utility
        self.running = False
        self.thread = 0
        self.telemetry_update_request = False
        self.telemetry_update_period = telemetry_update_period
        self.challenge_info = {}

        self.selected_driver_index = 0
        self.current_car = ""
        self.current_track = ""
        self.current_track_layout = ""

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.main)
        self.thread.start()

    def update(self):
        self.telemetry_update_request = True

    def stop(self):
        self.running = False

    def next_driver(self, *args):
        if not self.challenge_info:
            return

        self.selected_driver_index = self.selected_driver_index + 1
        if self.selected_driver_index >= len(self.challenge_info["leaderboard"]):
            self.selected_driver_index = len(self.challenge_info["leaderboard"]) - 1
    
        self.telemetry_update_request = True

    def previous_driver(self, *args):
        self.selected_driver_index = self.selected_driver_index - 1
        if self.selected_driver_index <= 0:
            self.selected_driver_index = 0
                
        self.telemetry_update_request = True
    
    def set_current_car(self, car):
        self.current_car = car
    
    def set_current_track(self, track):
        self.current_track = track
    
    def set_current_layout(self, layout):
        self.current_track_layout = layout
    
    def get_challenge_name(self):
        if not self.challenge_info:
            return ""
        return self.challenge_info["challengeName"]

    def get_selected_driver(self):
        if not self.challenge_info or len(self.challenge_info["leaderboard"]) == 0:
            return ""
        
        if self.selected_driver_index >= len(self.challenge_info["leaderboard"]):
            return ""

        selected_leaderboard_entry = self.challenge_info["leaderboard"][self.selected_driver_index]
        driver_name = selected_leaderboard_entry["assettoDisplayName"]
        if len(driver_name) > 20:
            driver_name = driver_name[:17] + "..."

        readable_laptime = laptime_to_readable(selected_leaderboard_entry["laptime"])
        return "{}. {} - {}".format(selected_leaderboard_entry["position"], driver_name, readable_laptime)        
    
    def fetch_leaderboard(self):
        try:
            response = requests.get("{}car={}&track={}&layout={}".format(leaderboard_request_route, self.current_car, self.current_track, self.current_track_layout), timeout=5)
            if response.status_code == 200:
                data = json.loads(response.text)
                self.challenge_info = data
            else:
                self.challenge_info = {}

        except Exception as e:
            ac.log("{}".format(e))      

    def fetch_telemetry(self):
        if not self.challenge_info:
            return

        try:
            # Normalise selected driver index in case leaderboard has changed
            self.selected_driver_index = min(self.selected_driver_index, len(self.challenge_info["leaderboard"]) - 1)
            response = requests.get(telemetry_request_route + "/{}/challenge/{}".format(self.selected_driver_index, self.challenge_info["id"]), timeout=5)
            if response.status_code == 200:
                data = json.loads(response.text)
                self.telemetry_utility.set_telemetry(data["telemetryEntries"])
            else:
                self.telemetry_utility.set_telemetry({})
        except Exception as e:
            ac.log("{}".format(e))

    def main(self):
        self.fetch_leaderboard()
        self.fetch_telemetry()

        time_of_last_fetch = 0
        while self.running:
            current_time = time.time()
            if current_time - time_of_last_fetch > self.telemetry_update_period or self.telemetry_update_request:
                time_of_last_fetch = current_time
                self.telemetry_update_request = False

                self.fetch_leaderboard()
                self.fetch_telemetry()
            
            # Prevents thread from consuming excess resources
            time.sleep(2)
