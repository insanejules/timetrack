"""Menüleisten-Icon: App läuft nach dem Schließen des Fensters weiter."""

from datetime import datetime, timezone

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from . import SUPPORT_URL


def _clock_icon() -> QIcon:
    """Einfache Uhr als Template-Icon (passt sich heller/dunkler Menüleiste an)."""
    pm = QPixmap(44, 44)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(Qt.GlobalColor.black, 3))
    painter.drawEllipse(4, 4, 36, 36)
    painter.drawLine(22, 22, 22, 11)
    painter.drawLine(22, 22, 30, 26)
    painter.end()
    icon = QIcon(pm)
    icon.setIsMask(True)
    return icon


class Tray(QSystemTrayIcon):
    def __init__(self, tracker):
        super().__init__(_clock_icon(), tracker)
        self.tracker = tracker

        self._menu = QMenu()
        self.status_action = self._menu.addAction("Kein Timer aktiv")
        self.status_action.setEnabled(False)
        self._menu.addSeparator()
        show_action = self._menu.addAction("Widget anzeigen")
        show_action.triggered.connect(self._show_tracker)
        check_action = self._menu.addAction("Systemcheck && Anleitung…")
        check_action.triggered.connect(tracker.show_onboarding)
        self.stop_action = self._menu.addAction("Timer stoppen && speichern")
        self.stop_action.triggered.connect(self._stop_timer)
        self._menu.addSeparator()
        coffee_action = self._menu.addAction("☕ Einen Kaffee spendieren…")
        coffee_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl(SUPPORT_URL)))
        quit_action = self._menu.addAction("TimeTrack beenden")
        quit_action.triggered.connect(tracker.quit_app)
        from . import __version__
        version_action = self._menu.addAction(f"Version {__version__}")
        version_action.setEnabled(False)
        self.setContextMenu(self._menu)
        self._menu.aboutToShow.connect(self._refresh)

        # Tooltip regelmäßig aktualisieren (zeigt Projekt + Laufzeit beim Hovern)
        self._ticker = QTimer(self)
        self._ticker.setInterval(1000)
        self._ticker.timeout.connect(self._refresh)
        self._ticker.start()
        self._refresh()

    def _refresh(self):
        from .tracker import fmt_hms

        if self.tracker.entry_id is not None and self.tracker.started_at is not None:
            elapsed = int(
                (datetime.now(timezone.utc) - self.tracker.started_at).total_seconds())
            text = f"{self.tracker.project.currentText()} – {fmt_hms(elapsed)}"
            self.status_action.setText(f"Läuft: {text}")
            self.stop_action.setEnabled(True)
            self.setToolTip(f"TimeTrack – {text}")
        else:
            self.status_action.setText("Kein Timer aktiv")
            self.stop_action.setEnabled(False)
            self.setToolTip("TimeTrack – kein Timer aktiv")

    def _show_tracker(self):
        self.tracker.show()
        self.tracker.raise_()
        self.tracker.activateWindow()

    def _stop_timer(self):
        if self.tracker.entry_id is not None:
            self.tracker._stop()
