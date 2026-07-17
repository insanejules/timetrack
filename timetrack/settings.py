"""Einstellungen: DB-Verbindung via QSettings, Passwort im macOS-Schlüsselbund.

Es werden bewusst keine Zugangsdaten in der App, im Bundle oder in
Konfigurationsdateien abgelegt: Host/Port/DB/Benutzer stehen in den
macOS-Preferences, das Passwort ausschließlich verschlüsselt in der Keychain
des jeweiligen Nutzers. GitHub und Claude nutzen die lokalen CLI-Logins des
Nutzers (gh auth login, claude) – dafür speichert TimeTrack nichts.
"""

import os
import subprocess

import psycopg
from psycopg.conninfo import make_conninfo
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

ORG = "timetrack"
APP = "TimeTrack"

DEFAULTS = {
    "host": "",          # leer = lokaler Unix-Socket
    "port": 5432,
    "dbname": "timetrack",
    "user": "",          # leer = aktueller macOS-Benutzer
    "password": "",
}

KEYCHAIN_SERVICE = "TimeTrack"
KEYCHAIN_ACCOUNT = "database"


# ---- macOS-Keychain ------------------------------------------------------

def keychain_set_password(password: str, account: str = KEYCHAIN_ACCOUNT):
    if not password:
        keychain_delete_password(account)
        return
    # Hex-kodiert gespeichert: `security … -w` gibt Nicht-ASCII-Passwörter
    # sonst mehrdeutig hex-kodiert zurück, und Shell-Escaping entfällt.
    # Übergabe via stdin, damit nichts in der Prozessliste (argv) auftaucht.
    encoded = password.encode("utf-8").hex()
    subprocess.run(
        ["/usr/bin/security", "-i"],
        input=(f'add-generic-password -U -s "{KEYCHAIN_SERVICE}" '
               f'-a "{account}" -w "{encoded}"\n'),
        capture_output=True, text=True, check=True)


