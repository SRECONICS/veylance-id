import os
import cv2
import numpy as np

from paths import app_root


# YuNet detection rows are Nx15 float32:
#   [x, y, w, h,
#    right_eye_x,  right_eye_y,
#    left_eye_x,   left_eye_y,
#    nose_x,       nose_y,
#    right_mouth_x, right_mouth_y,
#    left_mouth_x,  left_mouth_y,
#    score]
#
# This exact layout is what cv2.FaceRecognizerSF.alignCrop() expects, so we
# keep the raw row around instead of reshaping it into our own structure —
# vision/embeddings.py consumes these rows directly.

MODEL_PATH = os.path.join(
    app_root(), "models", "face_detection_yunet_2023mar.onnx"
)


class FaceDetector:

    def __init__(self, model_path=MODEL_PATH, score_threshold=0.75):

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                "Veylance could not find the YuNet face detection model at "
                f"'{model_path}'. Download face_detection_yunet_2023mar.onnx "
                "from the OpenCV Zoo and place it in the models/ folder."
            )

        self.detector = cv2.FaceDetectorYN_create(
            model_path,
            "",
            (320, 320),
            score_threshold=score_threshold,
            nms_threshold=0.3,
            top_k=10
        )

        self._last_size = (320, 320)

        print("[Veylance] YuNet face detector initialized.")

    def detect(self, frame):
        """Returns an (N, 15) float32 numpy array of raw YuNet detections.
        Returns an empty (0, 15) array when nothing is detected."""

        height, width = frame.shape[:2]

        if (width, height) != self._last_size:
            self.detector.setInputSize((width, height))
            self._last_size = (width, height)

        _, faces = self.detector.detect(frame)

        if faces is None:
            return np.empty((0, 15), dtype=np.float32)

        return faces

    @staticmethod
    def get_bbox(face_row):
        x, y, w, h = face_row[0:4].astype(int)
        return int(x), int(y), int(w), int(h)

    @staticmethod
    def get_score(face_row):
        return float(face_row[14])

    def draw_faces(self, frame, faces, labels=None):

        for i, face_row in enumerate(faces):

            x, y, w, h = self.get_bbox(face_row)
            score = self.get_score(face_row)

            label = "FACE DETECTED"
            if labels is not None and i < len(labels) and labels[i]:
                label = labels[i]

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 120),
                2
            )

            cv2.putText(
                frame,
                f"{label} ({score:.2f})",
                (x, max(y - 12, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 120),
                2
            )

        return frame
