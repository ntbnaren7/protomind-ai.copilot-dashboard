# save as test_ip_cam.py and run inside your venv
import cv2, sys, time
url = "http://192.0.0.2:8080/video"  # change if needed
cap = cv2.VideoCapture(url)
print("Opened:", cap.isOpened())
for i in range(10):
    ok, frame = cap.read()
    print(i, "read:", ok, "mean:", (frame.mean() if ok else None))
    time.sleep(0.1)
cap.release()
