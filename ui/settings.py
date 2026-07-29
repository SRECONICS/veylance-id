from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QSlider,
    QSpinBox,
    QPushButton,
    QFrame
)
from PySide6.QtCore import Qt, Signal


class SettingsPage(QWidget):

    # Emitted whenever the user changes a control — main.py listens and
    # persists to the database + applies the change live.
    face_recognition_toggled = Signal(bool)
    liveness_toggled = Signal(bool)
    unknown_face_toggled = Signal(bool)
    manage_pin_requested = Signal()
    threshold_changed = Signal(float)
    walk_away_toggled = Signal(bool)
    absence_timeout_changed = Signal(int)

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(45, 40, 45, 40)
        main_layout.setSpacing(20)

        title = QLabel("Settings")
        title.setObjectName("pageTitle")

        description = QLabel(
            "Control how Veylance detects, recognizes, and responds to faces"
        )
        description.setObjectName("pageDescription")

        main_layout.addWidget(title)
        main_layout.addWidget(description)

        # ================= SECURITY =================

        security_card = self._make_card("SECURITY")
        security_layout = security_card.layout()

        self.face_recognition_toggle = self._make_toggle_row(
            security_layout,
            "Face Recognition",
            "Match detected faces against enrolled identities"
        )
        self.liveness_toggle = self._make_toggle_row(
            security_layout,
            "Liveness Detection",
            "Require a head-turn challenge before granting VERIFIED"
        )
        self.unknown_toggle = self._make_toggle_row(
            security_layout,
            "Unknown Face Detection",
            "Flag and log faces that don't match any enrolled identity"
        )

        threshold_row = QVBoxLayout()
        threshold_row.setSpacing(6)

        threshold_header = QHBoxLayout()
        threshold_label = QLabel("Recognition Sensitivity")
        threshold_label.setObjectName("rowLabel")
        self.threshold_value_label = QLabel("0.36")
        self.threshold_value_label.setObjectName("thresholdValue")
        threshold_header.addWidget(threshold_label)
        threshold_header.addStretch()
        threshold_header.addWidget(self.threshold_value_label)

        threshold_row.addLayout(threshold_header)

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(20, 60)  # maps to 0.20 - 0.60
        self.threshold_slider.setValue(36)
        threshold_row.addWidget(self.threshold_slider)

        threshold_hint = QLabel(
            "Lower = easier match, more false accepts. "
            "Higher = stricter, more false rejects."
        )
        threshold_hint.setObjectName("rowHint")
        threshold_hint.setWordWrap(True)
        threshold_row.addWidget(threshold_hint)

        security_layout.addLayout(threshold_row)

        main_layout.addWidget(security_card)

        # ================= ENROLLMENT PIN =================

        pin_card = self._make_card("ENROLLMENT PIN")
        pin_layout = pin_card.layout()

        pin_row = QHBoxLayout()

        pin_text_col = QVBoxLayout()
        pin_text_col.setSpacing(2)

        self.pin_status_label = QLabel("Checking...")
        self.pin_status_label.setObjectName("rowLabel")

        pin_hint = QLabel("Required to authorize enrolling any new identity")
        pin_hint.setObjectName("rowHint")
        pin_hint.setWordWrap(True)

        pin_text_col.addWidget(self.pin_status_label)
        pin_text_col.addWidget(pin_hint)

        self.pin_button = QPushButton("Set PIN")
        self.pin_button.setObjectName("refreshButton")
        self.pin_button.setCursor(Qt.PointingHandCursor)
        self.pin_button.clicked.connect(self.manage_pin_requested.emit)

        pin_row.addLayout(pin_text_col, 1)
        pin_row.addWidget(self.pin_button)

        pin_layout.addLayout(pin_row)

        main_layout.addWidget(pin_card)

        # ================= PRESENCE =================

        presence_card = self._make_card("PRESENCE")
        presence_layout = presence_card.layout()

        self.walk_away_toggle = self._make_toggle_row(
            presence_layout,
            "Walk-Away Lock",
            "Lock Windows automatically when the verified user leaves "
            "(coming in a later checkpoint — safe to enable now)"
        )

        timeout_row = QHBoxLayout()
        timeout_label = QLabel("Absence Timeout")
        timeout_label.setObjectName("rowLabel")
        timeout_hint = QLabel("Seconds of absence before locking")
        timeout_hint.setObjectName("rowHint")
        timeout_hint.setWordWrap(True)

        timeout_text = QVBoxLayout()
        timeout_text.setSpacing(2)
        timeout_text.addWidget(timeout_label)
        timeout_text.addWidget(timeout_hint)

        self.absence_timeout_spin = QSpinBox()
        self.absence_timeout_spin.setRange(3, 120)
        self.absence_timeout_spin.setValue(10)
        self.absence_timeout_spin.setSuffix(" sec")
        self.absence_timeout_spin.setFixedWidth(100)

        timeout_row.addLayout(timeout_text)
        timeout_row.addStretch()
        timeout_row.addWidget(self.absence_timeout_spin)

        presence_layout.addLayout(timeout_row)

        main_layout.addWidget(presence_card)

        # ================= CAMERA =================

        camera_card = self._make_card("CAMERA")
        camera_layout = camera_card.layout()

        camera_row = QHBoxLayout()
        camera_label = QLabel("Integrated Camera")
        camera_label.setObjectName("rowLabel")
        camera_status = QLabel("Active")
        camera_status.setObjectName("cameraActiveLabel")
        camera_row.addWidget(camera_label)
        camera_row.addStretch()
        camera_row.addWidget(camera_status)

        camera_layout.addLayout(camera_row)

        camera_hint = QLabel(
            "Camera switching isn't available yet — Veylance uses the "
            "system default camera."
        )
        camera_hint.setObjectName("rowHint")
        camera_hint.setWordWrap(True)
        camera_layout.addWidget(camera_hint)

        main_layout.addWidget(camera_card)

        main_layout.addStretch()

        # ================= STYLE =================

        self.setStyleSheet("""
            #pageTitle {
                font-size: 28px;
                font-weight: 600;
                color: white;
            }

            #pageDescription {
                color: #788a99;
                font-size: 13px;
            }

            #settingsCard {
                background-color: #111820;
                border: 1px solid #26313c;
                border-radius: 12px;
            }

            #cardHeading {
                color: #55d68b;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }

            #rowLabel {
                color: #e8edf2;
                font-size: 13px;
                font-weight: 600;
            }

            #rowHint {
                color: #6f8294;
                font-size: 11px;
            }

            #thresholdValue {
                color: #55d68b;
                font-size: 13px;
                font-weight: 700;
            }

            #cameraActiveLabel {
                color: #55d68b;
                font-size: 12px;
                font-weight: 600;
            }

            QCheckBox {
                spacing: 10px;
                color: #e8edf2;
                font-size: 13px;
                font-weight: 600;
            }

            QCheckBox::indicator {
                width: 38px;
                height: 20px;
                border-radius: 10px;
                background-color: #26313c;
                border: 1px solid #33414d;
            }

            QCheckBox::indicator:checked {
                background-color: #55d68b;
                border: 1px solid #55d68b;
            }

            QSlider::groove:horizontal {
                height: 6px;
                background: #26313c;
                border-radius: 3px;
            }

            QSlider::handle:horizontal {
                background: #55d68b;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }

            QSlider::sub-page:horizontal {
                background: #3a9b66;
                border-radius: 3px;
            }

            QSpinBox {
                background-color: #090e13;
                border: 1px solid #2a3742;
                border-radius: 7px;
                padding: 6px 10px;
                color: white;
                font-size: 13px;
            }

            #refreshButton {
                background-color: #18232d;
                color: #d5dde3;
                border: 1px solid #2a3742;
                border-radius: 7px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
            }

            #refreshButton:hover {
                background-color: #223040;
            }

            #pinStatusActive {
                color: #55d68b;
            }

            #pinStatusInactive {
                color: #e0a94c;
            }
        """)

        # ================= WIRING =================

        self.face_recognition_toggle.stateChanged.connect(
            lambda state: self.face_recognition_toggled.emit(bool(state))
        )
        self.liveness_toggle.stateChanged.connect(
            lambda state: self.liveness_toggled.emit(bool(state))
        )
        self.unknown_toggle.stateChanged.connect(
            lambda state: self.unknown_face_toggled.emit(bool(state))
        )
        self.threshold_slider.valueChanged.connect(self._on_threshold_changed)
        self.walk_away_toggle.stateChanged.connect(
            lambda state: self.walk_away_toggled.emit(bool(state))
        )
        self.absence_timeout_spin.valueChanged.connect(
            self.absence_timeout_changed.emit
        )

    # ================= HELPERS =================

    def _make_card(self, heading_text):

        card = QFrame()
        card.setObjectName("settingsCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(25, 20, 25, 22)
        layout.setSpacing(16)

        heading = QLabel(heading_text)
        heading.setObjectName("cardHeading")
        layout.addWidget(heading)

        return card

    def _make_toggle_row(self, parent_layout, label_text, hint_text):

        row = QHBoxLayout()

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        label = QLabel(label_text)
        label.setObjectName("rowLabel")

        hint = QLabel(hint_text)
        hint.setObjectName("rowHint")
        hint.setWordWrap(True)

        text_col.addWidget(label)
        text_col.addWidget(hint)

        toggle = QCheckBox()
        toggle.setCursor(Qt.PointingHandCursor)
        toggle.setChecked(True)

        row.addLayout(text_col, 1)
        row.addWidget(toggle)

        parent_layout.addLayout(row)

        return toggle

    def _on_threshold_changed(self, raw_value):
        threshold = raw_value / 100.0
        self.threshold_value_label.setText(f"{threshold:.2f}")
        self.threshold_changed.emit(threshold)

    def set_pin_status(self, has_pin):

        if has_pin:
            self.pin_status_label.setText("PIN protection active")
            self.pin_status_label.setObjectName("pinStatusActive")
            self.pin_button.setText("Change PIN")
        else:
            self.pin_status_label.setText("No PIN set — enrollment is open to anyone")
            self.pin_status_label.setObjectName("pinStatusInactive")
            self.pin_button.setText("Set PIN")

        # Force the stylesheet to re-evaluate after changing objectName
        self.pin_status_label.style().unpolish(self.pin_status_label)
        self.pin_status_label.style().polish(self.pin_status_label)

    # ================= LOAD WITHOUT EMITTING =================

    def load_values(self, settings):
        """Set initial control states from saved settings without firing
        the change signals (which would otherwise re-save on startup)."""

        controls = [
            (self.face_recognition_toggle, "face_recognition_enabled"),
            (self.liveness_toggle, "liveness_enabled"),
            (self.unknown_toggle, "unknown_face_detection"),
            (self.walk_away_toggle, "walk_away_lock"),
        ]

        for checkbox, key in controls:
            checkbox.blockSignals(True)
            checkbox.setChecked(bool(settings.get(key, True)))
            checkbox.blockSignals(False)

        threshold = settings.get("similarity_threshold", 0.363)
        self.threshold_slider.blockSignals(True)
        self.threshold_slider.setValue(round(threshold * 100))
        self.threshold_value_label.setText(f"{threshold:.2f}")
        self.threshold_slider.blockSignals(False)

        self.absence_timeout_spin.blockSignals(True)
        self.absence_timeout_spin.setValue(settings.get("absence_timeout", 10))
        self.absence_timeout_spin.blockSignals(False)
