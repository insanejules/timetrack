"""Einstiegspunkt für das PyInstaller-Bundle (Paket-Import statt python -m)."""

import sys

from timetrack.__main__ import main

sys.exit(main())
