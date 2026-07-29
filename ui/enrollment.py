from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QProgressBar
)
from PySide6.QtCore import Qt


class EnrollmentPage(QWidget):

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(45, 40, 45, 40)
        main_layout.setSpacing(20)

        # ================= HEADER =================

        title = QLabel("Enroll Identity")
        title.setObjectName("pageTitle")

        description = QLabel(
            "Register a new identity for local biometric verification"
        )
        description.setWordWrap(True)
        description.setObjectName("pageDescription")

        main_layout.addWidget(title)
        main_layout.addWidget(description)

        # ================= FORM CARD =================

        form_card = QFrame()
        form_card.setObjectName("enrollmentCard")

        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(30, 25, 30, 25)
        form_layout.setSpacing(15)

        name_label = QLabel("IDENTITY NAME")
        name_label.setObjectName("fieldLabel")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter name")

        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_input)

        main_layout.addWidget(form_card)

        # ================= CAMERA AREA =================

        camera_card = QFrame()
        camera_card.setObjectName("enrollmentCameraCard")

        camera_layout = QVBoxLayout(camera_card)
        camera_layout.setContentsMargins(20, 20, 20, 20)

        camera_title = QLabel("ENROLLMENT CAMERA")
        camera_title.setObjectName("fieldLabel")
        camera_title.setAlignment(Qt.AlignCenter)

        self.camera_view = QLabel(
            "Camera preview will appear here during enrollment"
        )

        self.camera_view.setAlignment(Qt.AlignCenter)
        self.camera_view.setMinimumHeight(320)
        self.camera_view.setObjectName("enrollmentCamera")

        camera_layout.addWidget(camera_title)
        camera_layout.addWidget(self.camera_view)

        main_layout.addWidget(camera_card, 1)

        # ================= FACE STATUS =================

        self.face_status = QLabel("●  Waiting for face")
        self.face_status.setObjectName("faceStatus")
        self.face_status.setWordWrap(True)
        self.face_status.setMinimumHeight(36)

        main_layout.addWidget(self.face_status)

        # ================= PROGRESS =================

        progress_layout = QHBoxLayout()

        progress_label = QLabel("Capture progress")
        progress_label.setObjectName("fieldLabel")

        self.progress_text = QLabel("0 / 10")
        self.progress_text.setObjectName("progressText")

        progress_layout.addWidget(progress_label)
        progress_layout.addStretch()
        progress_layout.addWidget(self.progress_text)

        main_layout.addLayout(progress_layout)

        self.progress = QProgressBar()
        self.progress.setRange(0, 10)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)

        main_layout.addWidget(self.progress)

        # ================= BUTTON =================

        self.enroll_button = QPushButton("Start Enrollment")
        self.enroll_button.setObjectName("enrollButton")
        self.enroll_button.setCursor(Qt.PointingHandCursor)
        self.enroll_button.setMinimumHeight(45)

        main_layout.addWidget(self.enroll_button)

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

            #enrollmentCard,
            #enrollmentCameraCard {
                background-color: #111820;
                border: 1px solid #26313c;
                border-radius: 12px;
            }

            #fieldLabel {
                color: #7f909e;
                font-size: 11px;
                font-weight: 600;
            }

            QLineEdit {
                background-color: #090e13;
                border: 1px solid #2a3742;
                border-radius: 7px;
                padding: 12px;
                color: white;
                font-size: 14px;
            }

            QLineEdit:focus {
                border: 1px solid #55d68b;
            }

            #enrollmentCamera {
                background-color: #070b0f;
                border-radius: 8px;
                color: #52616d;
                font-size: 14px;
            }

            #faceStatus {
                color: #7f909e;
                font-size: 12px;
            }

            #progressText {
                color: #55d68b;
                font-weight: 600;
            }

            QProgressBar {
                background-color: #111820;
                border: 1px solid #26313c;
                border-radius: 5px;
                height: 8px;
            }

            QProgressBar::chunk {
                background-color: #55d68b;
                border-radius: 4px;
            }

            #enrollButton {
                background-color: #55d68b;
                color: #07110b;
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
            }

            #enrollButton:hover {
                background-color: #68e39a;
            }
        """)