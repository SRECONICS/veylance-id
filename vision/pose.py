# Rough head-pose bucketing for enrollment variety — deliberately NOT the
# same object as vision/liveness.py's LivenessChecker (which measures a
# *shift from a per-session baseline*). This measures an absolute-ish
# ratio instead, since enrollment needs "center vs. turned" classification
# before any baseline exists yet.
#
# The left/right labels are directional but not guaranteed to match your
# physical left/right — camera mirroring varies. That's fine here: all we
# need is two genuinely different poses for capture variety, not a
# correctly-signed compass.

CENTER_MAX_YAW = 0.08
TURN_MIN_YAW = 0.12


def yaw_ratio(face_row):
    """face_row is a raw YuNet detection row (see vision/detector.py)."""

    right_eye_x = face_row[4]
    left_eye_x = face_row[6]
    nose_x = face_row[8]

    eye_mid_x = (right_eye_x + left_eye_x) / 2.0
    eye_distance = abs(left_eye_x - right_eye_x)

    if eye_distance < 1e-3:
        return 0.0

    return (nose_x - eye_mid_x) / eye_distance


def classify_pose(face_row):
    """Returns 'center', 'left', 'right', or 'transition' (clearly neither
    centered nor turned far enough — the dead zone between thresholds)."""

    yaw = yaw_ratio(face_row)

    if yaw <= -TURN_MIN_YAW:
        return "left"
    if yaw >= TURN_MIN_YAW:
        return "right"
    if abs(yaw) <= CENTER_MAX_YAW:
        return "center"

    return "transition"
