import os
import sys
import time
import ctypes
import cv2

# When packaged with PyInstaller's --windowed flag, there's no console,
# so sys.stdout/stderr are None — and the very first print() anywhere
# (we have plenty of "[Veylance] ..." diagnostic ones) would crash the
# app with AttributeError before a window ever appears. Redirect to a
# no-op sink instead. No-op in normal `python main.py` runs, where
# stdout/stderr are real.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from paths import data_root
from vision.detector import FaceDetector
from vision.embeddings import FaceEmbedder
from vision.recognizer import IdentityStore
from vision.liveness import LivenessChecker
from vision.presence import PresenceMonitor
from vision.quality import assess_quality
from vision.pose import classify_pose
from database.database import Database
from ui.enrollment import EnrollmentPage
from ui.identities import IdentitiesPage
from ui.history import HistoryPage
from ui.settings import SettingsPage
from ui.pin_dialog import PinEntryDialog, PinSetupDialog
from PySide6.QtGui import QImage, QPixmap, QDesktopServices, QIcon, QPainter, QColor
from PySide6.QtCore import Qt, QTimer, QUrl, QEvent
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedWidget,
    QProgressBar,
    QSystemTrayIcon,
    QMenu,
    QMessageBox
)


# Which head pose each of the 10 enrollment samples requires, in order.
# 4 centered + 3 to each side gives the averaged embedding some genuine
# pose variety instead of 10 near-identical frontal shots.
ENROLLMENT_POSE_PLAN = (
    ["center"] * 4 +
    ["left"] * 3 +
    ["right"] * 3
)

ENROLLMENT_POSE_PROMPTS = {
    "center": "Look straight at the camera",
    "left": "Turn your head to one side",
    "right": "Turn your head to the other side",
}


