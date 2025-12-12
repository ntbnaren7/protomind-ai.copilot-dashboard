# **SentinelWorks – Industry 5.0 Human–Machine Collaboration Prototype**

**SentinelWorks** is a simulated Industry 5.0 system demonstrating how smart sensors, AI-driven monitoring, and real-time human–machine collaboration can optimize industrial processes.

> This project was developed for **OBVN’25 – a 24-hour National Hackathon hosted by SNS College of Engineering and Technology, Coimbatore.**

---

## 📌 Overview

Industrial environments are becoming increasingly complex, requiring tighter synergy between humans and intelligent machines.  
This prototype presents a **functional simulation interface** showcasing:

- Real-time sensor monitoring  
- Adaptive camera feed visualization  
- Human interaction detection (simulated)  
- Minimalistic industrial dashboard UI  
- A structure ready for future AI integration  

This is **not a production system** — it is a **working template** created within hackathon constraints to demonstrate feasibility and concept clarity.

---

## 🔧 Key Features

### 🎥 Camera Monitoring  
- Supports **Webcam/IP camera**  
- Automatic fallback to **demo video**  
- Smooth, optimized rendering for dashboards  

### 📡 Smart Sensor Simulation  
Live simulated values for:
- Temperature  
- Movement/Vibration  
- Stress/Load  
- Human detection events  

### 📊 Real-Time Minimal Charts  
- Lightweight, distraction-free visualizations  
- Auto-refresh  
- Designed for industrial environment clarity  

### 🧠 AI-Ready Architecture  
Built to easily plug in:
- ML/AI models  
- Worker-safety alerts  
- Predictive maintenance modules  
- Anomaly detection  

---

## 🏗️ System Architecture
IP Camera / Webcam → OpenCV → Flask Stream → Web UI (Video Panel)
Simulated Sensor Engine → Flask API → Chart.js → Dashboard Panels

---


Hardware components can be replaced with real sensors without UI rewrites.

---

## 🚀 Tech Stack

- **Backend:** Python (Flask)  
- **Frontend:** HTML, CSS, JavaScript  
- **Charts:** Chart.js  
- **Video:** OpenCV  
- **Simulation:** Custom Sensor Engine  
- **Environment:** Localhost (Demo-Ready)  

---

## 🎯 Purpose of This Prototype

This build demonstrates:

- A realistic Industry 5.0 monitoring workflow  
- Live collaboration between humans and intelligent systems  
- Safe, efficient, adaptive process supervision  
- Hackathon-feasible implementation  
- A scalable architecture for future industrial integration  

It is intended as a **conceptual and visual demonstration**, not a completed industrial product.

---

## 📁 Folder Structure
.
├── app.py
├── aruco_utils.py # Optional module for distance estimation
├── static/
│ ├── styles.css
│ └── script.js
└── templates/
└── index.html

---

## 🏃 Getting Started

### 1. Install Dependencies
```
bash
pip install -r requirements.txt
2. (Optional) Set IP Camera URL
export IP_CAM_URL="http://<your-ip>:8080/video"

3. Run the Application
python app.py

4. Open in Browser
http://127.0.0.1:5000/
```

🔮 Future Enhancements

Real industrial sensor integration

YOLO/OpenCV or MediaPipe-based human detection

Predictive maintenance insights

Safety alert system for workers

AR-assisted operator view

Multi-sensor fusion layer

Cloud dashboard + analytics

📝 Disclaimer

This dashboard is a simulated prototype, created specifically for
OBVN’25 - National 24 Hour Hackathon, to demonstrate a feasible Industry 5.0 concept.

🤝 License

Released under the MIT License - free to use, modify, and expand.
