from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton
)
from PySide6.QtCore import Qt


DIALOG_STYLE = """
    QDialog {
        background-color: #0b0f14;
    }

    QLabel {
        color: #d5dde3;
        font-size: 13px;
    }

    QLineEdit {
        background-color: #090e13;
        border: 1px solid #2a3742;
        border-radius: 7px;
        padding: 10px;
        color: white;
        font-size: 14px;
    }

    QLineEdit:focus {
        border: 1px solid #55d68b;
    }

    QPushButton {
        border-radius: 7px;
        padding: 9px 18px;
        font-size: 12px;
        font-weight: 700;
    }

    #primaryButton {
        background-color: #55d68b;
        color: #07110b;
        border: none;
    }

    #primaryButton:hover {
        background-color: #68e39a;
    }

    #cancelButton {
        background-color: transparent;
        color: #9eacb8;
        border: 1px solid #2a3742;
    }

    #cancelButton:hover {
        background-color: #18232d;
    }
"""


class PinEntryDialog(QDialog):
    """Prompts for an existing PIN and verifies it via verify_fn.
    Allows a few retries in the same dialog before giving up."""

    MAX_ATTEMPTS = 5

    def __init__(self, parent, verify_fn, title, message):
        super().__init__(parent)

        self.verify_fn = verify_fn
        self.attempts = 0

        self.setWindowTitle(title)
        self.setFixedWidth(360)
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(14)

        label = QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)

        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.Password)
        self.input.setPlaceholderText("PIN")
        self.input.returnPressed.connect(self._on_submit)
        layout.addWidget(self.input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e2596b; font-size: 11px;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        button_row = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("cancelButton")
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.clicked.connect(self.reject)

        submit_button = QPushButton("Unlock")
        submit_button.setObjectName("primaryButton")
        submit_button.setCursor(Qt.PointingHandCursor)
        submit_button.setDefault(True)
        submit_button.clicked.connect(self._on_submit)

        button_row.addWidget(cancel_button)
        button_row.addStretch()
        button_row.addWidget(submit_button)

        layout.addLayout(button_row)

        self.input.setFocus()

    def _on_submit(self):

        pin = self.input.text().strip()

        if pin and self.verify_fn(pin):
            self.accept()
            return

        self.attempts += 1
        remaining = self.MAX_ATTEMPTS - self.attempts

        if remaining <= 0:
            self.error_label.setText("Too many incorrect attempts.")
            self.reject()
            return

        self.error_label.setText(f"Incorrect PIN — {remaining} attempt(s) left")
        self.input.clear()
        self.input.setFocus()

    @staticmethod
    def prompt(parent, verify_fn, title="Enter Security PIN", message="Enter the security PIN to continue"):
        dialog = PinEntryDialog(parent, verify_fn, title, message)
        return dialog.exec() == QDialog.Accepted


class PinSetupDialog(QDialog):
    """Creates or changes the enrollment PIN. If require_current is True,
    the user must first prove they know the existing PIN via
    verify_current_fn before a new one can be set."""

    MIN_LENGTH = 4

    def __init__(self, parent, require_current=False, verify_current_fn=None):
        super().__init__(parent)

        self.require_current = require_current
        self.verify_current_fn = verify_current_fn
        self.new_pin = None

        self.setWindowTitle("Set Security PIN")
        self.setFixedWidth(360)
        self.setModal(True)
        self.setStyleSheet(DIALOG_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        intro = QLabel(
            "This PIN will be required every time someone starts enrolling "
            "a new identity — keep it private."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.current_input = None
        if require_current:
            self.current_input = QLineEdit()
            self.current_input.setEchoMode(QLineEdit.Password)
            self.current_input.setPlaceholderText("Current PIN")
            layout.addWidget(self.current_input)

        self.new_input = QLineEdit()
        self.new_input.setEchoMode(QLineEdit.Password)
        self.new_input.setPlaceholderText(f"New PIN (min {self.MIN_LENGTH} digits)")
        layout.addWidget(self.new_input)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Confirm new PIN")
        self.confirm_input.returnPressed.connect(self._on_submit)
        layout.addWidget(self.confirm_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #e2596b; font-size: 11px;")
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        button_row = QHBoxLayout()

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("cancelButton")
        cancel_button.setCursor(Qt.PointingHandCursor)
        cancel_button.clicked.connect(self.reject)

        submit_button = QPushButton("Save PIN")
        submit_button.setObjectName("primaryButton")
        submit_button.setCursor(Qt.PointingHandCursor)
        submit_button.setDefault(True)
        submit_button.clicked.connect(self._on_submit)

        button_row.addWidget(cancel_button)
        button_row.addStretch()
        button_row.addWidget(submit_button)

        layout.addLayout(button_row)

        (self.current_input or self.new_input).setFocus()

    def _on_submit(self):

        if self.require_current:
            current = self.current_input.text().strip()
            if not current or not self.verify_current_fn(current):
                self.error_label.setText("Current PIN is incorrect")
                self.current_input.clear()
                self.current_input.setFocus()
                return

        new_pin = self.new_input.text().strip()
        confirm_pin = self.confirm_input.text().strip()

        if len(new_pin) < self.MIN_LENGTH or not new_pin.isdigit():
            self.error_label.setText(
                f"PIN must be at least {self.MIN_LENGTH} digits, numbers only"
            )
            return

        if new_pin != confirm_pin:
            self.error_label.setText("PINs don't match")
            self.confirm_input.clear()
            self.confirm_input.setFocus()
            return

        self.new_pin = new_pin
        self.accept()

    @staticmethod
    def prompt(parent, require_current=False, verify_current_fn=None):
        dialog = PinSetupDialog(
            parent,
            require_current=require_current,
            verify_current_fn=verify_current_fn
        )
        if dialog.exec() == QDialog.Accepted:
            return dialog.new_pin
        return None
