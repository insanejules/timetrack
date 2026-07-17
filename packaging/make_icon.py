"""Erzeugt das App-Icon (TimeTrack.icns) – einmalig bzw. bei Design-Änderung."""

import os
import subprocess
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QGuiApplication, QLinearGradient, QPainter, QPen, QPixmap

HERE = os.path.dirname(os.path.abspath(__file__))


def draw(size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Abgerundetes Quadrat mit Rand (macOS-Stil), blauer Verlauf
    margin = size * 0.09
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, QColor("#3b82c4"))
    gradient.setColorAt(1.0, QColor("#1e3f66"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(gradient))
    p.drawRoundedRect(rect, size * 0.2, size * 0.2)

    # Weiße Uhr
    center = rect.center()
    radius = rect.width() * 0.30
    pen = QPen(QColor("white"), max(2.0, size * 0.045))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(center, radius, radius)
    # Zeiger: Minute nach oben, Stunde nach rechts unten
    p.drawLine(center, QPointF(center.x(), center.y() - radius * 0.62))
    p.drawLine(center, QPointF(center.x() + radius * 0.42, center.y() + radius * 0.25))

    p.end()
    return pm


def main() -> int:
    app = QGuiApplication(sys.argv)  # noqa: F841 - für QPixmap nötig
    iconset = os.path.join(HERE, "TimeTrack.iconset")
    os.makedirs(iconset, exist_ok=True)

    sizes = {16: "16x16", 32: "16x16@2x", 64: "32x32@2x", 128: "128x128",
             256: "128x128@2x", 512: "256x256@2x", 1024: "512x512@2x"}
    for px, name in sizes.items():
        draw(px).save(os.path.join(iconset, f"icon_{name}.png"))
    draw(32).save(os.path.join(iconset, "icon_32x32.png"))
    draw(256).save(os.path.join(iconset, "icon_256x256.png"))
    draw(512).save(os.path.join(iconset, "icon_512x512.png"))

    subprocess.run(
        ["iconutil", "-c", "icns", iconset, "-o", os.path.join(HERE, "TimeTrack.icns")],
        check=True)
    print("TimeTrack.icns erzeugt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
