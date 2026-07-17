"""Issue-Erstellung aus einer Notiz: eingebettete Claude-Code-Session + gh.

Ablauf: Die Notiz wird als Startprompt an das lokale claude-CLI (Headless-Modus,
``claude -p --output-format json``) übergeben. Der Nutzer verfeinert das Issue im
Chat, „Entwurf übernehmen“ lässt Claude den finalen Titel + Body in festem Format
ausgeben, „Auf GitHub erstellen“ legt das Issue per gh-CLI an und dokumentiert es
in der TimeTrack-Datenbank.
"""

import json
import os
import re
import shutil
import tempfile

from PySide6.QtCore import QProcess, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

SESSION_DIR = os.path.expanduser(
    "~/Library/Application Support/TimeTrack/claude-sessions")

# GUI-Apps aus dem Finder haben einen minimalen PATH – bekannte Orte ergänzen
TOOL_PATHS = ["/opt/homebrew/bin", "/usr/local/bin",
              os.path.expanduser("~/.local/bin")]


def find_tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for directory in TOOL_PATHS:
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


SEED_PROMPT = """\
Du hilfst mir, aus einer Notiz ein gutes GitHub-Issue zu formulieren.

Notiz-Titel: {title}
Notiz-Inhalt:
{body}

Schlage ein Issue vor (prägnanter Titel, strukturierter Markdown-Body mit
Kontext, ggf. Akzeptanzkriterien). Stelle mir Rückfragen, wenn etwas unklar
ist. Antworte auf Deutsch und fasse dich kompakt – reine Textarbeit, du musst
keine Dateien lesen oder Tools benutzen."""

FINALIZE_PROMPT = """\
Gib jetzt ausschließlich das finale Issue aus, exakt in diesem Format ohne
weitere Kommentare:

TITEL: <einzeiliger Issue-Titel>

<Markdown-Body des Issues>"""


