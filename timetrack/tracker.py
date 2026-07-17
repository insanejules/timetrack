"""Das kompakte Haupt-Widget: Projekt, Beschreibung, Start/Stop-Timer."""

from datetime import datetime, timezone

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QCompleter,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .db import Database
from .history import HistoryWindow
from .i18n import tr
from .knowledge import KnowledgeWindow
from .settings import SettingsDialog


def fmt_hms(secs: int) -> str:
    h, rest = divmod(max(0, secs), 3600)
    m, s = divmod(rest, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class TrackerWidget(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.entry_id: int | None = None
        self.started_at: datetime | None = None
        self.tray = None  # wird in __main__ gesetzt, wenn eine Menüleiste verfügbar ist
        self._knowledge: KnowledgeWindow | None = None
        self._history: HistoryWindow | None = None

        self.setWindowTitle(f"TimeTrack v{__version__}")
        self.setMinimumWidth(320)

        # -- Projekt + Beschreibung --
        self.project = QComboBox()
        self.project.setEditable(True)
        self.project.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.project.lineEdit().setPlaceholderText(tr("Projekt…"))
        self._reload_projects()

        self.description = QLineEdit()
        self.description.setPlaceholderText(tr("Beschreibung…"))
        self.description.returnPressed.connect(self._toggle)

        self.issue_combo = QComboBox()
        self.issue_combo.setToolTip(
            tr("Optional: Arbeitszeit direkt auf ein GitHub-Issue buchen"))
        self.project.currentTextChanged.connect(self._reload_issues)
        self._reload_issues()

        # -- Timer-Anzeige --
        self.clock = QLabel("00:00:00")
        clock_font = QFont()
        clock_font.setPointSize(32)
        clock_font.setBold(True)
        self.clock.setFont(clock_font)
        self.clock.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.today = QLabel()
        self.today.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.today.setStyleSheet("color: gray;")

        # -- Buttons --
        self.start_stop = QPushButton(tr("▶  Start"))
        self.start_stop.setMinimumHeight(36)
        self.start_stop.clicked.connect(self._toggle)

        notes_btn = QToolButton()
        notes_btn.setText("📓")
        notes_btn.setToolTip(tr("Knowledgebase (Notizen zu Kunden & Projekten)"))
        notes_btn.clicked.connect(self._show_knowledge)

        history_btn = QToolButton()
        history_btn.setText("📊")
        history_btn.setToolTip(tr("Historie & Auswertung"))
        history_btn.clicked.connect(self._show_history)

        settings_btn = QToolButton()
        settings_btn.setText("⚙️")
        settings_btn.setToolTip(tr("Einstellungen (Datenbank-Verbindung)"))
        settings_btn.clicked.connect(self._show_settings)

        info_btn = QToolButton()
        info_btn.setText("ℹ️")
        info_btn.setToolTip(tr("Systemcheck & Erste Schritte"))
        info_btn.clicked.connect(self.show_onboarding)

        self.pin_btn = QToolButton()
        self.pin_btn.setText("📌")
        self.pin_btn.setToolTip(tr("Fenster immer im Vordergrund halten"))
        self.pin_btn.setCheckable(True)
        self.pin_btn.toggled.connect(self._toggle_pin)

        top = QHBoxLayout()
        top.addWidget(self.pin_btn)
        top.addStretch()
        top.addWidget(notes_btn)
        top.addWidget(history_btn)
        top.addWidget(settings_btn)
        top.addWidget(info_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.clock)
        layout.addWidget(self.today)
        layout.addWidget(self.project)
        layout.addWidget(self.issue_combo)
        layout.addWidget(self.description)
        layout.addWidget(self.start_stop)

        self.ticker = QTimer(self)
        self.ticker.setInterval(1000)
        self.ticker.timeout.connect(self._tick)

        self._resume_open_entry()
        self._update_today()

    # ---- Timer-Logik ----------------------------------------------------

    def _resume_open_entry(self):
        """Nach App-Neustart einen noch laufenden Eintrag weiterführen."""
        entry = self.db.open_entry()
        if not entry:
            return
        self.entry_id = entry["id"]
        self.started_at = entry["started_at"]
        self.project.setCurrentText(entry["project"])
        self.description.setText(entry["description"])
        self._reload_issues()
        idx = self.issue_combo.findData(entry["issue_id"])
        self.issue_combo.setCurrentIndex(max(0, idx))
        self._enter_running_state()
        self._tick()

    def _toggle(self):
        if self.entry_id is None:
            self._start()
        else:
            self._stop()

    def _start(self):
        name = self.project.currentText().strip()
        if not name:
            QMessageBox.warning(self, "TimeTrack",
                                tr("Bitte zuerst ein Projekt angeben."))
            return
        project_id = self.db.ensure_project(name)
        self.entry_id = self.db.start_entry(
            project_id, self.description.text().strip(),
            issue_id=self.issue_combo.currentData())
        self.started_at = datetime.now(timezone.utc)
        self._enter_running_state()

    def _stop(self):
        self.db.stop_entry(self.entry_id, self.description.text().strip())
        self.entry_id = None
        self.started_at = None
        self.ticker.stop()
        self.clock.setText("00:00:00")
        self.description.clear()
        self.start_stop.setText(tr("▶  Start"))
        self.project.setEnabled(True)
        self.issue_combo.setEnabled(True)
        self._reload_projects()
        self._reload_issues()
        self._update_today()

    def _enter_running_state(self):
        self.start_stop.setText(tr("⏹  Stop"))
        self.project.setEnabled(False)
        self.issue_combo.setEnabled(False)
        self.ticker.start()

    def _tick(self):
        if self.started_at is not None:
            elapsed = int((datetime.now(timezone.utc) - self.started_at).total_seconds())
            self.clock.setText(fmt_hms(elapsed))
            if elapsed % 60 == 0:
                self._update_today()

    def _update_today(self):
        self.today.setText(tr("Heute gesamt: {}").format(fmt_hms(self.db.today_seconds())))

    # ---- Hilfen ---------------------------------------------------------

    def _reload_projects(self):
        current = self.project.currentText()
        names = self.db.project_names()
        self.project.clear()
        self.project.addItems(names)
        completer = QCompleter(names, self.project)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.project.setCompleter(completer)
        self.project.setCurrentText(current)

    def _reload_issues(self):
        """Offene Issues des eingetragenen Projekts als Buchungsziel anbieten."""
        selected = self.issue_combo.currentData()
        self.issue_combo.blockSignals(True)
        self.issue_combo.clear()
        self.issue_combo.addItem(tr("— kein Issue —"), None)
        project_id = self.db.project_id_by_name(self.project.currentText())
        if project_id is not None:
            for issue in self.db.open_issues(project_id):
                self.issue_combo.addItem(
                    f"#{issue['number']}  {issue['title']}", issue["id"])
        idx = self.issue_combo.findData(selected)
        self.issue_combo.setCurrentIndex(max(0, idx))
        self.issue_combo.blockSignals(False)

    def _toggle_pin(self, checked: bool):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, checked)
        self.show()

    def _show_knowledge(self):
        if self._knowledge is None:
            self._knowledge = KnowledgeWindow(self.db)
        self._knowledge.reload()
        self._knowledge.show()
        self._knowledge.raise_()

    def _show_history(self):
        if self._history is None:
            self._history = HistoryWindow(self.db)
        self._history.reload()
        self._history.show()
        self._history.raise_()

    def show_onboarding(self):
        from .onboarding import ChecklistDialog
        ChecklistDialog(self.db, self).exec()

    def _show_settings(self):
        if self.entry_id is not None:
            QMessageBox.information(
                self, "TimeTrack",
                tr("Bitte zuerst den laufenden Timer stoppen – während ein "
                   "Eintrag läuft, kann die Datenbankverbindung nicht "
                   "gewechselt werden."))
            return
        dialog = SettingsDialog(self.db, self)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            # Neue DB kann andere Projekte/Einträge (auch einen offenen) enthalten
            self._reload_projects()
            self._update_today()
            self._resume_open_entry()
            if self._knowledge is not None:
                self._knowledge.reload()
            if self._history is not None:
                self._history.reload()

    # ---- Beenden --------------------------------------------------------

    def _confirm_quit(self) -> bool:
        """Beenden vorbereiten; False, wenn der Nutzer abbricht."""
        if self.entry_id is not None:
            box = QMessageBox(self)
            box.setWindowTitle(tr("Timer läuft noch"))
            box.setText(tr("Der Timer läuft noch. Was soll passieren?"))
            stop_btn = box.addButton(tr("Stoppen && speichern"),
                                     QMessageBox.ButtonRole.AcceptRole)
            box.addButton(tr("Weiterlaufen lassen"),
                          QMessageBox.ButtonRole.DestructiveRole)
            cancel = box.addButton(tr("Abbrechen"), QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is cancel:
                return False
            if box.clickedButton() is stop_btn:
                self._stop()
            # sonst: Eintrag bleibt offen und wird beim nächsten Start fortgesetzt
        if self._knowledge is not None:
            self._knowledge.close()
        if self._history is not None:
            self._history.close()
        return True

    def quit_app(self):
        """Komplett beenden (aus dem Menüleisten-Menü)."""
        self.show()
        self.raise_()
        if self._confirm_quit():
            QApplication.instance().quit()

    def closeEvent(self, event):
        # Mit Menüleisten-Icon: Fenster nur verstecken, App (und Timer) laufen weiter.
        if self.tray is not None:
            self.hide()
            event.ignore()
            return
        if self._confirm_quit():
            event.accept()
        else:
            event.ignore()
