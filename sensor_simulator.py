import time
import math
import random
import threading

class SensorSimulator:
    def __init__(self, update_interval=1.0):
        self._lock = threading.Lock()
        self._running = False
        self._interval = update_interval
        self._state = "RUNNING"
        self._data = {
            "temperature_c": 25.0,
            "pressure_bar": 1.0,
            "load_pct": 50.0,
            "throughput": 100,
            "vibration": 1.5,
            "humidity": 40.0
        }
        self._stress_until = 0.0
        self._stress_intensity = 0.0

    def start(self):
        if not self._running:
            self._running = True
            threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._running = False

    def set_state(self, state: str):
        with self._lock:
            self._state = state

    def trigger_stress(self, seconds=30, intensity=0.9):
        with self._lock:
            self._stress_until = time.time() + max(5, int(seconds))
            self._stress_intensity = max(0.2, min(1.0, float(intensity)))

    def cancel_stress(self):
        with self._lock:
            self._stress_until = 0.0
            self._stress_intensity = 0.0

    def stress_status(self):
        with self._lock:
            remaining = max(0, int(self._stress_until - time.time()))
            return {"active": remaining > 0, "seconds_left": remaining}

    def get_data(self):
        with self._lock:
            return dict(self._data)

    def _loop(self):
        t0 = time.time()
        while self._running:
            t = time.time() - t0
            with self._lock:
                stress_active = time.time() < self._stress_until
                k = self._stress_intensity if stress_active else 0.0

                # Dynamic oscillating load with stress boost
                load_wave = 50 + 20 * math.sin(2 * math.pi * (t / 18.0))
                stress_boost = 35 * k
                self._data["load_pct"] = max(0, min(120, load_wave + stress_boost + random.uniform(-6, 6)))

                temp_target = 28 + (self._data["load_pct"] / 120.0) * 70 + 8 * k
                press_target = 1.1 + (self._data["load_pct"] / 120.0) * 3.6 + 0.4 * k
                vib_target = 1.8 + (self._data["load_pct"] / 100.0) * 6.0 + (press_target - 1.1) * 0.5 + 1.2 * k

                if random.random() < (0.03 + 0.05 * k): vib_target += random.uniform(0.8, 1.8)
                if random.random() < (0.02 + 0.03 * k): temp_target += random.uniform(2.0, 5.0)
                if random.random() < (0.02 + 0.03 * k): press_target += random.uniform(0.15, 0.45)

                if self._state == "STOPPED":
                    temp_target -= 0.5
                    press_target -= 0.05
                    vib_target -= 0.1
                    self._data["throughput"] = max(0, self._data["throughput"] - 5)
                else:
                    self._data["throughput"] = min(300, self._data["throughput"] + random.randint(-2, 5))

                self._data["temperature_c"] += (temp_target - self._data["temperature_c"]) * 0.1
                self._data["pressure_bar"] += (press_target - self._data["pressure_bar"]) * 0.1
                self._data["vibration"] += (vib_target - self._data["vibration"]) * 0.1
                self._data["humidity"] = max(20, min(80, 40 + 5 * math.sin(t / 30.0) + random.uniform(-2, 2)))

            time.sleep(self._interval)
