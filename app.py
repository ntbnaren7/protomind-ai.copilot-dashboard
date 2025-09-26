import os, time, math, threading, urllib.request
import numpy as np
import cv2
from flask import Flask, render_template, Response, jsonify, request

from sensor_simulator import SensorSimulator
from aruco_utils import ArucoDistanceEstimator

app = Flask(__name__)

# -------------------- Simulator --------------------
sim = SensorSimulator(update_interval=1.0)
# Use start() if your SensorSimulator has it; otherwise thread _loop directly
if hasattr(sim, "start"):
    sim.start()
else:
    threading.Thread(target=sim._loop, daemon=True).start()

# -------------------- ArUco distance --------------------
aruco = ArucoDistanceEstimator(
    marker_size=0.05,     # 5 cm marker
    target_id=None,       # detect any ID
    smooth_alpha=0.35,
    draw_axes=True
)

# -------------------- Human (face) detector --------------------
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)

# -------------------- System state --------------------
latest_frame = None
last_distance = None
system_state = "RUNNING"
lock = threading.Lock()

RISK_WARNING = 0.50
RISK_CRITICAL = 0.70

# for stress-driven virtual distance squeeze
stress_started_at = 0.0

# -------------------- Camera source selection --------------------
IP_CAM_URL = os.environ.get("IP_CAM_URL", "").strip()                 # e.g. http://PHONE_IP:8080/video
IP_CAM_SNAPSHOT_URL = os.environ.get("IP_CAM_SNAPSHOT_URL", "").strip()  # e.g. http://PHONE_IP:8080/shot.jpg
print("IP_CAM_URL =", repr(IP_CAM_URL), "IP_CAM_SNAPSHOT_URL =", repr(IP_CAM_SNAPSHOT_URL))

CAP_MODE = "demo"     # "stream" | "snapshot" | "local" | "demo"
CAP_OBJ = None

def _read_snapshot(url, timeout=3.0):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()
        arr = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None

def _open_local_camera():
    for backend in (cv2.CAP_DSHOW, cv2.CAP_MSMF):
        cap = cv2.VideoCapture(0, backend)
        if cap.isOpened():
            return cap
    return None

# Prefer IP stream
if IP_CAM_URL:
    c = cv2.VideoCapture(IP_CAM_URL)
    print("Trying IP stream:", IP_CAM_URL, "opened:", c.isOpened())
    if c.isOpened():
        CAP_MODE, CAP_OBJ = "stream", c

# Then snapshot
if CAP_OBJ is None and IP_CAM_SNAPSHOT_URL:
    print("Using IP snapshot:", IP_CAM_SNAPSHOT_URL)
    CAP_MODE = "snapshot"

# Then local webcam
if CAP_OBJ is None and CAP_MODE != "snapshot":
    c = _open_local_camera()
    if c is not None:
        print("Using local webcam")
        CAP_MODE, CAP_OBJ = "local", c

# Finally demo
if CAP_OBJ is None and CAP_MODE != "snapshot":
    print("Falling back to DEMO camera")
    CAP_MODE = "demo"

# -------------------- Risk model --------------------
def compute_risk(s, d):
    temp = min(1.0, s["temperature_c"] / 100.0)
    pres = min(1.0, s["pressure_bar"] / 5.0)
    load = min(1.0, s["load_pct"] / 120.0)
    vib  = min(1.0, s["vibration"] / 12.0)
    hum  = min(1.0, s["humidity"] / 80.0)
    dist = 0.0 if d is None else max(0.0, 1.0 - min(d / 2.0, 1.0))  # 0..2m -> 1..0
    risk = 0.25*temp + 0.20*pres + 0.15*load + 0.15*vib + 0.10*hum + 0.15*dist
    return round(float(risk), 3)

