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

from .issue import find_tool

HOWTO_DB = """brew install postgresql@17
brew services start postgresql@17
/opt/homebrew/opt/postgresql@17/bin/createdb timetrack"""

HOWTO_GH_INSTALL = """brew install gh
gh auth login"""

HOWTO_CLAUDE = """brew install --cask claude-code
claude   # einmal starten und anmelden"""


def _run(cmd: list[str], timeout: int = 4):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None


def check_database(db) -> tuple[bool, str, str]:
    """PostgreSQL: erforderlich."""
    if db is None:
        return False, "Keine Verbindung konfiguriert.", HOWTO_DB
    try:
        db.project_names()
    except Exception as exc:  # noqa: BLE001
        return False, f"Verbindung gestört: {exc}", HOWTO_DB
    dsn = re.sub(r"password=\S+", "password=•••", db.dsn)
    return True, f"Verbunden ({dsn}).", ""


def check_gh() -> tuple[bool, str, str]:
    """GitHub-CLI: optional, nur für die Issue-Erstellung."""
    gh = find_tool("gh")
    if gh is None:
        return False, "GitHub-CLI (gh) ist nicht installiert.", HOWTO_GH_INSTALL
    result = _run([gh, "auth", "status"])
    if result is None:
        return False, "gh gefunden, Status nicht prüfbar (Timeout).", "gh auth status"
    if result.returncode != 0:
        return False, "gh ist installiert, aber nicht angemeldet.", "gh auth login"
    match = re.search(r"account (\S+)", (result.stdout or "") + (result.stderr or ""))
    account = f" als {match.group(1)}" if match else ""
    return True, f"Installiert und angemeldet{account}.", ""


def check_claude() -> tuple[bool, str, str]:
    """Claude Code: optional, nur für den Issue-Assistenten."""
    if find_tool("claude") is None:
        return False, "Claude Code (claude) ist nicht installiert.", HOWTO_CLAUDE
    return True, "Installiert – der Login erfolgt beim ersten Aufruf.", ""


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
        self.setWindowTitle("TimeTrack – Systemcheck & Erste Schritte")
        self.setMinimumWidth(560)

        intro = QLabel(
            "Damit alle Funktionen von TimeTrack laufen, braucht dein Mac die "
            "folgenden Dinge. Die Zeiterfassung selbst funktioniert schon mit "
            "der Datenbank – GitHub- und Claude-Integration sind optional.")
        intro.setWordWrap(True)

        self._rows: list[tuple[QLabel, QLabel, QLabel]] = []
        layout = QVBoxLayout(self)
        layout.addWidget(intro)

        for title, level, _check in CHECKS:
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            box = QVBoxLayout(frame)

            head = QLabel(f"<b>{title}</b> <span style='color:gray'>({level})</span>")
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
            "Hinweis: TimeTrack speichert keine Zugangsdaten. Das DB-Passwort "
            "liegt verschlüsselt in deinem macOS-Schlüsselbund, GitHub und "
            "Claude nutzen deine lokalen CLI-Logins.")
        note.setWordWrap(True)
        note.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(note)

        recheck_btn = QPushButton("Erneut prüfen")
        recheck_btn.clicked.connect(self.refresh)
        close_btn = QPushButton("Schließen")
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
