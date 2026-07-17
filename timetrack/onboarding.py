"""Systemcheck & Erste Schritte: prüft, was die App zum Funktionieren braucht."""

import re
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from . import SUPPORT_URL
from .i18n import tr
from .issue import find_tool

HOWTO_DB = """brew install postgresql@17
brew services start postgresql@17
/opt/homebrew/opt/postgresql@17/bin/createdb timetrack"""

HOWTO_GH_INSTALL = """brew install gh
gh auth login"""


def _run(cmd: list[str], timeout: int = 4):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None


def check_database(db) -> tuple[bool, str, str]:
    """PostgreSQL: erforderlich."""
    if db is None:
        return False, tr("Keine Verbindung konfiguriert."), HOWTO_DB
    try:
        db.project_names()
    except Exception as exc:  # noqa: BLE001
        return False, tr("Verbindung gestört: {}").format(exc), HOWTO_DB
    dsn = re.sub(r"password=\S+", "password=•••", db.dsn)
    return True, tr("Verbunden ({}).").format(dsn), ""


def check_gh() -> tuple[bool, str, str]:
    """GitHub-CLI: optional, nur für die Issue-Erstellung."""
    gh = find_tool("gh")
    if gh is None:
        return False, tr("GitHub-CLI (gh) ist nicht installiert."), HOWTO_GH_INSTALL
    result = _run([gh, "auth", "status"])
    if result is None:
        return False, tr("gh gefunden, Status nicht prüfbar (Timeout)."), "gh auth status"
    if result.returncode != 0:
        return False, tr("gh ist installiert, aber nicht angemeldet."), "gh auth login"
    match = re.search(r"account (\S+)", (result.stdout or "") + (result.stderr or ""))
    if match:
        return True, tr("Installiert und angemeldet als {}.").format(match.group(1)), ""
    return True, tr("Installiert und angemeldet."), ""


def check_claude() -> tuple[bool, str, str]:
    """Claude Code: optional, nur für den Issue-Assistenten."""
    if find_tool("claude") is None:
        guide = ("brew install --cask claude-code\n"
                 + tr("claude   # einmal starten und anmelden"))
        return False, tr("Claude Code (claude) ist nicht installiert."), guide
    return True, tr("Installiert – der Login erfolgt beim ersten Aufruf."), ""


CHECKS = [
    ("PostgreSQL-Datenbank", "erforderlich – hier landen alle Zeiten und Notizen",
     lambda db: check_database(db)),
    ("GitHub-CLI (gh)", "optional – nur für „Issue aus Notiz erstellen“",
     lambda db: check_gh()),
    ("Claude Code (claude)", "optional – nur für den Issue-Assistenten",
     lambda db: check_claude()),
]


class ChecklistDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle(tr("TimeTrack – Systemcheck & Erste Schritte"))
        self.setMinimumWidth(560)

        intro = QLabel(
            tr("Damit alle Funktionen von TimeTrack laufen, braucht dein Mac "
               "die folgenden Dinge. Die Zeiterfassung selbst funktioniert "
               "schon mit der Datenbank – GitHub- und Claude-Integration sind "
               "optional."))
        intro.setWordWrap(True)

        self._rows: list[tuple[QLabel, QLabel, QLabel]] = []
        layout = QVBoxLayout(self)
        layout.addWidget(intro)

        for title, level, _check in CHECKS:
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            box = QVBoxLayout(frame)

            head = QLabel(f"<b>{tr(title)}</b> "
                          f"<span style='color:gray'>({tr(level)})</span>")
            status = QLabel()
            status.setWordWrap(True)
            howto = QLabel()
            howto.setWordWrap(True)
            howto.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse)
            howto.setStyleSheet(
                "font-family: Menlo, monospace; font-size: 11px; "
                "background: palette(alternate-base); padding: 6px; border-radius: 4px;")

            box.addWidget(head)
            box.addWidget(status)
            box.addWidget(howto)
            layout.addWidget(frame)
            self._rows.append((head, status, howto))

        note = QLabel(
            tr("Hinweis: TimeTrack speichert keine Zugangsdaten. Das "
               "DB-Passwort liegt verschlüsselt in deinem macOS-Schlüsselbund, "
               "GitHub und Claude nutzen deine lokalen CLI-Logins."))
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(note)

        support = QLabel(
            tr("Gefällt dir TimeTrack? <a href=\"{}\">☕ Buy me a coffee</a>")
            .format(SUPPORT_URL))
        support.setOpenExternalLinks(True)
        support.setStyleSheet("font-size: 11px;")
        layout.addWidget(support)

        recheck_btn = QPushButton(tr("Erneut prüfen"))
        recheck_btn.clicked.connect(self.refresh)
        close_btn = QPushButton(tr("Schließen"))
        close_btn.setDefault(True)
        close_btn.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addWidget(recheck_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self.refresh()

    def refresh(self):
        for (title, level, check), (_head, status, howto) in zip(CHECKS, self._rows):
            ok, text, guide = check(self.db)
            icon = "✅" if ok else "⚠️"
            status.setText(f"{icon}  {text}")
            howto.setText(guide.replace("\n", "<br>"))
            howto.setVisible(bool(guide))
