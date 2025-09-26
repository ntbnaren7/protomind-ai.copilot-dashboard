import cv2
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
img = cv2.aruco.generateImageMarker(aruco_dict, 0, 300)
cv2.imwrite("aruco_marker_id0_5cm.png", img)
print("Saved: aruco_marker_id0_5cm.png (print at 5 cm x 5 cm)")
