import time


class PresenceMonitor:
    """Tracks whether a verified user is still in frame and, once they
    disappear, how long they've been gone. Feed it one call per Dashboard
    frame with either the currently-VERIFIED name or None.

    Deliberately dumb: it doesn't do its own face detection or timing
    beyond wall-clock elapsed time. Note that main.py only calls update()
    while the Dashboard page is actually being rendered — see the
    on_page_changed() reset — so navigating to Settings/History/Enrollment
    doesn't silently burn down the absence timer in the background.
    """

    def __init__(self, timeout=10):
        self.timeout = timeout
        self.reset()

    def reset(self):
        self.present = False
        self.verified_name = None
        self.absent_since = None
        self.locked_for_session = False

    def update(self, verified_name):
        """Returns True exactly once, the frame the absence timeout is
        crossed for a session that was previously verified."""

        now = time.time()

        if verified_name is not None:
            self.verified_name = verified_name
            self.present = True
            self.absent_since = None
            self.locked_for_session = False
            return False

        if not self.present:
            return False  # no active verified session to monitor

        if self.absent_since is None:
            self.absent_since = now
            return False

        if self.locked_for_session:
            return False

        if now - self.absent_since >= self.timeout:
            self.locked_for_session = True
            return True

        return False

    def seconds_remaining(self):
        if self.absent_since is None:
            return None
        return max(0.0, self.timeout - (time.time() - self.absent_since))
