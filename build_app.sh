#!/bin/zsh
# Baut TimeTrack.app (PyInstaller) und ein Zip zum Verschicken.
set -e
cd "$(dirname "$0")"

.venv/bin/pip show pyinstaller > /dev/null 2>&1 || .venv/bin/pip install pyinstaller
[ -f packaging/TimeTrack.icns ] || .venv/bin/python packaging/make_icon.py

.venv/bin/pyinstaller --noconfirm --clean --windowed \
    --name TimeTrack \
    --icon packaging/TimeTrack.icns \
    --osx-bundle-identifier com.timetrack.TimeTrack \
    --paths . \
    packaging/launcher.py

# Version aus dem Paket in die Info.plist übernehmen (sichtbar im Finder)
VERSION=$(.venv/bin/python -c "import timetrack; print(timetrack.__version__)")
plutil -replace CFBundleShortVersionString -string "$VERSION" dist/TimeTrack.app/Contents/Info.plist
plutil -replace CFBundleVersion -string "$VERSION" dist/TimeTrack.app/Contents/Info.plist

# Versand-Ordner: App + Anleitung zusammen in ein Zip
STAGE=dist/TimeTrack-Versand
rm -rf "$STAGE" dist/TimeTrack-Versand.zip dist/TimeTrack-app.zip
mkdir -p "$STAGE"
ditto dist/TimeTrack.app "$STAGE/TimeTrack.app"
cp packaging/Anleitung.txt "$STAGE/Anleitung.txt"
ditto -c -k --keepParent "$STAGE" dist/TimeTrack-Versand.zip

echo ""
echo "Fertig:"
echo "  App: dist/TimeTrack.app"
echo "  Zip: dist/TimeTrack-Versand.zip  ($(du -h dist/TimeTrack-Versand.zip | cut -f1 | tr -d ' '))  – enthält App + Anleitung"