class VeylanceApp(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Veylance ID")
        self.resize(1200, 750)

        # ================= MAIN WINDOW =================

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ================= SIDEBAR =================

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(25, 35, 25, 25)
        sidebar_layout.setSpacing(15)

        logo = QLabel("VEYLANCE ID")
        logo.setObjectName("logo")

        subtitle = QLabel("LOCAL AI SECURITY")
        subtitle.setObjectName("subtitle")

        sidebar_layout.addWidget(logo)
        sidebar_layout.addWidget(subtitle)
        sidebar_layout.addSpacing(35)

        dashboard_button = QPushButton("⌂   Dashboard")
        enroll_button = QPushButton("＋   Enroll Identity")
        identities_button = QPushButton("☰   Enrolled Identities")
        history_button = QPushButton("◷   Authentication History")
        settings_button = QPushButton("⚙   Settings")

        buttons = [
            dashboard_button,
            enroll_button,
            identities_button,
            history_button,
            settings_button
        ]

        for button in buttons:
            button.setObjectName("navButton")
            button.setCursor(Qt.PointingHandCursor)
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()

        version = QLabel("Veylance ID\nVersion 1.0")
        version.setObjectName("version")

        sidebar_layout.addWidget(version)

        # ================= DASHBOARD =================

        dashboard = QWidget()

        dashboard_layout = QVBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(45, 40, 45, 40)
        dashboard_layout.setSpacing(25)

        title = QLabel("Security Dashboard")
        title.setObjectName("title")

        description = QLabel(
            "Local AI-powered identity verification and presence security"
        )
        description.setObjectName("description")

        dashboard_layout.addWidget(title)
        dashboard_layout.addWidget(description)

        # ================= STATUS CARD =================

        status_card = QFrame()
        status_card.setObjectName("card")

        status_layout = QHBoxLayout(status_card)
        status_layout.setContentsMargins(25, 20, 25, 20)

        status_text = QVBoxLayout()

        protection_title = QLabel("SYSTEM PROTECTION")
        protection_title.setObjectName("cardLabel")

        protection_status = QLabel("●  Protection Active")
        protection_status.setObjectName("activeStatus")

        status_text.addWidget(protection_title)
        status_text.addWidget(protection_status)

        status_layout.addLayout(status_text)
        status_layout.addStretch()

        # Keep reference so we can update it later
        self.camera_status = QLabel("CAMERA STARTING...")
        self.camera_status.setObjectName("cameraStatus")

        status_layout.addWidget(self.camera_status)

        dashboard_layout.addWidget(status_card)

        # ================= CAMERA CARD =================

        camera_card = QFrame()
        camera_card.setObjectName("cameraCard")

        camera_layout = QVBoxLayout(camera_card)
        camera_layout.setContentsMargins(20, 15, 20, 20)
        camera_layout.setSpacing(10)

        camera_title = QLabel("LIVE IDENTITY MONITOR")
        camera_title.setObjectName("cameraTitle")
        camera_title.setAlignment(Qt.AlignCenter)

        self.camera_view = QLabel("Starting camera...")

        self.camera_view.setAlignment(Qt.AlignCenter)
        self.camera_view.setMinimumSize(640, 360)
        self.camera_view.setObjectName("cameraView")

        camera_layout.addWidget(camera_title)
        camera_layout.addWidget(self.camera_view, 1)

        dashboard_layout.addWidget(camera_card, 1)

        # ================= SIMILARITY METER =================

        similarity_card = QFrame()
        similarity_card.setObjectName("similarityCard")

        similarity_layout = QHBoxLayout(similarity_card)
        similarity_layout.setContentsMargins(20, 14, 20, 14)
        similarity_layout.setSpacing(14)

        similarity_title = QLabel("MATCH CONFIDENCE")
        similarity_title.setObjectName("cardLabel")

        self.similarity_bar = QProgressBar()
        self.similarity_bar.setRange(0, 100)
        self.similarity_bar.setValue(0)
        self.similarity_bar.setTextVisible(False)
        self.similarity_bar.setFixedHeight(10)
        self.similarity_bar.setObjectName("similarityBar")

        self.similarity_value_label = QLabel("No signal")
        self.similarity_value_label.setObjectName("similarityValue")
        self.similarity_value_label.setFixedWidth(160)
        self.similarity_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        similarity_layout.addWidget(similarity_title)
        similarity_layout.addWidget(self.similarity_bar, 1)
        similarity_layout.addWidget(self.similarity_value_label)

        dashboard_layout.addWidget(similarity_card)

        # ================= BOTTOM STATUS =================

        self.identity_status = QLabel(
            "IDENTITY     Waiting for face...        "
            "LIVENESS     Waiting        "
            "AUTHENTICATION     Standby"
        )

        self.identity_status.setObjectName("bottomStatus")
        self.identity_status.setWordWrap(True)
        self.identity_status.setMinimumHeight(50)

        dashboard_layout.addWidget(self.identity_status)

        # ================= APPLICATION PAGES =================

        self.pages = QStackedWidget()

        self.enrollment_page = EnrollmentPage()
        self.identities_page = IdentitiesPage()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage()

        # Page 0 = Dashboard
        self.pages.addWidget(dashboard)

        # Page 1 = Enrollment
        self.pages.addWidget(self.enrollment_page)

        # Page 2 = Enrolled Identities
        self.pages.addWidget(self.identities_page)

        # Page 3 = Authentication History
        self.pages.addWidget(self.history_page)

        # Page 4 = Settings
        self.pages.addWidget(self.settings_page)

        # Add sidebar + page container
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages, 1)


        # ================= NAVIGATION =================

        dashboard_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(0)
        )

        enroll_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(1)
        )

        identities_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(2)
        )

        history_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(3)
        )

        settings_button.clicked.connect(
            lambda: self.pages.setCurrentIndex(4)
        )

        self.history_page.refresh_button.clicked.connect(self.refresh_history)
        self.history_page.view_snapshot_requested.connect(self.view_snapshot)

        self.identities_page.refresh_button.clicked.connect(self.refresh_identities)
        self.identities_page.delete_requested.connect(self.confirm_delete_identity)

        self.settings_page.face_recognition_toggled.connect(
            lambda value: self.update_setting("face_recognition_enabled", value)
        )
        self.settings_page.liveness_toggled.connect(
            lambda value: self.update_setting("liveness_enabled", value)
        )
        self.settings_page.unknown_face_toggled.connect(
            lambda value: self.update_setting("unknown_face_detection", value)
        )
        self.settings_page.threshold_changed.connect(
            self.update_similarity_threshold
        )
        self.settings_page.walk_away_toggled.connect(
            lambda value: self.update_setting("walk_away_lock", value)
        )
        self.settings_page.absence_timeout_changed.connect(
            lambda value: self.update_setting("absence_timeout", value)
        )

        self.settings_page.manage_pin_requested.connect(self.manage_pin)

        self.pages.currentChanged.connect(self.on_page_changed)

        self.enrollment_page.enroll_button.clicked.connect(
            self.toggle_enrollment
        )

        # ================= STYLE =================
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b0f14;
            }

            QWidget {
                background-color: #0b0f14;
                color: #e8edf2;
                font-family: "Segoe UI";
            }

            #sidebar {
                background-color: #111820;
                border-right: 1px solid #26313c;
            }

            #logo {
                font-size: 24px;
                font-weight: 700;
                color: #ffffff;
            }

            #subtitle {
                font-size: 10px;
                font-weight: 600;
                color: #6f8294;
                letter-spacing: 2px;
            }

            #navButton {
                background-color: transparent;
                border: none;
                border-radius: 8px;
                color: #9eacb8;
                text-align: left;
                padding: 13px 15px;
                font-size: 13px;
            }

            #navButton:hover {
                background-color: #18232d;
                color: white;
            }

            #version {
                color: #566674;
                font-size: 11px;
            }

            #title {
                font-size: 28px;
                font-weight: 600;
                color: white;
            }

            #description {
                color: #788a99;
                font-size: 13px;
            }

            #card {
                background-color: #111820;
                border: 1px solid #26313c;
                border-radius: 12px;
            }

            #cardLabel {
                color: #718291;
                font-size: 10px;
                font-weight: 600;
            }

            #activeStatus {
                color: #55d68b;
                font-size: 16px;
                font-weight: 600;
            }

            #cameraStatus {
                color: #55d68b;
                font-size: 11px;
                font-weight: 600;
            }

            #cameraCard {
                background-color: #10171e;
                border: 1px solid #26313c;
                border-radius: 12px;
            }

            #cameraTitle {
                color: #7f909e;
                font-size: 11px;
                font-weight: 600;
            }

            #cameraView {
                background-color: #070b0f;
                border-radius: 8px;
                color: #52616d;
                font-size: 15px;
            }

            #similarityCard {
                background-color: #111820;
                border: 1px solid #26313c;
                border-radius: 12px;
            }

            #similarityBar {
                background-color: #1a232c;
                border: none;
                border-radius: 5px;
            }

            #similarityBar::chunk {
                background-color: #55d68b;
                border-radius: 5px;
            }

            #similarityValue {
                color: #9eacb8;
                font-size: 12px;
                font-weight: 600;
            }

            #bottomStatus {
                background-color: #111820;
                border: 1px solid #26313c;
                border-radius: 8px;
                padding: 15px;
                color: #8797a4;
                font-size: 11px;
            }
        """)
        
        # ================= FACE DETECTION / RECOGNITION =================
        # Both models live in models/ and are downloaded separately (they're
        # binary ONNX files, not something we generate) — see setup notes.
        # We fail soft: if a model is missing, Veylance still runs, just
        # without that capability, instead of crashing on launch.

        try:
            self.face_detector = FaceDetector()
        except FileNotFoundError as e:
            self.face_detector = None
            print(f"[Veylance] {e}")

        try:
            self.embedder = FaceEmbedder()
        except FileNotFoundError as e:
            self.embedder = None
            print(f"[Veylance] {e}")

        self.db = Database()
        self.identity_store = IdentityStore(db=self.db)

        # ================= SETTINGS =================

        self.settings = {
            "face_recognition_enabled": self.db.get_setting("face_recognition_enabled", True),
            "liveness_enabled": self.db.get_setting("liveness_enabled", True),
            "unknown_face_detection": self.db.get_setting("unknown_face_detection", True),
            "similarity_threshold": self.db.get_setting("similarity_threshold", 0.363),
            "walk_away_lock": self.db.get_setting("walk_away_lock", True),
            "absence_timeout": self.db.get_setting("absence_timeout", 10),
        }

        self.identity_store.threshold = self.settings["similarity_threshold"]
        self.settings_page.load_values(self.settings)
        self.settings_page.set_pin_status(self.db.has_pin())

        # ================= PRESENCE / WALK-AWAY LOCK =================

        self.presence = PresenceMonitor(timeout=self.settings["absence_timeout"])

        # ================= LIVENESS STATE =================

        self.liveness = LivenessChecker()
        self.liveness_name = None  # which enrolled identity the active challenge belongs to

        # Edge-triggered auth logging: only write a row when the outcome
        # actually changes, not every frame at ~30fps.
        self.last_auth_event = None

        # ================= ENROLLMENT STATE =================

        self.enrolling = False
        self.enroll_name = ""
        self.enroll_count = 0
        self.enroll_target = 10
        self.enroll_embeddings = []
        self.last_capture_time = 0.0
        self.capture_interval = 0.6  # seconds between accepted samples
        self.samples_dir = os.path.join(data_root(), "faces")
        self.snapshots_dir = os.path.join(data_root(), "snapshots")

        # Latest frame seen by the camera loop, kept around so any code
        # path (even outside update_dashboard) can grab a snapshot.
        self.last_raw_frame = None

        # ================= CAMERA INITIALIZATION =================

        self.camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)

        if self.camera.isOpened():

            self.camera_status.setText("CAMERA CONNECTED  ●")

            # Request HD resolution
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        else:

            self.camera_status.setText("CAMERA UNAVAILABLE  ●")
            self.camera_view.setText("Unable to access camera")

        # Timer controls how often we fetch a frame
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_camera)

        if self.camera.isOpened():
            self.timer.start(30)

        # ================= SYSTEM TRAY =================

        self._force_quit = False
        self._tray_notice_shown = False
        self.tray_icon = None

        if QSystemTrayIcon.isSystemTrayAvailable():
            self._setup_tray()
        else:
            print(
                "[Veylance] System tray not available on this system — "
                "closing the window will exit normally."
            )

    # ============================================================
    # SYSTEM TRAY
    # ============================================================

    def _build_tray_icon(self):

        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#0b0f14"))
        painter.setPen(QColor("#55d68b"))
        painter.drawEllipse(1, 1, 30, 30)

        font = painter.font()
        font.setBold(True)
        font.setPointSize(14)
        painter.setFont(font)
        painter.setPen(QColor("#55d68b"))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "V")
        painter.end()

        return QIcon(pixmap)

    def _setup_tray(self):

        self.tray_icon = QSystemTrayIcon(self._build_tray_icon(), self)
        self.tray_icon.setToolTip("Veylance ID — protection active")

        tray_menu = QMenu()

        open_action = tray_menu.addAction("Open Veylance ID")
        open_action.triggered.connect(self._restore_from_tray)

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("Quit Veylance ID")
        quit_action.triggered.connect(self._quit_from_tray)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_from_tray(self):
        self._force_quit = True
        self.close()

    def _notify_still_running(self):

        if self.tray_icon is None or self._tray_notice_shown:
            return

        self.tray_icon.showMessage(
            "Veylance ID is still running",
            "Protection continues in the background — detection and "
            "walk-away lock stay active. Right-click the tray icon to quit.",
            QSystemTrayIcon.Information,
            4000
        )
        self._tray_notice_shown = True

    def changeEvent(self, event):

        if (
            event.type() == QEvent.WindowStateChange
            and self.isMinimized()
            and self.tray_icon is not None
        ):
            event.ignore()
            self.hide()
            self._notify_still_running()
            return

        super().changeEvent(event)

    # ============================================================
    # CAMERA FRAME UPDATE
    # ============================================================

    def update_camera(self):

        ret, frame = self.camera.read()

        if not ret:
            self.camera_status.setText("CAMERA ERROR  ●")
            return

        # Keep an unmodified copy for alignment/crops
        # (draw_faces below burns a box + label into the display frame)
        raw_frame = frame.copy()
        self.last_raw_frame = raw_frame  # available for snapshots from anywhere

        # ================= FACE DETECTION =================

        if self.face_detector is not None:
            faces = self.face_detector.detect(frame)
        else:
            faces = []

        current_page = self.pages.currentIndex()

        if current_page == 0:
            self.update_dashboard(raw_frame, frame, faces)

        elif current_page == 1:
            display_frame = frame
            if len(faces) > 0:
                display_frame = self.face_detector.draw_faces(frame, faces)
            self.update_enrollment_page(raw_frame, faces)
            self.render_frame(display_frame, self.enrollment_page.camera_view)

    # ============================================================
    # DASHBOARD — LIVE RECOGNITION
    # ============================================================

    def update_dashboard(self, raw_frame, frame, faces):

        if self.face_detector is None:
            self.presence.reset()
            self.update_similarity_meter(None)
            self.identity_status.setText(
                "IDENTITY     Detection models missing        "
                "LIVENESS     Unavailable        "
                "AUTHENTICATION     Unavailable"
            )
            self.render_frame(frame, self.camera_view)
            return

        if len(faces) == 0:
            self.liveness_name = None
            self.liveness.reset()
            self.last_auth_event = None
            self.update_similarity_meter(None)
            self.identity_status.setText(
                "IDENTITY     Waiting for face...        "
                "LIVENESS     Waiting        "
                "AUTHENTICATION     Standby"
            )
            self.process_presence(None)
            self.render_frame(frame, self.camera_view)
            return

        labels = [None] * len(faces)

        # Only the primary (first) face gets identified — good enough until
        # multi-person handling arrives later in the roadmap.
        primary_row = faces[0]

        # Set inside the branches below whenever this frame's outcome is a
        # genuine VERIFIED — feeds the walk-away presence monitor.
        verified_this_frame = None

        if not self.settings["face_recognition_enabled"]:
            self.liveness_name = None
            self.liveness.reset()
            self.last_auth_event = None
            self.update_similarity_meter(None)
            labels[0] = "FACE DETECTED"
            self.identity_status.setText(
                f"IDENTITY     Face detected ({len(faces)}) — recognition disabled        "
                "LIVENESS     Disabled        "
                "AUTHENTICATION     Disabled"
            )

        elif self.embedder is not None and self.identity_store.identities:

            embedding = self.embedder.align_and_embed(raw_frame, primary_row)
            name, score = self.identity_store.identify(embedding)
            self.update_similarity_meter(score)

            if name:

                if not self.settings["liveness_enabled"]:

                    # Liveness disabled in Settings — identity match alone
                    # is enough for VERIFIED.
                    self.liveness_name = None
                    self.liveness.reset()

                    labels[0] = f"{name.upper()} VERIFIED"
                    self.identity_status.setText(
                        f"IDENTITY     {name} — VERIFIED ✓ (similarity {score:.2f})        "
                        "LIVENESS     Disabled        "
                        "AUTHENTICATION     VERIFIED ✓"
                    )
                    verified_this_frame = name

                    event_key = f"verified:{name}"
                    if self.last_auth_event != event_key:
                        self.db.log_auth_event(name, score, "disabled", "VERIFIED")
                        self.last_auth_event = event_key

                else:

                    # (Re)start the liveness challenge whenever a *new* identity
                    # session begins — i.e. this name just started matching.
                    if self.liveness_name != name:
                        self.liveness_name = name
                        self.liveness.start(primary_row)
                    else:
                        self.liveness.update(primary_row)
                        if self.liveness.ready_to_retry():
                            self.liveness.start(primary_row)

                    if self.liveness.state == "passed":
                        labels[0] = f"{name.upper()} VERIFIED"
                        self.identity_status.setText(
                            f"IDENTITY     {name} — VERIFIED ✓ (similarity {score:.2f})        "
                            "LIVENESS     Passed ✓        "
                            "AUTHENTICATION     VERIFIED ✓"
                        )
                        verified_this_frame = name

                        event_key = f"verified:{name}"
                        if self.last_auth_event != event_key:
                            self.db.log_auth_event(name, score, "passed", "VERIFIED")
                            self.last_auth_event = event_key

                    elif self.liveness.state == "failed":
                        labels[0] = f"{name.upper()} — LIVENESS FAILED"
                        self.identity_status.setText(
                            f"IDENTITY     {name} — matched (similarity {score:.2f})        "
                            f"LIVENESS     Failed — {self.liveness.message}        "
                            "AUTHENTICATION     DENIED"
                        )

                        event_key = f"denied:{name}"
                        if self.last_auth_event != event_key:
                            snapshot = self.save_snapshot(raw_frame, "DENIED")
                            self.db.log_auth_event(
                                name, score, "failed", "DENIED", snapshot
                            )
                            self.last_auth_event = event_key

                    else:
                        labels[0] = f"{name.upper()} — CHECKING LIVENESS"
                        self.identity_status.setText(
                            f"IDENTITY     {name} — matched (similarity {score:.2f})        "
                            f"LIVENESS     {self.liveness.message}        "
                            "AUTHENTICATION     Awaiting liveness"
                        )

            else:
                self.liveness_name = None
                self.liveness.reset()

                if self.settings["unknown_face_detection"]:

                    labels[0] = "UNKNOWN"
                    self.identity_status.setText(
                        f"IDENTITY     Unknown (best similarity {score:.2f})        "
                        "LIVENESS     Not checked        "
                        "AUTHENTICATION     Denied"
                    )

                    if self.last_auth_event != "unknown":
                        snapshot = self.save_snapshot(raw_frame, "UNKNOWN")
                        self.db.log_auth_event(
                            None, score, "skipped", "UNKNOWN", snapshot
                        )
                        self.last_auth_event = "unknown"

                else:
                    labels[0] = "FACE DETECTED"
                    self.identity_status.setText(
                        "IDENTITY     Face detected — unrecognized "
                        "(flagging disabled)        "
                        "LIVENESS     Not checked        "
                        "AUTHENTICATION     Standby"
                    )
                    self.last_auth_event = None

        elif self.embedder is None:
            self.liveness_name = None
            self.liveness.reset()
            self.last_auth_event = None
            self.update_similarity_meter(None)
            self.identity_status.setText(
                f"IDENTITY     Face detected ({len(faces)}) — recognition model missing        "
                "LIVENESS     Unavailable        "
                "AUTHENTICATION     Unavailable"
            )

        else:
            self.liveness_name = None
            self.liveness.reset()
            self.last_auth_event = None
            self.update_similarity_meter(None)
            self.identity_status.setText(
                f"IDENTITY     Face detected ({len(faces)}) — no enrolled identities yet        "
                "LIVENESS     Waiting        "
                "AUTHENTICATION     Enroll to continue"
            )

        self.process_presence(verified_this_frame)

        display_frame = self.face_detector.draw_faces(frame, faces, labels)
        self.render_frame(display_frame, self.camera_view)

    # ============================================================
    # LIVE SIMILARITY METER
    # ============================================================

    def update_similarity_meter(self, score):
        """score is the raw cosine similarity from identify() for whichever
        face is primary this frame, or None when there's nothing meaningful
        to show (no face, no enrolled identities, recognition disabled...).
        Updates every frame regardless of whether it cleared the threshold,
        so you can see near-misses, not just confirmed matches."""

        if score is None:
            self.similarity_bar.setValue(0)
            self.similarity_bar.setStyleSheet(
                self._similarity_bar_style("#2a3742")
            )
            self.similarity_value_label.setText("No signal")
            return

        threshold = self.settings["similarity_threshold"]
        clamped = max(0.0, min(1.0, score))

        self.similarity_bar.setValue(int(clamped * 100))

        color = "#55d68b" if score >= threshold else "#e0a94c"
        self.similarity_bar.setStyleSheet(self._similarity_bar_style(color))

        self.similarity_value_label.setText(f"{score:.2f}  (need {threshold:.2f})")

    @staticmethod
    def _similarity_bar_style(chunk_color):
        return f"""
            #similarityBar {{
                background-color: #1a232c;
                border: none;
                border-radius: 5px;
            }}
            #similarityBar::chunk {{
                background-color: {chunk_color};
                border-radius: 5px;
            }}
        """

    # ============================================================
    # PRESENCE / WALK-AWAY LOCK
    # ============================================================

    def process_presence(self, verified_name):

        if not self.settings["walk_away_lock"]:
            self.presence.reset()
            return

        should_lock = self.presence.update(verified_name)

        if should_lock:
            self.trigger_walk_away_lock()
            return

        remaining = self.presence.seconds_remaining()
        if remaining is not None:
            current_text = self.identity_status.text()
            self.identity_status.setText(
                f"{current_text}        AUTO-LOCK IN {remaining:.0f}s"
            )

    def trigger_walk_away_lock(self):

        name = self.presence.verified_name
        print(
            f"[Veylance] {name} was absent for {self.presence.timeout}s "
            "— locking Windows."
        )

        self.db.log_auth_event(name, None, "n/a", "AUTO_LOCK")

        try:
            if os.name == "nt":
                ctypes.windll.user32.LockWorkStation()
            else:
                print(
                    "[Veylance] Walk-away lock only calls the Windows "
                    "LockWorkStation API — no-op on this OS."
                )
        except Exception as e:
            print(f"[Veylance] Failed to lock the workstation: {e}")

        self.presence.reset()

    # ============================================================
    # OPENCV -> QT FRAME RENDERING
    # ============================================================

    def render_frame(self, frame, label):

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        height, width, channels = rgb_frame.shape
        bytes_per_line = channels * width

        image = QImage(
            rgb_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888
        )

        pixmap = QPixmap.fromImage(image)

        pixmap = pixmap.scaled(
            label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        label.setPixmap(pixmap)

    # ============================================================
    # ENROLLMENT CAPTURE
    # ============================================================

    def on_page_changed(self, index):

        # Cancel an in-progress enrollment if the user navigates away
        if self.enrolling and index != 1:
            self.stop_enrollment(cancelled=True)

        # Presence/walk-away is only monitored while the Dashboard is the
        # visible page (that's the only page running face detection). Reset
        # on the way out so time spent on other pages never silently counts
        # as "absent" once you come back.
        if index != 0:
            self.presence.reset()

        if index == 2:
            self.refresh_identities()

        if index == 3:
            self.refresh_history()

    def refresh_history(self):
        logs = self.db.get_recent_logs(200)
        self.history_page.set_logs(logs)

    def refresh_identities(self):
        identities = self.db.get_all_users()
        self.identities_page.set_identities(identities)

    def confirm_delete_identity(self, name):

        confirmed = QMessageBox.question(
            self,
            "Delete enrolled identity",
            f"Delete '{name}'? They will no longer be recognized on the "
            "Dashboard. This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if confirmed != QMessageBox.Yes:
            return

        # Deleting a registered face is security-sensitive too — same PIN
        # gate as enrolling a new one, skipped only if no PIN exists yet
        # (shouldn't happen in practice, since enrolling always forces one).
        if self.db.has_pin():
            authorized = PinEntryDialog.prompt(
                self,
                self.db.verify_pin,
                title="Confirm Deletion",
                message=f"Enter the security PIN to delete '{name}'"
            )
            if not authorized:
                return

        self.identity_store.remove(name)

        # Clear any in-flight liveness/presence session tied to this name
        # so nothing keeps referencing an identity that no longer exists.
        if self.liveness_name == name:
            self.liveness_name = None
            self.liveness.reset()

        if self.presence.verified_name == name:
            self.presence.reset()

        self.last_auth_event = None

        self.refresh_identities()

    def view_snapshot(self, path):
        absolute_path = os.path.abspath(path)
        if os.path.exists(absolute_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(absolute_path))

    # ============================================================
    # SETTINGS
    # ============================================================

    def update_setting(self, key, value):
        self.settings[key] = value
        self.db.set_setting(key, value)

        if key == "absence_timeout":
            self.presence.timeout = value

        # A setting change may invalidate whatever liveness/auth/presence
        # session is currently in progress — safest to just reset and let
        # the next frame re-evaluate from scratch.
        self.liveness_name = None
        self.liveness.reset()
        self.last_auth_event = None
        self.presence.reset()

    def update_similarity_threshold(self, threshold):
        self.settings["similarity_threshold"] = threshold
        self.db.set_setting("similarity_threshold", threshold)
        self.identity_store.threshold = threshold

    def _authorize_enrollment(self):
        """Gate for the 'Start Enrollment' click. If no PIN exists yet,
        this is the very first enrollment ever — force one to be set now
        so every enrollment after this one (including this one) is
        PIN-gated. Otherwise, require the existing PIN."""

        if not self.db.has_pin():

            new_pin = PinSetupDialog.prompt(self, require_current=False)

            if not new_pin:
                self.enrollment_page.face_status.setText(
                    "●  Enrollment cancelled — a security PIN is required "
                    "before enrolling anyone"
                )
                return False

            self.db.set_pin(new_pin)
            self.settings_page.set_pin_status(True)
            self.enrollment_page.face_status.setText(
                "●  Security PIN set — starting enrollment"
            )
            return True

        authorized = PinEntryDialog.prompt(
            self,
            self.db.verify_pin,
            title="Enrollment Locked",
            message=(
                "Enter the security PIN to authorize enrolling a new identity"
            )
        )

        if not authorized:
            self.enrollment_page.face_status.setText(
                "●  Enrollment cancelled — incorrect or missing PIN"
            )
            snapshot = self.save_snapshot(self.last_raw_frame, "ENROLL_PIN_DENIED")
            self.db.log_auth_event(
                None, None, "n/a", "ENROLL_PIN_DENIED", snapshot
            )

        return authorized

    def manage_pin(self):

        if self.db.has_pin():
            new_pin = PinSetupDialog.prompt(
                self, require_current=True, verify_current_fn=self.db.verify_pin
            )
        else:
            new_pin = PinSetupDialog.prompt(self, require_current=False)

        if new_pin:
            self.db.set_pin(new_pin)
            self.settings_page.set_pin_status(True)

    def toggle_enrollment(self):

        if self.enrolling:
            self.stop_enrollment(cancelled=True)
            return

        if not self._authorize_enrollment():
            return

        name = self.enrollment_page.name_input.text().strip()

        if not name:
            self.enrollment_page.face_status.setText(
                "●  Enter a name before starting enrollment"
            )
            return

        if not self.camera.isOpened():
            self.enrollment_page.face_status.setText(
                "●  Camera unavailable"
            )
            return

        if self.face_detector is None:
            self.enrollment_page.face_status.setText(
                "●  Face detection model missing — see models/ setup"
            )
            return

        self.enroll_name = name
        self.enroll_count = 0
        self.enroll_embeddings = []
        self.last_capture_time = 0.0

        self.enrollment_page.progress.setValue(0)
        self.enrollment_page.progress_text.setText(
            f"0 / {self.enroll_target}"
        )
        first_prompt = ENROLLMENT_POSE_PROMPTS[ENROLLMENT_POSE_PLAN[0]]
        self.enrollment_page.face_status.setText(
            f"●  Enrolling — {first_prompt}"
        )
        self.enrollment_page.enroll_button.setText("Cancel Enrollment")

        self.enrolling = True

    def stop_enrollment(self, cancelled=False, completed=False):

        self.enrolling = False
        self.enrollment_page.enroll_button.setText("Start Enrollment")

        if completed:

            if self.embedder is not None and self.enroll_embeddings:
                try:
                    self.identity_store.enroll(
                        self.enroll_name, self.enroll_embeddings
                    )
                    self.enrollment_page.face_status.setText(
                        f"●  Enrollment complete — {self.enroll_name} registered "
                        f"({self.enroll_count}/{self.enroll_target} samples)"
                    )
                except ValueError as e:
                    self.enrollment_page.face_status.setText(f"●  {e}")
            else:
                self.enrollment_page.face_status.setText(
                    f"●  Captured {self.enroll_count}/{self.enroll_target} samples, "
                    "but recognition model is missing — identity not registered"
                )

        elif cancelled:
            self.enrollment_page.face_status.setText("●  Enrollment cancelled")

        self.enroll_embeddings = []

    def update_enrollment_page(self, raw_frame, faces):

        if len(faces) == 0:
            if self.enrolling:
                self.enrollment_page.face_status.setText(
                    "●  Face not detected — center your face"
                )
            else:
                self.enrollment_page.face_status.setText("●  Waiting for face")
            return

        if len(faces) > 1:
            self.enrollment_page.face_status.setText(
                "●  Multiple faces detected — only one person allowed"
            )
            return

        if not self.enrolling:
            self.enrollment_page.face_status.setText(
                "●  Face detected — ready to enroll"
            )
            return

        # ---- Enrolling: capture spaced, pose-guided, quality-checked samples ----

        now = time.time()

        if now - self.last_capture_time < self.capture_interval:
            self.enrollment_page.face_status.setText("●  Hold steady...")
            return

        face_row = faces[0]

        required_pose = ENROLLMENT_POSE_PLAN[self.enroll_count]
        current_pose = classify_pose(face_row)

        if current_pose != required_pose:
            prompt = ENROLLMENT_POSE_PROMPTS[required_pose]
            self.enrollment_page.face_status.setText(
                f"●  {prompt} — sample {self.enroll_count + 1}/{self.enroll_target}"
            )
            return

        x, y, w, h = self.face_detector.get_bbox(face_row)
        face_crop = raw_frame[y:y + h, x:x + w]

        if face_crop.size == 0:
            return  # face box clipped off-frame edge; skip this tick

        face_crop = cv2.resize(face_crop, (200, 200))

        ok, reason = assess_quality(face_crop)
        if not ok:
            self.enrollment_page.face_status.setText(
                f"●  Capture rejected ({reason}) — try again"
            )
            return

        if self.embedder is not None:
            embedding = self.embedder.align_and_embed(raw_frame, face_row)
            self.enroll_embeddings.append(embedding)

        self.enroll_count += 1
        self.save_face_sample(face_crop)
        self.last_capture_time = now

        self.enrollment_page.progress.setValue(self.enroll_count)
        self.enrollment_page.progress_text.setText(
            f"{self.enroll_count} / {self.enroll_target}"
        )

        if self.enroll_count < self.enroll_target:
            next_prompt = ENROLLMENT_POSE_PROMPTS[
                ENROLLMENT_POSE_PLAN[self.enroll_count]
            ]
            self.enrollment_page.face_status.setText(
                f"●  Captured {self.enroll_count}/{self.enroll_target} — "
                f"next: {next_prompt}"
            )
        else:
            self.enrollment_page.face_status.setText(
                f"●  Captured {self.enroll_count}/{self.enroll_target}"
            )

        if self.enroll_count >= self.enroll_target:
            self.stop_enrollment(completed=True)

    def save_face_sample(self, face_crop):

        person_dir = os.path.join(self.samples_dir, self.enroll_name)
        os.makedirs(person_dir, exist_ok=True)

        timestamp = int(time.time() * 1000)
        filename = os.path.join(
            person_dir,
            f"{self.enroll_name}_{self.enroll_count}_{timestamp}.jpg"
        )

        cv2.imwrite(filename, face_crop)

    # ============================================================
    # INTRUDER SNAPSHOTS
    # ============================================================

    def save_snapshot(self, frame, result):
        """Saves a full camera frame for a DENIED/UNKNOWN/PIN-denied event.
        Returns the path (relative to the project root, so it stays
        portable) or None if there was no frame to save."""

        if frame is None:
            return None

        os.makedirs(self.snapshots_dir, exist_ok=True)

        timestamp = int(time.time() * 1000)
        filename = f"{result}_{timestamp}.jpg"
        full_path = os.path.join(self.snapshots_dir, filename)

        cv2.imwrite(full_path, frame)

        return full_path


    def closeEvent(self, event):

        # Clicking the window's X shouldn't kill background protection —
        # hide to the tray instead, unless Quit was explicitly chosen from
        # the tray menu (or there's no tray to fall back to at all).
        if self.tray_icon is not None and not self._force_quit:
            event.ignore()
            self.hide()
            self._notify_still_running()
            return

        if hasattr(self, "timer"):
            self.timer.stop()

        if hasattr(self, "camera") and self.camera.isOpened():
            self.camera.release()

        if hasattr(self, "db"):
            self.db.close()

        if self.tray_icon is not None:
            self.tray_icon.hide()

        event.accept()


# ================================================================
# START APPLICATION
# ================================================================

if __name__ == "__main__":

    app = QApplication(sys.argv)

    # Without this, Qt exits the whole app the moment the window is
    # hidden (minimize-to-tray or close-to-tray) since it thinks the
    # "last window" closed — which would silently kill background
    # detection and the walk-away lock. The tray's Quit action is the
    # only real way out now.
    app.setQuitOnLastWindowClosed(False)

    window = VeylanceApp()
    window.show()

    sys.exit(app.exec())