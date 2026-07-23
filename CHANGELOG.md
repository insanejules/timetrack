# Changelog

Alle nennenswerten Änderungen dieses Projekts werden hier dokumentiert.
Das Format ist angelehnt an [Keep a Changelog](https://keepachangelog.com/de/),
die Versionierung folgt [Semantic Versioning](https://semver.org/lang/de/).
Jede Version ist als Git-Tag `vX.Y.Z` markiert; die aktuelle Versionsnummer
steht in `timetrack/__init__.py`.

## [0.6.0] – 2026-07-23

### Geändert
- Notizen werden nicht mehr automatisch gespeichert: Ein neuer
  „Speichern“-Button (auch ⌘S) übernimmt Änderungen erst nach Bestätigung.
  Beim Wechsel der Notiz bzw. des Kunden/Projekts oder beim Schließen des
  Fensters fragt TimeTrack bei ungespeicherten Änderungen nach
  (Speichern/Verwerfen) – versehentliche Änderungen landen so nicht mehr
  ungefragt in der Datenbank.

## [0.5.0] – 2026-07-18

### Hinzugefügt
- Zweisprachigkeit: komplette Oberfläche auf Deutsch und Englisch, Auswahl
  in den Einstellungen (System/Deutsch/English, greift nach Neustart);
  Claude-Prompts folgen der Sprache.
- Englische Kurzanleitung (`packaging/Instructions.txt`, liegt dem
  Versand-Zip bei) und englisches README (`README.en.md`) mit
  Sprachumschalt-Links in beiden READMEs.

## [0.4.1] – 2026-07-18

### Hinzugefügt
- Buy-Me-a-Coffee-Link: ☕-Eintrag im Menüleisten-Menü, Link im
  Systemcheck-Dialog, Badge und Support-Abschnitt im README sowie
  `.github/FUNDING.yml` für den GitHub-Sponsor-Button.

## [0.4.0] – 2026-07-18

### Hinzugefügt
- Systemcheck & Erste Schritte (ℹ️ im Widget, Menüleisten-Menü, einmalig nach
  dem ersten Start): prüft Datenbank, GitHub-CLI und Claude Code live und
  zeigt für alles Fehlende eine Mini-Anleitung mit den passenden Befehlen.

## [0.3.0] – 2026-07-18

### Hinzugefügt
- First-Run-Setup: Beim allerersten Start fragt ein Einrichtungs-Dialog die
  Datenbank-Verbindung ab.

### Geändert
- Das DB-Passwort liegt jetzt ausschließlich verschlüsselt im
  macOS-Schlüsselbund (Keychain) statt unverschlüsselt im Preferences-Plist;
  Altbestände werden automatisch migriert. Die App speichert damit nirgendwo
  Zugangsdaten – GitHub und Claude nutzen die lokalen CLI-Logins des Nutzers.
- Persönliche Beispieldaten aus der Oberfläche entfernt.

## [0.2.0] – 2026-07-18

### Hinzugefügt
- GitHub-Issues aus Notizen: eingebettete Claude-Code-Session formuliert aus
  einer Projekt-Notiz ein Issue, `gh` legt es im Repo an, TimeTrack
  dokumentiert es und bietet es im Timer als Buchungsziel an.
- Issue-Auswahl im Timer-Widget, Issue-Spalte und „Pro Issue“-Auswertung in
  der Historie.
- Repo-Dropdown mit den eigenen GitHub-Repos (via `gh repo list`).
- Versionsanzeige in Fenstertitel, Menüleisten-Menü, Einstellungen und
  Info.plist des App-Bundles.

## [0.1.0] – 2026-07-17

### Hinzugefügt
- Timer-Widget mit Projekt-Vorschlägen, Freitext-Beschreibung, Start/Stop und
  Tagessumme; laufende Einträge überleben App-Neustarts (absturzsicher).
- Knowledgebase: Notizen pro Kunde und Projekt, Kunden-Zuordnung von
  Projekten.
- Historie mit Zeiträumen, Summen pro Projekt, editierbaren Beschreibungen
  und Löschen von Fehlbuchungen.
- Menüleisten-Icon: Schließen des Fensters beendet die App nicht.
- Einstellungs-Dialog für die PostgreSQL-Verbindung inkl. Verbindungstest.
- PyInstaller-Build (`build_app.sh`) für ein eigenständiges macOS-App-Bundle
  samt Versand-Zip mit Anleitung.
