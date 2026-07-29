import cv2
import numpy as np


# Starting heuristics, not measured against this laptop's camera/lighting —
# loosen or tighten these if enrollment keeps rejecting good frames or
# waving through bad ones. Same spirit as the similarity threshold in
# recognizer.py: a reasonable guess we expect to calibrate from real use.
BLUR_VARIANCE_THRESHOLD = 35.0  # Laplacian variance below this looks blurry
MIN_BRIGHTNESS = 50             # mean pixel intensity below this is too dark
MAX_BRIGHTNESS = 205            # mean pixel intensity above this is blown out


def assess_quality(face_crop):
    """Returns (ok, reason). face_crop is a BGR image of any size.
    reason is None when ok is True, otherwise a short human-readable
    string suitable for showing directly in the enrollment status label."""

    if face_crop is None or face_crop.size == 0:
        return False, "no face"

    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)

    brightness = float(np.mean(gray))
    if brightness < MIN_BRIGHTNESS:
        return False, "too dark"
    if brightness > MAX_BRIGHTNESS:
        return False, "too bright"

    blur_variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    if blur_variance < BLUR_VARIANCE_THRESHOLD:
        return False, "too blurry — hold still"

    return True, None
