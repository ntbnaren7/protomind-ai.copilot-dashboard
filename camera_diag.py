import cv2, time
BACKENDS = [cv2.CAP_DSHOW, cv2.CAP_MSMF]
for be in BACKENDS:
    name = "CAP_DSHOW" if be == cv2.CAP_DSHOW else "CAP_MSMF"
    for idx in range(3):
        cap = cv2.VideoCapture(idx, be)
        ok = cap.isOpened()
        print(f"[{name}] index {idx}: {'OPENED' if ok else 'fail'}")
        if ok:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            time.sleep(0.2)
            ret, frm = cap.read()
            print("   read:", "ok" if ret else "fail", "mean=", (frm.mean() if ret else None))
            cap.release()