def keychain_get_password(account: str = KEYCHAIN_ACCOUNT) -> str:
    result = subprocess.run(
        ["/usr/bin/security", "find-generic-password",
         "-s", KEYCHAIN_SERVICE, "-a", account, "-w"],
        capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    raw = result.stdout.strip()
    try:
        return bytes.fromhex(raw).decode("utf-8")
    except ValueError:
        return raw  # manuell/extern angelegter Klartext-Eintrag


def keychain_delete_password(account: str = KEYCHAIN_ACCOUNT):
    subprocess.run(
        ["/usr/bin/security", "delete-generic-password",
         "-s", KEYCHAIN_SERVICE, "-a", account],
        capture_output=True, text=True)


# ---- Laden/Speichern -----------------------------------------------------

def load_settings() -> dict:
    s = QSettings(ORG, APP)
    # Migration: Passwort aus alten Versionen lag im Plist -> in die Keychain
    legacy_password = str(s.value("db/password", ""))
    if legacy_password:
        keychain_set_password(legacy_password)
        s.remove("db/password")
        s.sync()
    return {
        "host": str(s.value("db/host", DEFAULTS["host"])),
        "port": int(s.value("db/port", DEFAULTS["port"])),
        "dbname": str(s.value("db/dbname", DEFAULTS["dbname"])) or "timetrack",
        "user": str(s.value("db/user", DEFAULTS["user"])),
        "password": keychain_get_password(),
    }


def save_settings(values: dict):
    values = dict(values)
    keychain_set_password(values.pop("password", ""))
    s = QSettings(ORG, APP)
    for key, value in values.items():
        s.setValue(f"db/{key}", value)
    s.remove("db/password")  # Altbestand aus dem Plist sicher entfernen
    s.sync()


def is_configured() -> bool:
    """True, sobald das Setup einmal gespeichert wurde."""
    return QSettings(ORG, APP).contains("db/dbname")


def dsn_from_values(values: dict, *, with_password: bool = True) -> str:
    params = {"dbname": values["dbname"], "port": values["port"]}
    if values["host"]:
        params["host"] = values["host"]
    if values["user"]:
        params["user"] = values["user"]
    if with_password and values["password"]:
        params["password"] = values["password"]
    return make_conninfo(**params)


def resolve_dsn() -> str:
    """Verbindungsstring: Umgebungsvariable gewinnt, sonst gespeicherte Einstellungen."""
    return os.environ.get("TIMETRACK_DB") or dsn_from_values(load_settings())


class SettingsDialog(QDialog):
    def __init__(self, db, parent=None, first_run: bool = False):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("TimeTrack – Einrichtung" if first_run
                            else "TimeTrack – Einstellungen")
        self.setMinimumWidth(440)

        values = load_settings()

        self.host = QLineEdit(values["host"])
        self.host.setPlaceholderText("leer = lokaler Socket (Homebrew-Postgres)")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(values["port"])
        self.dbname = QLineEdit(values["dbname"])
        self.user = QLineEdit(values["user"])
        self.user.setPlaceholderText("leer = aktueller macOS-Benutzer")
        self.password = QLineEdit(values["password"])
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("leer = kein Passwort")

        form = QFormLayout()
        form.addRow("Host:", self.host)
        form.addRow("Port:", self.port)
        form.addRow("Datenbank:", self.dbname)
        form.addRow("Benutzer:", self.user)
        form.addRow("Passwort:", self.password)

        self.preview = QLabel()
        self.preview.setStyleSheet("color: gray; font-size: 11px;")
        self.preview.setWordWrap(True)
        for widget in (self.host, self.dbname, self.user):
            widget.textChanged.connect(self._update_preview)
        self.port.valueChanged.connect(self._update_preview)
        self._update_preview()

        layout = QVBoxLayout(self)
        if first_run:
            welcome = QLabel(
                "<b>Willkommen bei TimeTrack!</b><br>"
                "Richte einmalig die Verbindung zu deiner PostgreSQL-Datenbank "
                "ein. Für einen lokalen Homebrew-Postgres passen die Vorgaben – "
                "einfach „Verbindung testen“ und dann „Speichern“.")
            welcome.setWordWrap(True)
            layout.addWidget(welcome)
        layout.addLayout(form)
        layout.addWidget(self.preview)

        if os.environ.get("TIMETRACK_DB"):
            env_hint = QLabel(
                "⚠️ Die Umgebungsvariable TIMETRACK_DB ist gesetzt und überschreibt "
                "diese Einstellungen beim nächsten Start.")
            env_hint.setWordWrap(True)
            layout.addWidget(env_hint)

        pw_hint = QLabel(
            "Das Passwort wird verschlüsselt im macOS-Schlüsselbund (Keychain) "
            "gespeichert – nie in der App oder in Konfigurationsdateien. Für den "
            "lokalen Homebrew-Postgres ist keins nötig.")
        pw_hint.setStyleSheet("color: gray; font-size: 11px;")
        pw_hint.setWordWrap(True)
        layout.addWidget(pw_hint)

        from . import __version__
        version_label = QLabel(f"TimeTrack v{__version__}")
        version_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(version_label)

        test_btn = QPushButton("Verbindung testen")
        test_btn.clicked.connect(self._test_connection)

        buttons = QDialogButtonBox()
        buttons.addButton(test_btn, QDialogButtonBox.ButtonRole.ActionRole)
        save_btn = buttons.addButton("Speichern", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton("Abbrechen", QDialogButtonBox.ButtonRole.RejectRole)
        save_btn.setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _values(self) -> dict:
        return {
            "host": self.host.text().strip(),
            "port": self.port.value(),
            "dbname": self.dbname.text().strip() or "timetrack",
            "user": self.user.text().strip(),
            "password": self.password.text(),
        }

    def _update_preview(self):
        self.preview.setText(
            "Verbindung: " + dsn_from_values(self._values(), with_password=False))

    def _test_connection(self):
        try:
            with psycopg.connect(dsn_from_values(self._values()), connect_timeout=5) as conn:
                version = conn.execute("SELECT version()").fetchone()[0]
            QMessageBox.information(
                self, "Verbindung OK", f"Verbindung erfolgreich:\n\n{version}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(
                self, "Verbindung fehlgeschlagen", f"Keine Verbindung möglich:\n\n{exc}")

    def accept(self):
        values = self._values()
        dsn = dsn_from_values(values)
        try:
            if self.db is not None:
                self.db.reconnect(dsn)
            else:
                # Start-Fall: noch keine Datenbank – nur prüfen, ob die Verbindung geht
                with psycopg.connect(dsn, connect_timeout=5):
                    pass
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self, "Verbindung fehlgeschlagen",
                "Die neue Verbindung konnte nicht aufgebaut werden – die bisherige "
                f"bleibt aktiv:\n\n{exc}")
            return  # Dialog offen lassen, damit Eingaben korrigiert werden können
        save_settings(values)
        super().accept()