# -------------------- Video thread --------------------
def video_loop():
    global latest_frame, last_distance, system_state, stress_started_at

    t0 = time.time()
    consecutive_fail = 0

    while True:
        # 1) Read a frame
        if CAP_MODE in ("stream", "local"):
            ok, frame = CAP_OBJ.read()
            if not ok or frame is None:
                consecutive_fail += 1
                if consecutive_fail > 200:
                    # try fallback to snapshot if configured, else demo
                    if IP_CAM_SNAPSHOT_URL:
                        print("Stream failing; switching to SNAPSHOT.")
                        CAP_MODE_local = "snapshot"
                    else:
                        print("Stream failing; switching to DEMO.")
                        CAP_MODE_local = "demo"
                    # local switch within loop
                    while CAP_MODE_local == "snapshot":
                        frame = _read_snapshot(IP_CAM_SNAPSHOT_URL)
                        if frame is not None: break
                        time.sleep(0.06)
                    if CAP_MODE_local == "demo":
                        frame = None
                    consecutive_fail = 0
                time.sleep(0.02)
                continue
        elif CAP_MODE == "snapshot":
            frame = _read_snapshot(IP_CAM_SNAPSHOT_URL)
            if frame is None:
                time.sleep(0.06)
                continue
        else:  # demo mode
            h, w = 480, 854
            frame = (np.zeros((h, w, 3), dtype=np.uint8) + 12)
            y = int((np.sin((time.time()-t0)/1.3)*0.5+0.5)*(h-60))+30
            cv2.rectangle(frame, (30, y-8), (w-30, y+8), (40, 120, 220), -1)
            cv2.putText(frame, "DEMO CAMERA (no webcam/stream)", (24, 36),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 180, 180), 2)

        # 2) ArUco distance
        distance_m, frame = aruco.estimate_distance(frame)

        # 3) Virtual squeeze when stress active and no marker
        st = sim.stress_status()
        if distance_m is None and st.get("active"):
            elapsed = max(0.0, time.time() - (stress_started_at or time.time()))
            squeeze = min(1.0, elapsed / 8.0)
            base = 1.6 - 1.0 * squeeze           # 1.6 -> 0.6 m
            wobble = 0.05 * math.sin(elapsed * 3)
            distance_m = max(0.45, base + wobble)

        # 4) Simple human (face) overlay
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.15, minNeighbors=5, minSize=(60, 60))
            if len(faces) > 0:
                (x, y, w, h) = faces[0]
                cv2.rectangle(frame, (x, y), (x+w, y+h), (50, 220, 100), 2)
                cv2.putText(frame, "Human detected", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 220, 100), 2)
        except Exception:
            pass

        # 5) Risk, state & overlays
        sensors = sim.get_data() if hasattr(sim, "get_data") else sim.get_sensor_data()
        risk = compute_risk(sensors, distance_m)

        new_state = "STOPPED" if risk >= RISK_CRITICAL else ("RUNNING" if risk < RISK_WARNING else system_state)
        if new_state != system_state:
            system_state = new_state
            if hasattr(sim, "set_state"):
                sim.set_state(system_state)

        color = (0, 0, 255) if system_state == "STOPPED" else (0, 255, 0)
        cv2.putText(frame, f"System: {system_state}", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2)
        cv2.putText(frame, f"Risk: {risk:.2f}", (20, 104), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 200, 255), 2)

        ok_jpg, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ok_jpg:
            with lock:
                latest_frame = jpg.tobytes()
                last_distance = float(distance_m) if distance_m is not None else None

        time.sleep(0.03)

# -------------------- Flask routes --------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/video_feed")
def video_feed():
    def gen():
        while True:
            with lock:
                buf = latest_frame
            if buf is not None:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf + b"\r\n")
            time.sleep(0.05)
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/sensor_data")
def sensor_data():
    s = sim.get_data() if hasattr(sim, "get_data") else sim.get_sensor_data()
    with lock:
        d = last_distance
        st = system_state
    risk = compute_risk(s, d)
    return jsonify({
        "sensors": s,
        "distance_m": d,
        "risk": risk,
        "system_state": st,
        "stress": sim.stress_status() if hasattr(sim, "stress_status") else {"active": False, "seconds_left": 0}
    })

# ---- Stress routes ----
@app.route("/stress/start", methods=["POST", "GET"])
def stress_start():
    global stress_started_at
    secs = request.args.get("seconds")
    intensity = request.args.get("intensity")
    if request.is_json and (secs is None or intensity is None):
        body = request.get_json(silent=True) or {}
        secs = secs or body.get("seconds")
        intensity = intensity or body.get("intensity")
    try: secs = int(secs) if secs is not None else 30
    except: secs = 30
    try: intensity = float(intensity) if intensity is not None else 0.9
    except: intensity = 0.9

    if hasattr(sim, "trigger_stress"): sim.trigger_stress(seconds=secs, intensity=intensity)
    stress_started_at = time.time()
    return jsonify({"ok": True, "seconds": secs, "intensity": intensity})

@app.route("/stress/stop", methods=["POST", "GET"])
def stress_stop():
    if hasattr(sim, "cancel_stress"): sim.cancel_stress()
    return jsonify({"ok": True})

# ---- Compat (optional) ----
@app.route("/api/system")
def api_system():
    s = sim.get_data() if hasattr(sim, "get_data") else sim.get_sensor_data()
    with lock:
        d = last_distance
        st = system_state
    risk = compute_risk(s, d)
    return jsonify({"state": st, "risk": risk, "distance_m": d})

@app.route("/api/suggestions")
def api_suggestions():
    s = sim.get_data() if hasattr(sim, "get_data") else sim.get_sensor_data()
    with lock:
        d = last_distance
    risk = compute_risk(s, d)
    tips = []
    if d is None: tips.append("Show ArUco marker to enable precise distance monitoring.")
    if risk >= RISK_CRITICAL: tips.append("CRITICAL: Auto-STOP engaged. Increase distance and lower load.")
    elif risk >= RISK_WARNING: tips.append("WARNING: Reduce speed/load to lower temperature/pressure.")
    else: tips.append("SAFE: Conditions nominal.")
    return jsonify({"suggestions": tips})

if __name__ == "__main__":
    threading.Thread(target=video_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
