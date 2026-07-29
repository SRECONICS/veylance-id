import os

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor


RESULT_COLORS = {
    "VERIFIED": QColor("#55d68b"),
    "DENIED": QColor("#e2596b"),
    "UNKNOWN": QColor("#e0a94c"),
    "ENROLL_PIN_DENIED": QColor("#e2596b"),
    "AUTO_LOCK": QColor("#7f909e"),
}


class HistoryPage(QWidget):

    # Emitted with the snapshot's file path when "View" is clicked —
    # main.py owns opening it (keeps filesystem/OS concerns out of the UI).
    view_snapshot_requested = Signal(str)

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(45, 40, 45, 40)
        main_layout.setSpacing(20)

        # ================= HEADER =================

        header_layout = QHBoxLayout()

        title = QLabel("Authentication History")
        title.setObjectName("pageTitle")

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.setCursor(Qt.PointingHandCursor)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)

        main_layout.addLayout(header_layout)

        description = QLabel(
            "Local record of every identity match, liveness check, and denial"
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)

        main_layout.addWidget(description)

        # ================= TABLE CARD =================

        table_card = QFrame()
        table_card.setObjectName("historyCard")

        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(15, 15, 15, 15)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Timestamp", "Identity", "Result", "Similarity", "Liveness", "Snapshot"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)

        table_layout.addWidget(self.table)

        main_layout.addWidget(table_card, 1)

        self.empty_label = QLabel(
            "No authentication events recorded yet — "
            "they'll show up here once the Dashboard sees a face"
        )
        self.empty_label.setObjectName("emptyLabel")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.hide()

        main_layout.addWidget(self.empty_label)

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

            #snapshotButton {
                background-color: transparent;
                color: #55d68b;
                border: 1px solid #2e4a3a;
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }

            #snapshotButton:hover {
                background-color: #14251c;
            }

            #historyCard {
                background-color: #111820;
                border: 1px solid #26313c;
                border-radius: 12px;
            }

            #emptyLabel {
                color: #566674;
                font-size: 13px;
                padding: 20px;
            }

            QTableWidget {
                background-color: transparent;
                border: none;
                color: #d5dde3;
                font-size: 12px;
                gridline-color: #26313c;
            }

            QTableWidget::item {
                padding: 8px 6px;
            }

            QTableWidget::item:alternate {
                background-color: #0d131a;
            }

            QTableWidget::item:selected {
                background-color: #1c2836;
                color: white;
            }

            QHeaderView::section {
                background-color: #0d131a;
                color: #7f909e;
                font-size: 11px;
                font-weight: 600;
                padding: 8px 6px;
                border: none;
                border-bottom: 1px solid #26313c;
            }
        """)

    def set_logs(self, logs):

        if not logs:
            self.table.setRowCount(0)
            self.table.hide()
            self.empty_label.show()
            return

        self.empty_label.hide()
        self.table.show()

        self.table.setRowCount(len(logs))

        for row_index, entry in enumerate(logs):

            name = entry.get("user_name") or "Unknown"
            result = entry.get("result", "")
            similarity = entry.get("similarity")
            similarity_text = f"{similarity:.2f}" if similarity is not None else "—"
            liveness = entry.get("liveness_result") or "—"
            timestamp = entry.get("timestamp", "")
            snapshot_path = entry.get("snapshot_path")

            values = [timestamp, name, result, similarity_text, liveness]

            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

                if col == 2 and result in RESULT_COLORS:
                    item.setForeground(RESULT_COLORS[result])

                self.table.setItem(row_index, col, item)

            if snapshot_path and os.path.exists(snapshot_path):
                view_button = QPushButton("View")
                view_button.setObjectName("snapshotButton")
                view_button.setCursor(Qt.PointingHandCursor)
                view_button.clicked.connect(
                    lambda checked=False, path=snapshot_path:
                        self.view_snapshot_requested.emit(path)
                )
                self.table.setCellWidget(row_index, 5, view_button)
            else:
                placeholder = QTableWidgetItem("—")
                placeholder.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                placeholder.setForeground(QColor("#3d4b57"))
                self.table.setItem(row_index, 5, placeholder)
