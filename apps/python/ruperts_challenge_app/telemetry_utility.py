import math
import ac
import threading

class TelemetryUtility:
    def __init__(self):
        self.telemetry = {}
        self.telemetry_keys = []
        self.telemetry_access_lock = threading.Lock()

    def set_telemetry(self, telemetry):
        self.telemetry_access_lock.acquire()
        try:
            self.telemetry = telemetry
            self.telemetry_keys = list(telemetry.keys())
            self.telemetry_keys.sort(key = lambda x: float(x))
        finally:
            self.telemetry_access_lock.release()

    def get_telemetry_data(self, currentLaptime, currentSpline):

        def weighted_interpolation(xs, ys, currentx):
            '''
            Returns a weighted linear interpolation at currentx from four
            sampled points in xy space - two ahead and two behind

            Parameters
            ----------
            xs : array
                an array containing 4 ordered x points
            ys : array
                an array containing 4 ordered y points
            currentx : float
                the current x position for which a y estimate is required

            Returns
            -------
            float
                the estimated y value for current x

            '''
            grad12 = (ys[2] - ys[1])/(xs[2] - xs[1])
            grad13 = (ys[3] - ys[1])/(xs[3] - xs[1])
            grad03 = (ys[3] - ys[0])/(xs[3] - xs[0])
            grad02 = (ys[2] - ys[0])/(xs[2] - xs[0])

            est12 = ys[1] + (currentx - xs[1]) * grad12
            est13 = ys[1] + (currentx - xs[1]) * grad13
            est03 = ys[0] + (currentx - xs[0]) * grad03
            est02 = ys[0] + (currentx - xs[0]) * grad02

            return (5*est12 + 2*est03 + est13 + est02)/9

        telemetry_data = {}
        self.telemetry_access_lock.acquire()
        try:
            if self.telemetry:
                '''
                key_index_1, key_index_2 = self.index_of_closest(currentLaptime, currentSpline)

                telemetry_entry_1 = self.telemetry[self.telemetry_keys[key_index_1]]
                telemetry_entry_2 = self.telemetry[self.telemetry_keys[key_index_2]]
                spline_on_best_1 = float(self.telemetry_keys[key_index_1])
                spline_on_best_2 = float(self.telemetry_keys[key_index_2])
                '''

                #get the indices we care about
                indices = [0, 0, 0, 0]
                indices[1], indices[2] = self.index_of_closest(currentLaptime, currentSpline)
                indices[0] = (indices[1] - 1) % len(self.telemetry_keys)
                indices[3] = (indices[2] + 1) % len(self.telemetry_keys)
                splines = [float(self.telemetry_keys[index]) for index in indices]
                times = [self.telemetry[self.telemetry_keys[index]]["laptime"] for index in indices]
                speeds = [self.calculate_velocity_from_mps_vector(self.telemetry[self.telemetry_keys[index]]["velocity"]) for index in indices]
                gear = self.telemetry[self.telemetry_keys[indices[2]]]["gear"]


        finally:
            self.telemetry_access_lock.release()

        if not self.telemetry:
            return telemetry_data

        '''
        # Delta calculation
        laptime_on_best_1 = telemetry_entry_1["laptime"]
        laptime_on_best_2 = telemetry_entry_2["laptime"]

        gradient = (laptime_on_best_2 - laptime_on_best_1) / (spline_on_best_2 - spline_on_best_1)
        estimated_lap_time = laptime_on_best_1 + (currentSpline - spline_on_best_1) * gradient

        delta_ms = currentLaptime - estimated_lap_time
        telemetry_data["delta"] = delta_ms

        # Calculate velocity
        speed_on_best_1 = self.calculate_velocity_from_mps_vector(telemetry_entry_1["velocity"])
        speed_on_best_2 = self.calculate_velocity_from_mps_vector(telemetry_entry_2["velocity"])
        gradient = (speed_on_best_2 - speed_on_best_1) / (spline_on_best_2 - spline_on_best_1)
        estimated_speed = speed_on_best_1 + (currentSpline - spline_on_best_1) * gradient
        telemetry_data["speed"] = estimated_speed

        # Gear
        telemetry_data["gear"] = telemetry_entry_2["gear"]
        '''

        telemetry_data["delta"] = currentLaptime - weighted_interpolation(splines, times, currentSpline)
        telemetry_data["speed"] = weighted_interpolation(splines, speeds, currentSpline)
        telemetry_data["gear"] = gear

        return telemetry_data

    def calculate_velocity_from_mps_vector(self, mps_vector):
        sum_of_squares = mps_vector["x"] ** 2 + mps_vector["y"] ** 2 + mps_vector["z"] ** 2
        if sum_of_squares > 0:
            return math.sqrt(sum_of_squares) * 3.6
        else:
            return 0

    def index_of_closest(self, currentLaptime, currentSpline):
        start = 0
        end = len(self.telemetry_keys) - 1

        # if spline lower than lowest value in telem - wrap around
        if currentSpline < float(self.telemetry_keys[start]) or currentSpline > float(self.telemetry_keys[end]):
            return end, start

        while end - start > 1:
            comparator_index = math.floor((end - start) / 2) + start
            if currentSpline < float(self.telemetry_keys[comparator_index]):
                end = comparator_index
            else:
                start = comparator_index

        return start, end
