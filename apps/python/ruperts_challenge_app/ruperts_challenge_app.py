import ac
import acsys
import math
import json
import os
import sys
import platform
import time
from telemetry_utility import TelemetryUtility
from api_manager import ApiManager

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

background = "apps/python/ruperts_challenge_app/images/with offset.png"
arrow_up = "apps/python/ruperts_challenge_app/images/arrow-up.png"
arrow_down = "apps/python/ruperts_challenge_app/images/arrow-down.png"
empty_texture = "apps/python/ruperts_challenge_app/images/empty-texture.png"

app_name = "Rupert's Challenge App"

app_window_width = 300
app_window_height = 191 # 154: 37 offset
scale = 1.0
offset = 37

iosevka = "Iosevka"
exo2 = "Exo 2"

appWindow = 0
driver_indicator = 0
delta_indicator = 0
speed_indicator = 0
gear_indicator = 0
delta_change_indicator = 0
running = True
valid_server = False
api_manager = 0

time_since_last_render = 0
render_period = 0.1 # s
telemetry_utility = 0
telemetry_update_period = 20 # s

different_gear_time = 0 # s
different_gear_threshold = 2 # s

DELTA_INCREASING = "increasing"
DELTA_STEADY = "steady"
DELTA_DECREASING = "decreasing"

last_lap_time_reading = 0

class DeltaIndicator:
    def __init__(self, app):
        self.delta_label = ac.addLabel(appWindow, "-0.00")

        ac.setPosition(self.delta_label, app_window_width / 2 - 6 * scale, 26 * scale + offset)
        ac.setFontSize(self.delta_label, 68 * scale)
        ac.setCustomFont(self.delta_label, "Iosevka", 0, 0)
        ac.setFontAlignment(self.delta_label, "center")
        self.setCurrentValue(-18.30)

    def setCurrentValue(self, value):
        if value >= 100:
            value = 99.99
        elif value <= -100:
            value = -99.99

        if abs(value) < 0.005:
            ac.setFontColor(self.delta_label, 1, 1, 1, 1)
        elif value < 0:
            ac.setFontColor(self.delta_label, 0, 1, 0, 1)
        elif value > 0:
            ac.setFontColor(self.delta_label, 1, 0.247, 0.247, 1)

        sign = ""
        if round(value, 2) == 0 and value >= 0:
            sign = "-"
        elif value > 0: 
            sign = "+"
        
        formatted_value = "{}{:.2f}".format(sign, value)
        ac.setText(self.delta_label, formatted_value)

class SpeedIndicator:
    def __init__(self, app):
        self.speed_label = ac.addLabel(appWindow, "73")

        ac.setPosition(self.speed_label, 92 * scale, 113 * scale + offset)
        ac.setFontSize(self.speed_label, 30 * scale)
        ac.setCustomFont(self.speed_label, iosevka, 0, 0)
        ac.setFontAlignment(self.speed_label, "right")

    def setCurrentValue(self, value):
        ac.setText(self.speed_label, "{:.0f}".format(value))

class GearIndicator:
    def __init__(self, app):
        self.gear_label = ac.addLabel(appWindow, "5")

        ac.setPosition(self.gear_label, 225 * scale, 113 * scale + offset)
        ac.setFontSize(self.gear_label, 30 * scale)
        ac.setCustomFont(self.gear_label, iosevka, 0, 0)
        ac.setFontAlignment(self.gear_label, "center")

    def setCurrentValue(self, value, warn):
        gear = value - 1 
        # Otherwise records when user is in neutral 
        # during change
        if gear > 0:
            ac.setText(self.gear_label, "{}".format(gear))
            if warn:
                ac.setFontColor(self.gear_label, 1, 0.7, 0, 1)
            else:
                ac.setFontColor(self.gear_label, 1, 1, 1, 1)

    
    def setNeutral(self):
        ac.setText(self.gear_label, "n")

class DriverNameAndLapIndicator:
    def __init__(self, app):
        self.driver_label = ac.addLabel(appWindow, "")

        ac.setPosition(self.driver_label, app_window_width / 2, offset)
        ac.setFontSize(self.driver_label, 15 * scale)
        ac.setCustomFont(self.driver_label, exo2, 0, 0)
        ac.setFontAlignment(self.driver_label, "center")

    def setCurrentValue(self, value):
        ac.setText(self.driver_label, value)

class DeltaChangeIndicator:
    def __init__(self, app):
        self.delta_change_label = ac.addLabel(appWindow, "")

        ac.setPosition(self.delta_change_label, 258 * scale, 80)
        ac.setFontSize(self.delta_change_label, 15 * scale)
        ac.setCustomFont(self.delta_change_label, exo2, 0, 0)
        ac.setSize(self.delta_change_label, 26 * scale, 50 * scale)

        self.setDeltaChange(DELTA_INCREASING)
    
    def setDeltaChange(self, deltaChange):
        if deltaChange == DELTA_DECREASING:
            ac.setBackgroundTexture(self.delta_change_label, arrow_down)
        elif deltaChange == DELTA_STEADY:
            ac.setBackgroundTexture(self.delta_change_label, empty_texture)
        elif deltaChange == DELTA_INCREASING:
            ac.setBackgroundTexture(self.delta_change_label, arrow_up)

