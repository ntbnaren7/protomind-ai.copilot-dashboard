import cv2
import numpy as np
from collections import deque

class ArucoDistanceEstimator:
    """
    Robust ArUco distance estimator with smoothing and sensible defaults.

    Args:
        marker_size (float): Physical marker size in meters (e.g., 0.05 for 5 cm).
        camera_matrix (np.ndarray|None): 3x3 intrinsics. If None, uses a sane default.
        dist_coeffs (np.ndarray|None): Distortion coeffs (5x1). If None, assumes zero distortion.
        target_id (int|None): If set, only track this marker ID; otherwise pick the largest marker.
        smooth_alpha (float): EMA smoothing factor for distance (0=no smooth, 1=instant).
        draw_axes (bool): Draw pose axes on the frame.
    """
    def __init__(
        self,
        marker_size: float = 0.05,
        camera_matrix: np.ndarray | None = None,
        dist_coeffs: np.ndarray | None = None,
        target_id: int | None = None,
        smooth_alpha: float = 0.35,
        draw_axes: bool = True,
    ):
        self.marker_size = float(marker_size)
        self.target_id = target_id
        self.draw_axes = draw_axes

        # Dictionary & detector params
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.parameters = cv2.aruco.DetectorParameters()  # OpenCV 4.12+
        # Slightly more tolerant/adaptive for varied lighting
        self.parameters.adaptiveThreshWinSizeMin = 5
        self.parameters.adaptiveThreshWinSizeMax = 33
        self.parameters.adaptiveThreshWinSizeStep = 4
        self.parameters.adaptiveThreshConstant = 7
        self.parameters.minCornerDistanceRate = 0.02
        self.parameters.minMarkerDistanceRate = 0.02

        # New API (4.7+). Fall back to legacy if not present.
        self._detector = None
        if hasattr(cv2.aruco, "ArucoDetector"):
            self._detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.parameters)

        # Intrinsics
        if camera_matrix is None:
            # Reasonable default for 720p webcams; works well enough for demo
            self.camera_matrix = np.array(
                [[800.0,   0.0, 320.0],
                 [  0.0, 800.0, 240.0],
                 [  0.0,   0.0,   1.0]], dtype=np.float32
            )
        else:
            self.camera_matrix = np.array(camera_matrix, dtype=np.float32)

        if dist_coeffs is None:
            self.dist_coeffs = np.zeros((5, 1), dtype=np.float32)
        else:
            self.dist_coeffs = np.array(dist_coeffs, dtype=np.float32).reshape(-1, 1)

        # EMA smoothing for distance
        self.alpha = float(np.clip(smooth_alpha, 0.0, 1.0))
        self._ema_distance = None
        self._recent = deque(maxlen=3)  # tiny median filter to kill outliers

    # --- Public utilities -----------------------------------------------------

    def set_marker_size(self, meters: float):
        self.marker_size = float(meters)
        self.reset_filter()

    def set_camera_intrinsics(self, camera_matrix, dist_coeffs=None):
        self.camera_matrix = np.array(camera_matrix, dtype=np.float32)
        if dist_coeffs is not None:
            self.dist_coeffs = np.array(dist_coeffs, dtype=np.float32).reshape(-1, 1)
        self.reset_filter()

    def reset_filter(self):
        self._ema_distance = None
        self._recent.clear()

    # --- Core API -------------------------------------------------------------

    def estimate_distance(self, frame):
        """
        Detects ArUco marker(s) and returns (distance_m, annotated_frame).
        distance_m is smoothed; returns None if no reliable detection.
        """
        if frame is None or frame.size == 0:
            return None, frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect markers (new API first, fallback to legacy)
        if self._detector is not None:
            corners, ids, _rej = self._detector.detectMarkers(gray)
        else:
            corners, ids, _rej = cv2.aruco.detectMarkers(gray, self.aruco_dict, parameters=self.parameters)

        distance = None

        if ids is not None and len(corners) > 0:
            # choose marker: specific ID or the largest perimeter (best pose stability)
            idx = self._select_marker_index(corners, ids)
            if idx is not None:
                sel_corners = [corners[idx]]
                try:
                    rvec, tvec, _obj = cv2.aruco.estimatePoseSingleMarkers(
                        sel_corners, self.marker_size, self.camera_matrix, self.dist_coeffs
                    )
                    # Euclidean distance camera->marker center
                    raw_dist = float(np.linalg.norm(tvec[0][0]))
                    # small median filter to remove spikes
                    self._recent.append(raw_dist)
                    median_dist = float(np.median(self._recent))

                    # EMA smoothing
                    if self.alpha > 0.0:
                        if self._ema_distance is None:
                            self._ema_distance = median_dist
                        else:
                            self._ema_distance = self.alpha * median_dist + (1 - self.alpha) * self._ema_distance
                        distance = float(self._ema_distance)
                    else:
                        distance = median_dist

                    # Draw visuals
                    cv2.aruco.drawDetectedMarkers(frame, sel_corners, ids[idx:idx+1])
                    if self.draw_axes:
                        cv2.drawFrameAxes(frame, self.camera_matrix, self.dist_coeffs, rvec, tvec, self.marker_size * 0.6)

                except cv2.error:
                    # Pose could fail on partial markers; ignore gracefully
                    distance = None

        # HUD text
        if distance is not None:
            cv2.putText(frame, f"Distance: {distance:.2f} m", (20, 36),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "Show ArUco marker (4x4_50)", (20, 36),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 2)

        return distance, frame

    # --- Internals ------------------------------------------------------------

    def _select_marker_index(self, corners, ids):
        """
        Prefer target_id if provided; otherwise pick the marker with the largest perimeter in image space.
        """
        ids = ids.flatten()
        if self.target_id is not None:
            matches = np.where(ids == self.target_id)[0]
            if len(matches) > 0:
                return int(matches[0])

        # Pick by largest perimeter (more pixels -> generally closer & better pose)
        perims = []
        for i, c in enumerate(corners):
            pts = c.reshape(-1, 2)
            perim = (np.linalg.norm(pts[0]-pts[1]) +
                     np.linalg.norm(pts[1]-pts[2]) +
                     np.linalg.norm(pts[2]-pts[3]) +
                     np.linalg.norm(pts[3]-pts[0]))
            perims.append(perim)
        if not perims:
            return None
        return int(np.argmax(perims))
