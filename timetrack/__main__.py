"""Einstiegspunkt: python -m timetrack"""

import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from .db import Database
from .settings import SettingsDialog, is_configured
from .tracker import TrackerWidget
from .tray import Tray


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("TimeTrack")

    # Erststart: einmaliges Setup (DB-Zugang abfragen, Passwort -> Keychain)
    if not is_configured():
        setup = SettingsDialog(None, first_run=True)
        setup.exec()  # bei Abbruch unten einfach die Defaults probieren

    # Verbindung aufbauen; schlägt sie fehl, direkt die Einstellungen anbieten
    while True:
        try:
            db = Database()
            break
        except Exception as exc:  # noqa: BLE001 - Fehler dem Nutzer anzeigen
            QMessageBox.critical(
                None,
                "TimeTrack – Datenbankfehler",
                "Konnte keine Verbindung zur Postgres-Datenbank aufbauen:\n\n"
                f"{exc}\n\nLäuft Postgres? Im nächsten Dialog kannst du die "
                "Verbindung anpassen.",
            )
            dialog = SettingsDialog(None)
            if dialog.exec() != SettingsDialog.DialogCode.Accepted:
                return 1

    widget = TrackerWidget(db)

    if QSystemTrayIcon.isSystemTrayAvailable():
        tray = Tray(widget)
        tray.show()
        widget.tray = tray
        # Fenster schließen beendet die App nicht mehr – sie lebt in der Menüleiste
        app.setQuitOnLastWindowClosed(False)

    widget.show()

    # Einmalig nach dem ersten Start: zeigen, was die App alles braucht
    from PySide6.QtCore import QSettings
    from .settings import APP, ORG
    prefs = QSettings(ORG, APP)
    if not prefs.value("onboarding/done", False, bool):
        widget.show_onboarding()
        prefs.setValue("onboarding/done", True)
        prefs.sync()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
