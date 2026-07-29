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


class IdentitiesPage(QWidget):

    # Emitted with the identity's name when its Delete button is clicked —
    # main.py owns confirmation + PIN check + the actual database delete.
    delete_requested = Signal(str)

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(45, 40, 45, 40)
        main_layout.setSpacing(20)

        # ================= HEADER =================

        header_layout = QHBoxLayout()

        title = QLabel("Enrolled Identities")
        title.setObjectName("pageTitle")

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.setCursor(Qt.PointingHandCursor)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)

        main_layout.addLayout(header_layout)

        description = QLabel(
            "Everyone currently registered for face recognition on this device"
        )
        description.setObjectName("pageDescription")
        description.setWordWrap(True)

        main_layout.addWidget(description)

        # ================= TABLE CARD =================

        table_card = QFrame()
        table_card.setObjectName("identitiesCard")

        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(15, 15, 15, 15)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Enrolled On", "Samples", ""]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)

        table_layout.addWidget(self.table)

        main_layout.addWidget(table_card, 1)

        self.empty_label = QLabel(
            "No identities enrolled yet — head to Enroll Identity to add one"
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

            #deleteButton {
                background-color: transparent;
                color: #e2596b;
                border: 1px solid #4a2a30;
                border-radius: 6px;
                padding: 4px 12px;
                font-size: 11px;
                font-weight: 600;
            }

            #deleteButton:hover {
                background-color: #251519;
            }

            #identitiesCard {
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

    def set_identities(self, identities):
        """identities: list of dicts with name, enrolled_at, sample_count
        (the same shape Database.get_all_users() returns)."""

        if not identities:
            self.table.setRowCount(0)
            self.table.hide()
            self.empty_label.show()
            return

        self.empty_label.hide()
        self.table.show()

        self.table.setRowCount(len(identities))

        for row_index, entry in enumerate(identities):

            name = entry.get("name", "")
            enrolled_at = entry.get("enrolled_at", "")
            sample_count = str(entry.get("sample_count", ""))

            values = [name, enrolled_at, sample_count]

            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.table.setItem(row_index, col, item)

            delete_button = QPushButton("Delete")
            delete_button.setObjectName("deleteButton")
            delete_button.setCursor(Qt.PointingHandCursor)
            delete_button.clicked.connect(
                lambda checked=False, n=name: self.delete_requested.emit(n)
            )
            self.table.setCellWidget(row_index, 3, delete_button)