def next_driver(*args):
    global different_gear_time
    different_gear_time = 0
    api_manager.next_driver()

def previous_driver(*args):
    global different_gear_time
    different_gear_time = 0
    api_manager.previous_driver()

# This function gets called by AC when the Plugin is initialised
# The function has to return a string with the plugin name
def acMain(ac_version):
    global longitudinalGIndicator, appWindow, driver_indicator, delta_indicator, speed_indicator, gear_indicator, delta_change_indicator, api_manager, telemetry_utility, app_window_height, app_window_width, scale, valid_server
    
    appWindow = ac.newApp(app_name)
    ac.setBackgroundOpacity(appWindow, 0)
    ac.setTitle(appWindow, "")
    ac.initFont(0, "Exo2", 0, 0)
    ac.setIconPosition(appWindow, 0, -10000) # Hide icon
    ac.setSize(appWindow, app_window_width, app_window_height)
    ac.drawBorder(appWindow, 0)
    
    telemetry_utility = TelemetryUtility()
    api_manager = ApiManager(telemetry_utility, telemetry_update_period)

    # Manually fetch server data
    # This potentially shouldn't be in here...
    api_manager.fetch_leaderboard()
    if api_manager.challenge_info:
        active_challenge_name = api_manager.challenge_info["challengeName"]
        if ac.getServerName() == active_challenge_name:
            valid_server = True
        else:
            return app_name
            

    api_manager.start()
    
    ac.setBackgroundTexture(appWindow, background)

    # Render buttons
    left_button = ac.addButton(appWindow, "")
    ac.setBackgroundOpacity(left_button, 0)
    ac.setSize(left_button, 36, 30)
    ac.setPosition(left_button, 0, 31)
    ac.drawBorder(left_button, 0)
    ac.addOnClickedListener(left_button, previous_driver)
        
    right_button = ac.addButton(appWindow, "")
    ac.setBackgroundOpacity(right_button, 0)
    ac.setSize(right_button, 36, 30)
    ac.setPosition(right_button, app_window_width - 36, 31)
    ac.drawBorder(right_button, 0)
    ac.addOnClickedListener(right_button, next_driver)

    # Render indicators
    delta_indicator = DeltaIndicator(appWindow)
    speed_indicator = SpeedIndicator(appWindow)
    gear_indicator = GearIndicator(appWindow)
    driver_indicator = DriverNameAndLapIndicator(appWindow)
    delta_change_indicator = DeltaChangeIndicator(appWindow)

    return app_name


def acUpdate(deltaT):
    global appWindow, driver_indicator, delta_indicator, delta_change_indicator, speed_indicator, api_manager, gear_indicator, telemetry_utility, time_since_last_render, last_lap_time_reading, different_gear_time
    ac.setBackgroundOpacity(appWindow, 0)
    
    if not valid_server:
        return

    if time_since_last_render < render_period:
        time_since_last_render += deltaT
        return
    else:
        time_since_last_render = 0
    
    # Driver info
    driver_indicator.setCurrentValue(api_manager.get_selected_driver())

    current_laptime = ac.getCarState(0, acsys.CS.LapTime)
    current_spline = ac.getCarState(0, acsys.CS.NormalizedSplinePosition)
    current_gear = ac.getCarState(0, acsys.CS.Gear)

    telemetry_data = telemetry_utility.get_telemetry_data(current_laptime, current_spline)
    if not telemetry_data:
        # Zero displays
        delta_indicator.setCurrentValue(0)
        speed_indicator.setCurrentValue(0)
        gear_indicator.setNeutral()
        delta_change_indicator.setDeltaChange(DELTA_STEADY)
        return
    
    delta_ms = telemetry_data["delta"]
    delta_s = delta_ms / 1000
    delta_indicator.setCurrentValue(delta_s)

    current_speed = ac.getCarState(0, acsys.CS.SpeedKMH)
    speed_delta = telemetry_data["speed"] - current_speed
    if speed_delta > 2:
        delta_change_indicator.setDeltaChange(DELTA_DECREASING)
    elif speed_delta < -2:
        delta_change_indicator.setDeltaChange(DELTA_INCREASING)
    else:
        delta_change_indicator.setDeltaChange(DELTA_STEADY)

    speed_indicator.setCurrentValue(telemetry_data["speed"])

    # Gear
    if current_gear == telemetry_data["gear"]:
        different_gear_time = 0
    else:
        different_gear_time += render_period
        
    gear_indicator.setCurrentValue(telemetry_data["gear"], different_gear_time >= different_gear_threshold)

    # Delay when new lap set to ensure latest
    # telemetry is returned by server
    if current_laptime < last_lap_time_reading and current_laptime > 5000:
        last_lap_time_reading = current_laptime
        api_manager.update()

def acShutdown():
    # Clear up threads
    api_manager.stop()
