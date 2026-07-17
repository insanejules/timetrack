"""Historie & Auswertung: Einträge nach Zeitraum, Summen pro Projekt."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .db import Database

# Feste, sichere SQL-Fragmente für die Zeitraum-Auswahl
PERIODS = [
    ("Heute", "date_trunc('day', now())"),
    ("Diese Woche", "date_trunc('week', now())"),
    ("Dieser Monat", "date_trunc('month', now())"),
    ("Alles", None),
]

ROLE_ENTRY_ID = Qt.ItemDataRole.UserRole


def fmt_hours(secs: float) -> str:
    h, rest = divmod(int(secs), 3600)
    m = rest // 60
    return f"{h:d}:{m:02d} h"


class HistoryWindow(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self._loading = False

        self.setWindowTitle("TimeTrack – Historie")
        self.resize(860, 520)

        self.period = QComboBox()
        for label, _sql in PERIODS:
            self.period.addItem(label)
        self.period.currentIndexChanged.connect(self.reload)

        refresh_btn = QPushButton("Aktualisieren")
        refresh_btn.clicked.connect(self.reload)

        self.total_label = QLabel()
        font = self.total_label.font()
        font.setBold(True)
        self.total_label.setFont(font)

        top = QHBoxLayout()
        top.addWidget(QLabel("Zeitraum:"))
        top.addWidget(self.period)
        top.addWidget(refresh_btn)
        top.addStretch()
        top.addWidget(self.total_label)

        # -- Tab 1: Einzeleinträge --
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Datum", "Zeit", "Dauer", "Projekt", "Kunde", "Issue", "Beschreibung"])
        self.table.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemChanged.connect(self._description_edited)

        delete_btn = QPushButton("Ausgewählte löschen")
        delete_btn.clicked.connect(self._delete_selected)

        entries_tab = QWidget()
        entries_layout = QVBoxLayout(entries_tab)
        entries_layout.setContentsMargins(0, 8, 0, 0)
        entries_layout.addWidget(self.table)
        entries_layout.addWidget(delete_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # -- Tab 2: Summen pro Projekt --
        self.totals_table = QTableWidget(0, 2)
        self.totals_table.setHorizontalHeaderLabels(["Projekt", "Summe"])
        self.totals_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.totals_table.verticalHeader().hide()
        self.totals_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # -- Tab 3: Summen pro Issue --
        self.issue_table = QTableWidget(0, 3)
        self.issue_table.setHorizontalHeaderLabels(["Issue", "Projekt", "Summe"])
        self.issue_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch)
        self.issue_table.verticalHeader().hide()
        self.issue_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        tabs = QTabWidget()
        tabs.addTab(entries_tab, "Einträge")
        tabs.addTab(self.totals_table, "Pro Projekt")
        tabs.addTab(self.issue_table, "Pro Issue")

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(tabs)

        self.reload()

    def _since_sql(self) -> str | None:
        return PERIODS[self.period.currentIndex()][1]

    def reload(self):
        self._loading = True
        since = self._since_sql()
        entries = self.db.entries_since(since)

        self.table.setRowCount(len(entries))
        total = 0.0
        for row, e in enumerate(entries):
            start = e["started_at"].astimezone()
            end = e["ended_at"].astimezone() if e["ended_at"] else None
            time_str = start.strftime("%H:%M") + " – " + (end.strftime("%H:%M") if end else "läuft")
            total += float(e["secs"])

            issue_str = ""
            if e["issue_number"] is not None:
                issue_str = f"#{e['issue_number']} {e['issue_title']}"

            cells = [
                start.strftime("%a %d.%m.%Y"),
                time_str,
                fmt_hours(e["secs"]),
                e["project"],
                e["customer"] or "",
                issue_str,
                e["description"],
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setData(ROLE_ENTRY_ID, e["id"])
                if col != 6:  # nur die Beschreibung ist editierbar
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(
            6, QHeaderView.ResizeMode.Stretch)
        self.total_label.setText(f"Gesamt: {fmt_hours(total)}")

        totals = self.db.project_totals(since)
        self.totals_table.setRowCount(len(totals))
        for row, t in enumerate(totals):
            self.totals_table.setItem(row, 0, QTableWidgetItem(t["project"]))
            self.totals_table.setItem(row, 1, QTableWidgetItem(fmt_hours(t["secs"])))

        issue_totals = self.db.issue_totals(since)
        self.issue_table.setRowCount(len(issue_totals))
        for row, t in enumerate(issue_totals):
            label = f"{t['issue_repo']}#{t['issue_number']}  {t['issue_title']}"
            self.issue_table.setItem(row, 0, QTableWidgetItem(label))
            self.issue_table.setItem(row, 1, QTableWidgetItem(t["project"]))
            self.issue_table.setItem(row, 2, QTableWidgetItem(fmt_hours(t["secs"])))

        self._loading = False

    def _description_edited(self, item: QTableWidgetItem):
        if self._loading or item.column() != 6:
            return
        self.db.update_entry_description(item.data(ROLE_ENTRY_ID), item.text().strip())

    def _delete_selected(self):
        rows = {i.row() for i in self.table.selectedItems()}
        if not rows:
            return
        answer = QMessageBox.question(
            self, "Einträge löschen",
            f"{len(rows)} Eintrag/Einträge wirklich löschen?")
        if answer != QMessageBox.StandardButton.Yes:
            return
        for row in rows:
            entry_id = self.table.item(row, 0).data(ROLE_ENTRY_ID)
            self.db.discard_entry(entry_id)
        self.reload()