class IssueDialog(QDialog):
    def __init__(self, db, project: dict, note: dict, parent=None):
        super().__init__(parent)
        self.db = db
        self.project = project
        self.note = note
        self.session_id: str | None = None
        self.proc: QProcess | None = None
        self._repo_proc: QProcess | None = None
        self.created_issue: dict | None = None
        self._transcript: list[str] = []

        self.setWindowTitle(f"Issue erstellen – {project['name']}")
        self.resize(760, 640)

        # -- oben: Repo (eigene Repos werden per gh geladen, Freitext möglich) --
        self.repo_edit = QComboBox()
        self.repo_edit.setEditable(True)
        self.repo_edit.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.repo_edit.lineEdit().setPlaceholderText(
            "owner/repo  (z. B. firma/projekt)")
        self.repo_edit.setCurrentText(project.get("github_repo") or "")
        repo_row = QHBoxLayout()
        repo_row.addWidget(QLabel("GitHub-Repo:"))
        repo_row.addWidget(self.repo_edit, 1)
        self._load_repos()

        # -- Chat mit Claude --
        self.chat_view = QTextBrowser()
        self.chat_view.setOpenExternalLinks(True)

        self.chat_input = QPlainTextEdit()
        self.chat_input.setPlaceholderText(
            "Nachricht an Claude … (z. B. „mach den Titel kürzer“)")
        self.chat_input.setMaximumHeight(70)
        self.send_btn = QPushButton("Senden")
        self.send_btn.clicked.connect(self._send_message)
        self.finalize_btn = QPushButton("Entwurf übernehmen ⬇")
        self.finalize_btn.setToolTip(
            "Claude gibt den finalen Titel + Body aus, die Felder unten werden gefüllt")
        self.finalize_btn.clicked.connect(self._finalize)

        input_row = QHBoxLayout()
        input_row.addWidget(self.chat_input, 1)
        buttons_col = QVBoxLayout()
        buttons_col.addWidget(self.send_btn)
        buttons_col.addWidget(self.finalize_btn)
        input_row.addLayout(buttons_col)

        chat_widget = QWidget()
        chat_layout = QVBoxLayout(chat_widget)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.addWidget(self.chat_view, 1)
        chat_layout.addLayout(input_row)

        # -- unten: finales Issue --
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Issue-Titel (aus Entwurf oder manuell)")
        self.body_edit = QPlainTextEdit()
        self.body_edit.setPlaceholderText("Issue-Body (Markdown)")

        self.create_btn = QPushButton("Issue auf GitHub erstellen")
        self.create_btn.clicked.connect(self._create_on_github)

        final_widget = QWidget()
        final_layout = QVBoxLayout(final_widget)
        final_layout.setContentsMargins(0, 0, 0, 0)
        final_layout.addWidget(self.title_edit)
        final_layout.addWidget(self.body_edit, 1)
        final_layout.addWidget(self.create_btn)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.addWidget(chat_widget)
        splitter.addWidget(final_widget)
        splitter.setSizes([400, 240])

        layout = QVBoxLayout(self)
        layout.addLayout(repo_row)
        layout.addWidget(splitter)

        self._start_session()

    # ---- Claude-Session -------------------------------------------------

    def _append(self, who: str, text: str):
        self._transcript.append(f"**{who}:**\n\n{text}")
        self.chat_view.setMarkdown("\n\n---\n\n".join(self._transcript))
        self.chat_view.verticalScrollBar().setValue(
            self.chat_view.verticalScrollBar().maximum())

    def _start_session(self):
        seed = SEED_PROMPT.format(
            title=self.note.get("title") or "(ohne Titel)",
            body=self.note.get("body") or "(leer)")
        self._append("Du", f"*Notiz „{self.note.get('title') or '(ohne Titel)'}“ "
                           "an Claude übergeben – Issue-Entwurf angefragt.*")
        self._run_claude(seed)

    def _send_message(self):
        text = self.chat_input.toPlainText().strip()
        if not text or self.proc is not None:
            return
        self.chat_input.clear()
        self._append("Du", text)
        self._run_claude(text)

    def _finalize(self):
        if self.proc is not None:
            return
        self._append("Du", "*Finalen Entwurf angefordert …*")
        self._run_claude(FINALIZE_PROMPT, finalize=True)

    def _run_claude(self, prompt: str, finalize: bool = False):
        claude = find_tool("claude")
        if claude is None:
            QMessageBox.critical(
                self, "claude nicht gefunden",
                "Das claude-CLI wurde nicht gefunden. Installation:\n"
                "  brew install --cask claude-code")
            return
        os.makedirs(SESSION_DIR, exist_ok=True)

        args = ["-p", "--output-format", "json"]
        if self.session_id:
            args += ["--resume", self.session_id]
        args.append(prompt)

        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(SESSION_DIR)
        self.proc.finished.connect(
            lambda code, status: self._claude_done(code, finalize))
        self._set_busy(True)
        self.proc.start(claude, args)

    def _claude_done(self, exit_code: int, finalize: bool):
        stdout = bytes(self.proc.readAllStandardOutput()).decode("utf-8", "replace")
        stderr = bytes(self.proc.readAllStandardError()).decode("utf-8", "replace")
        self.proc = None
        self._set_busy(False)

        result_text, error = self._parse_result(exit_code, stdout, stderr)
        if error:
            self._append("Fehler", error)
            return

        if finalize:
            title, body = self._parse_final_issue(result_text)
            if title:
                self.title_edit.setText(title)
                self.body_edit.setPlainText(body)
                self._append("Claude", "*Entwurf unten übernommen – bei Bedarf "
                                       "anpassen und auf GitHub erstellen.*")
            else:
                self._append("Claude", result_text)
        else:
            self._append("Claude", result_text)

    def _parse_result(self, exit_code: int, stdout: str, stderr: str):
        try:
            events = json.loads(stdout)
            result = next(
                e for e in reversed(events)
                if isinstance(e, dict) and e.get("type") == "result")
        except (json.JSONDecodeError, StopIteration):
            detail = stderr.strip() or stdout.strip()[:500] or f"Exit-Code {exit_code}"
            return None, f"claude-Aufruf fehlgeschlagen:\n\n```\n{detail}\n```"
        if result.get("is_error"):
            return None, f"Claude meldet einen Fehler:\n\n{result.get('result', '')}"
        self.session_id = result.get("session_id", self.session_id)
        return result.get("result", ""), None

    @staticmethod
    def _parse_final_issue(text: str) -> tuple[str | None, str]:
        match = re.search(r"^TITEL:\s*(.+)$", text, re.MULTILINE)
        if not match:
            return None, ""
        title = match.group(1).strip()
        body = text[match.end():].strip()
        return title, body

    def _set_busy(self, busy: bool):
        for widget in (self.send_btn, self.finalize_btn, self.create_btn,
                       self.chat_input):
            widget.setEnabled(not busy)
        if busy:
            self.chat_view.setMarkdown(
                "\n\n---\n\n".join(self._transcript + ["*Claude arbeitet …*"]))
            self.chat_view.verticalScrollBar().setValue(
                self.chat_view.verticalScrollBar().maximum())

    # ---- GitHub ---------------------------------------------------------

    def _load_repos(self):
        """Eigene GitHub-Repos als Dropdown-Vorschläge laden (asynchron)."""
        gh = find_tool("gh")
        if gh is None:
            return
        self._repo_proc = QProcess(self)
        self._repo_proc.finished.connect(lambda *_: self._repos_loaded())
        self._repo_proc.start(gh, ["repo", "list", "--limit", "200",
                                   "--json", "nameWithOwner", "-q", ".[].nameWithOwner"])

    def _repos_loaded(self):
        try:
            proc = self._repo_proc
            stdout = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
        except RuntimeError:  # Dialog wurde geschlossen, bevor gh fertig war
            return
        self._repo_proc = None
        repos = [line.strip() for line in stdout.splitlines() if "/" in line]
        if not repos:
            return
        current = self.repo_edit.currentText()
        self.repo_edit.blockSignals(True)
        self.repo_edit.clear()
        self.repo_edit.addItems(sorted(repos))
        completer = QCompleter(sorted(repos), self.repo_edit)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.repo_edit.setCompleter(completer)
        self.repo_edit.setCurrentText(current)
        self.repo_edit.blockSignals(False)

    def _create_on_github(self):
        repo = self.repo_edit.currentText().strip()
        title = self.title_edit.text().strip()
        body = self.body_edit.toPlainText().strip()

        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
            QMessageBox.warning(self, "Repo fehlt",
                                "Bitte das GitHub-Repo als „owner/repo“ angeben.")
            return
        if not title:
            QMessageBox.warning(self, "Titel fehlt",
                                "Bitte zuerst einen Issue-Titel eintragen "
                                "(„Entwurf übernehmen“ oder manuell).")
            return

        gh = find_tool("gh")
        if gh is None:
            QMessageBox.critical(
                self, "gh nicht gefunden",
                "Das GitHub-CLI wurde nicht gefunden. Installation:\n"
                "  brew install gh && gh auth login")
            return

        with tempfile.NamedTemporaryFile(
                "w", suffix=".md", delete=False, encoding="utf-8") as tmp:
            tmp.write(body or "(kein Body)")
            body_file = tmp.name

        self.create_btn.setEnabled(False)
        proc = QProcess(self)
        proc.finished.connect(
            lambda code, status: self._github_done(proc, code, repo, title, body_file))
        proc.start(gh, ["issue", "create", "-R", repo,
                        "--title", title, "--body-file", body_file])

    def _github_done(self, proc: QProcess, exit_code: int, repo: str,
                     title: str, body_file: str):
        stdout = bytes(proc.readAllStandardOutput()).decode("utf-8", "replace")
        stderr = bytes(proc.readAllStandardError()).decode("utf-8", "replace")
        self.create_btn.setEnabled(True)
        os.unlink(body_file)

        url_match = re.search(r"https://github\.com/\S+/issues/(\d+)", stdout)
        if exit_code != 0 or not url_match:
            QMessageBox.critical(
                self, "GitHub-Fehler",
                f"gh issue create ist fehlgeschlagen:\n\n{stderr.strip() or stdout.strip()}")
            return

        url = url_match.group(0)
        number = int(url_match.group(1))
        issue_id = self.db.create_issue(
            project_id=self.project["id"], note_id=self.note.get("id"),
            repo=repo, number=number, title=title, url=url)
        self.db.set_project_repo(self.project["id"], repo)
        self.created_issue = {"id": issue_id, "repo": repo, "number": number,
                              "title": title, "url": url}
        QMessageBox.information(
            self, "Issue erstellt",
            f"Issue #{number} wurde angelegt und in TimeTrack dokumentiert:\n\n{url}\n\n"
            "Im Timer-Widget kannst du Arbeitszeit jetzt direkt auf dieses "
            "Issue buchen.")
        self.accept()

    def closeEvent(self, event):
        for proc in (self.proc, self._repo_proc):
            if proc is not None:
                proc.kill()
                proc.waitForFinished(1000)
        self.proc = None
        self._repo_proc = None
        event.accept()
