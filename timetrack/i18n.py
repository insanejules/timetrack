"""Zwei-Sprachen-Unterstützung: Deutsch ist Quellsprache, Englisch Übersetzung.

Alle UI-Texte laufen durch ``tr()``. Steht die Sprache auf Englisch, wird der
deutsche Text im ``EN``-Wörterbuch nachgeschlagen; fehlende Einträge fallen
sichtbar auf Deutsch zurück. Die Auswahl (system/de/en) liegt in QSettings und
wird beim App-Start ausgewertet – ein Wechsel greift nach einem Neustart.
"""

from PySide6.QtCore import QLocale, QSettings

from . import APP, ORG

_active: str | None = None


def stored_language() -> str:
    """Gespeicherte Auswahl: "system", "de" oder "en"."""
    value = str(QSettings(ORG, APP).value("ui/language", "system"))
    return value if value in ("system", "de", "en") else "system"


def set_stored_language(value: str):
    settings = QSettings(ORG, APP)
    settings.setValue("ui/language", value)
    settings.sync()
    global _active
    _active = None


def language() -> str:
    """Aktive Sprache ("de"/"en"), bei "system" anhand der macOS-Sprache."""
    global _active
    if _active is None:
        stored = stored_language()
        if stored in ("de", "en"):
            _active = stored
        else:
            _active = "de" if QLocale.system().name().lower().startswith("de") else "en"
    return _active


def tr(text: str) -> str:
    if language() == "de":
        return text
    return EN.get(text, text)


