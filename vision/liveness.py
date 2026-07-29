import time
import random


class LivenessChecker:
    """Active liveness challenge built on YuNet's 5-point landmarks.

    This is NOT a deep anti-spoofing model — we don't have eye-contour
    landmarks (YuNet gives one point per eye, not enough for real blink /
    EAR detection), so V1 asks for a head turn instead: track how the nose
    point shifts sideways relative to the eye midpoint, require a clear
    shift away from baseline, then a return to center, within time limits.

    A static printed photo can't do this. A video replay of the enrolled
    person still could — that's a known gap, flagged in the project roadmap
    as something a real anti-spoofing model should close later.
    """

    CHALLENGE_TIMEOUT = 6.0    # seconds allowed to turn away from baseline
    RETURN_TIMEOUT = 4.0       # seconds allowed to return to center after turning
    RETRY_DELAY = 2.5          # seconds to show a failure before auto-retrying

    TURN_THRESHOLD = 0.18      # |yaw shift| counted as "turned away"
    RETURN_THRESHOLD = 0.08    # |yaw shift| counted as "back near center"

    def __init__(self):
        self.reset()

    def reset(self):
        self.active = False
        self.state = "idle"       # idle | awaiting_turn | awaiting_return | passed | failed
        self.baseline_yaw = None
        self.deadline = None
        self.finished_at = None
        self.message = "Waiting to start liveness check"

    @staticmethod
    def yaw_shift(face_row, baseline_yaw):
        """Horizontal offset of the nose from the eye midpoint, normalized
        by inter-eye distance so it's roughly scale-invariant."""

        right_eye_x = face_row[4]
        left_eye_x = face_row[6]
        nose_x = face_row[8]

        eye_mid_x = (right_eye_x + left_eye_x) / 2.0
        eye_distance = abs(left_eye_x - right_eye_x)

        if eye_distance < 1e-3:
            return 0.0

        current_yaw = (nose_x - eye_mid_x) / eye_distance
        return current_yaw - baseline_yaw

    def start(self, face_row):
        right_eye_x = face_row[4]
        left_eye_x = face_row[6]
        nose_x = face_row[8]

        eye_mid_x = (right_eye_x + left_eye_x) / 2.0
        eye_distance = abs(left_eye_x - right_eye_x)

        self.baseline_yaw = 0.0 if eye_distance < 1e-3 else (
            (nose_x - eye_mid_x) / eye_distance
        )

        self.state = "awaiting_turn"
        self.active = True
        self.finished_at = None
        self.deadline = time.time() + self.CHALLENGE_TIMEOUT
        self.message = "Turn your head to either side, then face forward again"

    def update(self, face_row):
        """Call once per frame while this challenge is active and a face
        is visible. Returns the current state string."""

        if not self.active:
            return self.state

        now = time.time()

        if now > self.deadline:
            self.state = "failed"
            self.active = False
            self.finished_at = now
            self.message = "Liveness check timed out — no head movement detected"
            return self.state

        shift = self.yaw_shift(face_row, self.baseline_yaw)

        if self.state == "awaiting_turn":
            if abs(shift) >= self.TURN_THRESHOLD:
                self.state = "awaiting_return"
                self.deadline = now + self.RETURN_TIMEOUT
                self.message = "Good — now face forward again"

        elif self.state == "awaiting_return":
            if abs(shift) <= self.RETURN_THRESHOLD:
                self.state = "passed"
                self.active = False
                self.finished_at = now
                self.message = "Liveness confirmed"

        return self.state

    def ready_to_retry(self):
        return (
            self.state == "failed"
            and self.finished_at is not None
            and time.time() - self.finished_at > self.RETRY_DELAY
        )
