<p align="center">
  <img src="docs/icon.png" width="120" alt="TimeTrack-Icon">
</p>

<h1 align="center">TimeTrack</h1>

<p align="center">
  Kleines Zeiterfassungs-Widget für macOS – mit PostgreSQL-Backend,
  Knowledgebase und GitHub-Issue-Workflow über Claude Code.
</p>

---

## Was ist TimeTrack?

Projekt eintippen, Timer starten, fertig: TimeTrack ist ein kompaktes
Qt-Widget (PySide6), das Arbeitszeiten in eine PostgreSQL-Datenbank schreibt.
Dazu kommen eine kleine Knowledgebase für Notizen pro Kunde und Projekt, eine
Auswertungs-Historie – und ein Workflow, der aus einer Notiz gemeinsam mit
Claude ein GitHub-Issue formuliert, auf das sich anschließend Arbeitszeit
buchen lässt.

## Features

- **Timer-Widget** – Projekt mit Vorschlägen aus bereits bebuchten Projekten,
  Freitext-Beschreibung, Start/Stop, Tagessumme. 📌 hält das Fenster im
  Vordergrund.
- **Absturzsicher** – laufende Einträge stehen sofort in der DB und werden
  nach einem Neustart nahtlos fortgesetzt.
- **Menüleisten-App** – das Schließen des Fensters beendet nichts: TimeTrack
  läuft als Uhr-Symbol in der Menüleiste weiter (Status, Stoppen, Beenden).
- **Knowledgebase** 📓 – Notizen pro Kunde oder Projekt, Projekte lassen sich
  Kunden zuordnen; automatisches Speichern.
- **GitHub-Issues mit Claude** – „Issue aus Notiz erstellen“ öffnet eine
  eingebettete Claude-Code-Session (lokales `claude`-CLI): Issue im Chat
  verfeinern, Entwurf übernehmen, per `gh` im Repo anlegen. Das Issue wird in
  TimeTrack dokumentiert und ist im Timer als Buchungsziel wählbar.
- **Historie** 📊 – Einträge nach Zeitraum, Summen pro Projekt und pro Issue,
  Beschreibungen editierbar, Fehlbuchungen löschbar.
- **Systemcheck** ℹ️ – prüft Datenbank, `gh` und `claude` und zeigt für alles
  Fehlende die passenden Befehle.
- **Keine Credentials in der App** – DB-Passwort verschlüsselt im
  macOS-Schlüsselbund, GitHub/Claude über die lokalen CLI-Logins des Nutzers.

## Voraussetzungen

| Komponente | Zweck | Installation |
|---|---|---|
| macOS auf Apple Silicon | App-Bundle ist arm64 | – |
| PostgreSQL | Speicher für Zeiten & Notizen (erforderlich) | `brew install postgresql@17` |
| GitHub CLI `gh` | Issues anlegen (optional) | `brew install gh && gh auth login` |
| Claude Code `claude` | Issue-Assistent (optional) | `brew install --cask claude-code` |
| Python ≥ 3.12 | nur für den Start aus dem Quellcode | – |

## Schnellstart (fertiges App-Bundle)

1. Zip aus den [Releases](https://github.com/insanejules/timetrack/releases)
   laden, entpacken, `TimeTrack.app` nach „Programme“ ziehen.
2. Gatekeeper einmalig freigeben: *Systemeinstellungen → Datenschutz &
   Sicherheit → „Dennoch öffnen“* (die App ist nicht Apple-signiert).
3. Datenbank anlegen:

   ```sh
   brew services start postgresql@17
   /opt/homebrew/opt/postgresql@17/bin/createdb timetrack
   ```

4. App starten – der Einrichtungs-Dialog fragt die DB-Verbindung ab, der
   Systemcheck zeigt, ob alles bereit ist. Die Tabellen legt die App selbst an.

Details für Empfänger ohne Terminal-Erfahrung: [`packaging/Anleitung.txt`](packaging/Anleitung.txt).

## Start aus dem Quellcode

```sh
git clone https://github.com/insanejules/timetrack.git && cd timetrack
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m timetrack        # oder: ./TimeTrack.command
```

## App-Bundle bauen

```sh
./build_app.sh
```

Baut mit PyInstaller `dist/TimeTrack.app` (inkl. Icon und Version in der
Info.plist) und packt es mit der Anleitung nach `dist/TimeTrack-Versand.zip`.

## Konfiguration & Credentials

- Einstellungen über ⚙️ im Widget (Host, Port, Datenbank, Benutzer, Passwort,
  „Verbindung testen“). Leere Felder = lokaler Socket bzw. aktueller
  macOS-Benutzer (passend für Homebrew-Postgres).
- Host/Port/DB/Benutzer liegen in den macOS-Preferences
  (`~/Library/Preferences/com.timetrack.TimeTrack.plist`), das Passwort
  **ausschließlich verschlüsselt im macOS-Schlüsselbund** (Service
  „TimeTrack“). Nichts davon ist Teil der App oder des Repos.
- Die Umgebungsvariable `TIMETRACK_DB` (libpq-Verbindungsstring) überschreibt
  bei Bedarf alles.

## Auswertung per SQL

Die View `time_report` liefert fertige Zeilen mit Dauer, Projekt, Kunde und
Issue:

```sql
-- Stunden pro Projekt im aktuellen Monat
SELECT project, customer,
       round(EXTRACT(EPOCH FROM sum(duration)) / 3600, 2) AS hours
FROM time_report
WHERE started_at >= date_trunc('month', now())
GROUP BY project, customer
ORDER BY hours DESC;
```

## Projektstruktur

```
timetrack/
├── timetrack/           # App-Code (PySide6)
│   ├── tracker.py       # Timer-Widget (Hauptfenster)
│   ├── knowledge.py     # Knowledgebase (Notizen, Kunden)
│   ├── issue.py         # Issue-Dialog: Claude-Session + gh
│   ├── history.py       # Historie & Auswertung
│   ├── onboarding.py    # Systemcheck & Erste Schritte
│   ├── settings.py      # Einstellungen, Keychain
│   ├── tray.py          # Menüleisten-Icon
│   └── db.py            # Schema & alle Queries (psycopg)
├── packaging/           # Launcher, Icon-Generator, Anleitung
└── build_app.sh         # PyInstaller-Build + Versand-Zip
```

## Versionierung

Das Projekt folgt [Semantic Versioning](https://semver.org/lang/de/): Die
Versionsnummer steht zentral in `timetrack/__init__.py`, jede Version ist als
Git-Tag `vX.Y.Z` markiert und in [`CHANGELOG.md`](CHANGELOG.md) dokumentiert;
Releases mit fertigem App-Bundle liegen unter
[Releases](https://github.com/insanejules/timetrack/releases).