EN = {
    # ---- tracker.py ----
    "Projekt…": "Project…",
    "Beschreibung…": "Description…",
    "▶  Start": "▶  Start",
    "⏹  Stop": "⏹  Stop",
    "Knowledgebase (Notizen zu Kunden & Projekten)":
        "Knowledge base (notes on customers & projects)",
    "Historie & Auswertung": "History & reports",
    "Einstellungen (Datenbank-Verbindung)": "Settings (database connection)",
    "Systemcheck & Erste Schritte": "System check & getting started",
    "Fenster immer im Vordergrund halten": "Keep window always on top",
    "Optional: Arbeitszeit direkt auf ein GitHub-Issue buchen":
        "Optional: log work time directly on a GitHub issue",
    "— kein Issue —": "— no issue —",
    "Heute gesamt: {}": "Today's total: {}",
    "Bitte zuerst ein Projekt angeben.": "Please enter a project first.",
    "Bitte zuerst den laufenden Timer stoppen – während ein Eintrag läuft, "
    "kann die Datenbankverbindung nicht gewechselt werden.":
        "Please stop the running timer first – the database connection cannot "
        "be changed while an entry is running.",
    "Timer läuft noch": "Timer still running",
    "Der Timer läuft noch. Was soll passieren?":
        "The timer is still running. What should happen?",
    "Stoppen && speichern": "Stop && save",
    "Weiterlaufen lassen": "Keep running",
    "Abbrechen": "Cancel",

    # ---- knowledge.py ----
    "TimeTrack – Knowledgebase": "TimeTrack – Knowledge base",
    "+ Kunde": "+ Customer",
    "+ Notiz": "+ Note",
    "Löschen": "Delete",
    "Wähle links einen Kunden oder ein Projekt.":
        "Select a customer or project on the left.",
    "Kunde": "Customer",
    "Projekt": "Project",
    "Kunde:": "Customer:",
    "— kein Kunde —": "— no customer —",
    "— ohne Kunde —": "— without customer —",
    "Titel der Notiz…": "Note title…",
    "Notiz…": "Note…",
    "(ohne Titel)": "(untitled)",
    "Geändert: {}": "Modified: {}",
    "Neuer Kunde": "New customer",
    "Name des Kunden:": "Customer name:",
    "Neue Notiz": "New note",
    "Notiz löschen": "Delete note",
    "Diese Notiz wirklich löschen?": "Really delete this note?",
    "Änderungen an der Notiz speichern (⌘S)":
        "Save changes to the note (⌘S)",
    "Ungespeicherte Änderungen": "Unsaved changes",
    "Die Notiz hat ungespeicherte Änderungen. Sollen sie gespeichert werden?":
        "This note has unsaved changes. Do you want to save them?",
    "Verwerfen": "Discard",
    "Issue aus Notiz erstellen (mit Claude)…":
        "Create issue from note (with Claude)…",
    "Öffnet eine Claude-Code-Session, die aus dieser Notiz ein GitHub-Issue "
    "formuliert":
        "Opens a Claude Code session that turns this note into a GitHub issue",
    "Issues brauchen ein Projekt – diese Notiz hängt an einem Kunden":
        "Issues need a project – this note belongs to a customer",

    # ---- history.py ----
    "TimeTrack – Historie": "TimeTrack – History",
    "Heute": "Today",
    "Diese Woche": "This week",
    "Dieser Monat": "This month",
    "Alles": "All",
    "Zeitraum:": "Period:",
    "Aktualisieren": "Refresh",
    "Datum": "Date",
    "Zeit": "Time",
    "Dauer": "Duration",
    "Issue": "Issue",
    "Beschreibung": "Description",
    "läuft": "running",
    "Gesamt: {}": "Total: {}",
    "Ausgewählte löschen": "Delete selected",
    "Einträge": "Entries",
    "Pro Projekt": "Per project",
    "Pro Issue": "Per issue",
    "Summe": "Total",
    "Einträge löschen": "Delete entries",
    "{} Eintrag/Einträge wirklich löschen?": "Really delete {} entry/entries?",

    # ---- settings.py ----
    "TimeTrack – Einrichtung": "TimeTrack – Setup",
    "TimeTrack – Einstellungen": "TimeTrack – Settings",
    "<b>Willkommen bei TimeTrack!</b><br>Richte einmalig die Verbindung zu "
    "deiner PostgreSQL-Datenbank ein. Für einen lokalen Homebrew-Postgres "
    "passen die Vorgaben – einfach „Verbindung testen“ und dann „Speichern“.":
        "<b>Welcome to TimeTrack!</b><br>Set up the connection to your "
        "PostgreSQL database once. For a local Homebrew Postgres the defaults "
        "are fine – just click “Test connection” and then “Save”.",
    "leer = lokaler Socket (Homebrew-Postgres)":
        "empty = local socket (Homebrew Postgres)",
    "leer = aktueller macOS-Benutzer": "empty = current macOS user",
    "leer = kein Passwort": "empty = no password",
    "Host:": "Host:",
    "Port:": "Port:",
    "Datenbank:": "Database:",
    "Benutzer:": "User:",
    "Passwort:": "Password:",
    "Sprache / Language:": "Language:",
    "System (automatisch)": "System (automatic)",
    "Verbindung: {}": "Connection: {}",
    "⚠️ Die Umgebungsvariable TIMETRACK_DB ist gesetzt und überschreibt diese "
    "Einstellungen beim nächsten Start.":
        "⚠️ The environment variable TIMETRACK_DB is set and overrides these "
        "settings on the next start.",
    "Das Passwort wird verschlüsselt im macOS-Schlüsselbund (Keychain) "
    "gespeichert – nie in der App oder in Konfigurationsdateien. Für den "
    "lokalen Homebrew-Postgres ist keins nötig.":
        "The password is stored encrypted in the macOS Keychain – never in "
        "the app or in configuration files. The local Homebrew Postgres does "
        "not need one.",
    "Verbindung testen": "Test connection",
    "Speichern": "Save",
    "Verbindung OK": "Connection OK",
    "Verbindung erfolgreich:\n\n{}": "Connection successful:\n\n{}",
    "Verbindung fehlgeschlagen": "Connection failed",
    "Keine Verbindung möglich:\n\n{}": "Could not connect:\n\n{}",
    "Die neue Verbindung konnte nicht aufgebaut werden – die bisherige bleibt "
    "aktiv:\n\n{}":
        "The new connection could not be established – the previous one "
        "remains active:\n\n{}",
    "Sprache geändert": "Language changed",
    "Die Sprachänderung gilt nach einem Neustart von TimeTrack.":
        "The language change takes effect after restarting TimeTrack.",

    # ---- tray.py ----
    "Kein Timer aktiv": "No timer running",
    "Widget anzeigen": "Show widget",
    "Systemcheck && Anleitung…": "System check && guide…",
    "Timer stoppen && speichern": "Stop timer && save",
    "☕ Einen Kaffee spendieren…": "☕ Buy me a coffee…",
    "TimeTrack beenden": "Quit TimeTrack",
    "Version {}": "Version {}",
    "Läuft: {}": "Running: {}",
    "TimeTrack – {}": "TimeTrack – {}",
    "TimeTrack – kein Timer aktiv": "TimeTrack – no timer running",

    # ---- onboarding.py ----
    "TimeTrack – Systemcheck & Erste Schritte":
        "TimeTrack – System check & getting started",
    "Damit alle Funktionen von TimeTrack laufen, braucht dein Mac die "
    "folgenden Dinge. Die Zeiterfassung selbst funktioniert schon mit der "
    "Datenbank – GitHub- und Claude-Integration sind optional.":
        "For all TimeTrack features your Mac needs the following. Time "
        "tracking itself only needs the database – the GitHub and Claude "
        "integrations are optional.",
    "PostgreSQL-Datenbank": "PostgreSQL database",
    "erforderlich – hier landen alle Zeiten und Notizen":
        "required – all times and notes are stored here",
    "GitHub-CLI (gh)": "GitHub CLI (gh)",
    "optional – nur für „Issue aus Notiz erstellen“":
        "optional – only for “Create issue from note”",
    "Claude Code (claude)": "Claude Code (claude)",
    "optional – nur für den Issue-Assistenten":
        "optional – only for the issue assistant",
    "Keine Verbindung konfiguriert.": "No connection configured.",
    "Verbindung gestört: {}": "Connection problem: {}",
    "Verbunden ({}).": "Connected ({}).",
    "GitHub-CLI (gh) ist nicht installiert.":
        "The GitHub CLI (gh) is not installed.",
    "gh gefunden, Status nicht prüfbar (Timeout).":
        "gh found, status could not be checked (timeout).",
    "gh ist installiert, aber nicht angemeldet.":
        "gh is installed but not logged in.",
    "Installiert und angemeldet als {}.": "Installed and logged in as {}.",
    "Installiert und angemeldet.": "Installed and logged in.",
    "Claude Code (claude) ist nicht installiert.":
        "Claude Code (claude) is not installed.",
    "Installiert – der Login erfolgt beim ersten Aufruf.":
        "Installed – login happens on first use.",
    "claude   # einmal starten und anmelden":
        "claude   # start once and log in",
    "Hinweis: TimeTrack speichert keine Zugangsdaten. Das DB-Passwort liegt "
    "verschlüsselt in deinem macOS-Schlüsselbund, GitHub und Claude nutzen "
    "deine lokalen CLI-Logins.":
        "Note: TimeTrack stores no credentials. The database password lives "
        "encrypted in your macOS Keychain; GitHub and Claude use your local "
        "CLI logins.",
    "Gefällt dir TimeTrack? <a href=\"{}\">☕ Buy me a coffee</a>":
        "Enjoying TimeTrack? <a href=\"{}\">☕ Buy me a coffee</a>",
    "Erneut prüfen": "Check again",
    "Schließen": "Close",

    # ---- issue.py ----
    "Issue erstellen – {}": "Create issue – {}",
    "owner/repo  (z. B. firma/projekt)": "owner/repo  (e.g. company/project)",
    "GitHub-Repo:": "GitHub repo:",
    "Nachricht an Claude … (z. B. „mach den Titel kürzer“)":
        "Message to Claude … (e.g. “make the title shorter”)",
    "Senden": "Send",
    "Entwurf übernehmen ⬇": "Adopt draft ⬇",
    "Claude gibt den finalen Titel + Body aus, die Felder unten werden "
    "gefüllt":
        "Claude outputs the final title + body and fills the fields below",
    "Issue-Titel (aus Entwurf oder manuell)": "Issue title (from draft or manual)",
    "Issue-Body (Markdown)": "Issue body (Markdown)",
    "Issue auf GitHub erstellen": "Create issue on GitHub",
    "Du": "You",
    "Fehler": "Error",
    "*Claude arbeitet …*": "*Claude is working …*",
    "*Notiz „{}“ an Claude übergeben – Issue-Entwurf angefragt.*":
        "*Note “{}” handed to Claude – issue draft requested.*",
    "*Finalen Entwurf angefordert …*": "*Final draft requested …*",
    "*Entwurf unten übernommen – bei Bedarf anpassen und auf GitHub "
    "erstellen.*":
        "*Draft adopted below – adjust if needed and create it on GitHub.*",
    "claude nicht gefunden": "claude not found",
    "Das claude-CLI wurde nicht gefunden. Installation:\n"
    "  brew install --cask claude-code":
        "The claude CLI was not found. Install it with:\n"
        "  brew install --cask claude-code",
    "claude-Aufruf fehlgeschlagen:\n\n```\n{}\n```":
        "claude call failed:\n\n```\n{}\n```",
    "Claude meldet einen Fehler:\n\n{}": "Claude reports an error:\n\n{}",
    "Repo fehlt": "Repo missing",
    "Bitte das GitHub-Repo als „owner/repo“ angeben.":
        "Please specify the GitHub repo as “owner/repo”.",
    "Titel fehlt": "Title missing",
    "Bitte zuerst einen Issue-Titel eintragen („Entwurf übernehmen“ oder "
    "manuell).":
        "Please enter an issue title first (“Adopt draft” or manually).",
    "gh nicht gefunden": "gh not found",
    "Das GitHub-CLI wurde nicht gefunden. Installation:\n"
    "  brew install gh && gh auth login":
        "The GitHub CLI was not found. Install it with:\n"
        "  brew install gh && gh auth login",
    "GitHub-Fehler": "GitHub error",
    "gh issue create ist fehlgeschlagen:\n\n{}":
        "gh issue create failed:\n\n{}",
    "Issue erstellt": "Issue created",
    "Issue #{} wurde angelegt und in TimeTrack dokumentiert:\n\n{}\n\nIm "
    "Timer-Widget kannst du Arbeitszeit jetzt direkt auf dieses Issue buchen.":
        "Issue #{} was created and documented in TimeTrack:\n\n{}\n\nIn the "
        "timer widget you can now log work time directly on this issue.",
    "(kein Body)": "(no body)",
    "(leer)": "(empty)",

    # ---- Claude-Prompts (issue.py) ----
    "SEED_PROMPT":
        "You help me turn a note into a good GitHub issue.\n\n"
        "Note title: {title}\n"
        "Note content:\n{body}\n\n"
        "Propose an issue (concise title, well-structured Markdown body with "
        "context and acceptance criteria where useful). Ask me questions if "
        "anything is unclear. Reply in English and keep it compact – this is "
        "pure text work, you do not need to read files or use tools.",
    "FINALIZE_PROMPT":
        "Now output ONLY the final issue, exactly in this format and without "
        "any further comments:\n\n"
        "TITLE: <one-line issue title>\n\n"
        "<Markdown body of the issue>",

    # ---- __main__.py ----
    "TimeTrack – Datenbankfehler": "TimeTrack – Database error",
    "Konnte keine Verbindung zur Postgres-Datenbank aufbauen:\n\n{}\n\nLäuft "
    "Postgres? Im nächsten Dialog kannst du die Verbindung anpassen.":
        "Could not connect to the Postgres database:\n\n{}\n\nIs Postgres "
        "running? You can adjust the connection in the next dialog.",
}
