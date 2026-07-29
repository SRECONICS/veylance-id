import os
import cv2
import numpy as np

from paths import app_root


MODEL_PATH = os.path.join(
    app_root(), "models", "face_recognition_sface_2021dec.onnx"
)


class FaceEmbedder:
    """Wraps OpenCV's SFace model: aligns a detected face using YuNet's
    5-point landmarks, then produces a 128-d L2-normalized embedding."""

    def __init__(self, model_path=MODEL_PATH):

        if not os.path.exists(model_path):
            raise FileNotFoundError(
                "Veylance could not find the SFace recognition model at "
                f"'{model_path}'. Download face_recognition_sface_2021dec.onnx "
                "from the OpenCV Zoo and place it in the models/ folder."
            )

        self.recognizer = cv2.FaceRecognizerSF_create(model_path, "")

        print("[Veylance] SFace embedding model initialized.")

    def align(self, frame, face_row):
        """face_row is a raw YuNet detection row (see vision/detector.py)."""
        return self.recognizer.alignCrop(frame, face_row)

    def embed(self, aligned_face):
        """Returns a (1, 128) float32 L2-normalized embedding."""

        feature = self.recognizer.feature(aligned_face)

        norm = np.linalg.norm(feature)
        if norm > 0:
            feature = feature / norm

        return feature

    def align_and_embed(self, frame, face_row):
        aligned = self.align(frame, face_row)
        return self.embed(aligned)

    @staticmethod
    def cosine_similarity(embedding_a, embedding_b):
        """Both embeddings are assumed to already be L2-normalized,
        so cosine similarity reduces to a dot product."""
        return float(np.dot(embedding_a.flatten(), embedding_b.flatten()))
