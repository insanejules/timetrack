<p align="center">
  <img src="docs/icon.png" width="120" alt="TimeTrack icon">
</p>

<h1 align="center">TimeTrack</h1>

<p align="center">
  <a href="README.md">🇩🇪 Deutsch</a>&nbsp;·&nbsp;🇬🇧 English
</p>

<p align="center">
  A small time-tracking widget for macOS – with a PostgreSQL backend,
  knowledge base and a GitHub issue workflow powered by Claude Code.
</p>

<p align="center">
  <a href="https://buymeacoffee.com/insanejules"><img src="https://img.shields.io/badge/Buy%20me%20a%20coffee-%E2%98%95-FFDD00?logo=buymeacoffee&logoColor=black" alt="Buy Me a Coffee"></a>
</p>

---

## What is TimeTrack?

Type a project, start the timer, done: TimeTrack is a compact Qt widget
(PySide6) that writes working hours into a PostgreSQL database. On top of
that there is a small knowledge base for notes on customers and projects, a
reporting history – and a workflow that turns a note into a GitHub issue
together with Claude, so you can log work time directly on that issue.

## Features

- **Timer widget** – project field with suggestions from previously tracked
  projects, free-text description, start/stop, daily total. 📌 keeps the
  window on top.
- **Crash-safe** – running entries are written to the database immediately
  and resume seamlessly after a restart.
- **Menu bar app** – closing the window quits nothing: TimeTrack keeps
  running as a clock icon in the menu bar (status, stop, quit).
- **Knowledge base** 📓 – notes per customer or project, projects can be
  assigned to customers; auto-save.
- **GitHub issues with Claude** – “Create issue from note” opens an embedded
  Claude Code session (local `claude` CLI): refine the issue in a chat,
  adopt the draft, create it in the repo via `gh`. The issue is documented
  in TimeTrack and selectable as a booking target in the timer.
- **History** 📊 – entries by period, totals per project and per issue,
  editable descriptions, deletable entries.
- **System check** ℹ️ – verifies database, `gh` and `claude` and shows the
  right commands for anything missing.
- **No credentials in the app** – database password encrypted in the macOS
  Keychain; GitHub/Claude use the user's local CLI logins.
- **Bilingual** – the app follows the macOS language (German/English),
  switchable in the settings (⚙️ → Language); guides ship in both languages.

## Requirements

| Component | Purpose | Installation |
|---|---|---|
| macOS on Apple Silicon | app bundle is arm64 | – |
| PostgreSQL | storage for times & notes (required) | `brew install postgresql@17` |
| GitHub CLI `gh` | create issues (optional) | `brew install gh && gh auth login` |
| Claude Code `claude` | issue assistant (optional) | `brew install --cask claude-code` |
| Python ≥ 3.12 | only for running from source | – |

## Quick start (prebuilt app bundle)

1. Download the zip from the
   [releases](https://github.com/insanejules/timetrack/releases), unzip it
   and drag `TimeTrack.app` into “Applications”.
2. Allow the app once in Gatekeeper: *System Settings → Privacy & Security →
   “Open Anyway”* (the app is not Apple-signed).
3. Create the database:

   ```sh
   brew services start postgresql@17
   /opt/homebrew/opt/postgresql@17/bin/createdb timetrack
   ```

4. Start the app – the setup dialog asks for the database connection and the
   system check shows whether everything is ready. The app creates its
   tables itself.

Details for recipients without terminal experience:
[`packaging/Instructions.txt`](packaging/Instructions.txt).

## Running from source

```sh
git clone https://github.com/insanejules/timetrack.git && cd timetrack
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m timetrack        # or: ./TimeTrack.command
```

## Building the app bundle

```sh
./build_app.sh
```

Builds `dist/TimeTrack.app` with PyInstaller (including icon and version in
the Info.plist) and packs it together with both guides into
`dist/TimeTrack-Versand.zip`.

## Configuration & credentials

- Settings via ⚙️ in the widget (host, port, database, user, password,
  “Test connection”, language). Empty fields = local socket / current macOS
  user (matching Homebrew Postgres).
- Host/port/database/user live in the macOS preferences
  (`~/Library/Preferences/com.timetrack.TimeTrack.plist`); the password is
  stored **exclusively encrypted in the macOS Keychain** (service
  “TimeTrack”). None of this is part of the app or the repo.
- The environment variable `TIMETRACK_DB` (libpq connection string)
  overrides everything if needed.

## Reporting via SQL

The `time_report` view provides ready-made rows with duration, project,
customer and issue:

```sql
-- hours per project in the current month
SELECT project, customer,
       round(EXTRACT(EPOCH FROM sum(duration)) / 3600, 2) AS hours
FROM time_report
WHERE started_at >= date_trunc('month', now())
GROUP BY project, customer
ORDER BY hours DESC;
```

## Project structure

```
timetrack/
├── timetrack/           # app code (PySide6)
│   ├── tracker.py       # timer widget (main window)
│   ├── knowledge.py     # knowledge base (notes, customers)
│   ├── issue.py         # issue dialog: Claude session + gh
│   ├── history.py       # history & reports
│   ├── onboarding.py    # system check & getting started
│   ├── settings.py      # settings, Keychain
│   ├── i18n.py          # German/English translations
│   ├── tray.py          # menu bar icon
│   └── db.py            # schema & all queries (psycopg)
├── packaging/           # launcher, icon generator, guides (DE/EN)
└── build_app.sh         # PyInstaller build + distribution zip
```

## Support

TimeTrack is a spare-time project. If it makes your workday easier, I would
be happy about a coffee: ☕
[buymeacoffee.com/insanejules](https://buymeacoffee.com/insanejules)

## Versioning

The project follows [Semantic Versioning](https://semver.org/): the version
number lives in `timetrack/__init__.py`, every version is marked with a git
tag `vX.Y.Z` and documented in [`CHANGELOG.md`](CHANGELOG.md); releases with
a prebuilt app bundle are available under
[Releases](https://github.com/insanejules/timetrack/releases).
