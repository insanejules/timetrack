"""Knowledgebase: Notizen pro Kunde bzw. Projekt, Kunden-Zuordnung."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .db import Database
from .i18n import tr
from .issue import IssueDialog

ROLE_KIND = Qt.ItemDataRole.UserRole        # "customer" | "project"
ROLE_ID = Qt.ItemDataRole.UserRole + 1


class KnowledgeWindow(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.current_note_id: int | None = None
        self._loading = False

        self.setWindowTitle(tr("TimeTrack – Knowledgebase"))
        self.resize(820, 520)

        # -- linke Seite: Kunden/Projekte-Baum --
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.currentItemChanged.connect(self._selection_changed)

        new_customer_btn = QPushButton(tr("+ Kunde"))
        new_customer_btn.clicked.connect(self._new_customer)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.tree)
        left_layout.addWidget(new_customer_btn)

        # -- Mitte: Notizliste --
        self.note_list = QListWidget()
        self.note_list.currentItemChanged.connect(self._note_selected)

        self.new_note_btn = QPushButton(tr("+ Notiz"))
        self.new_note_btn.clicked.connect(self._new_note)
        self.del_note_btn = QPushButton(tr("Löschen"))
        self.del_note_btn.clicked.connect(self._delete_note)

        note_btns = QHBoxLayout()
        note_btns.addWidget(self.new_note_btn)
        note_btns.addWidget(self.del_note_btn)

        middle = QWidget()
        middle_layout = QVBoxLayout(middle)
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.addWidget(self.note_list)
        middle_layout.addLayout(note_btns)

        # -- rechte Seite: Editor --
        self.context_label = QLabel(tr("Wähle links einen Kunden oder ein Projekt."))
        self.context_label.setStyleSheet("font-weight: bold;")

        self.customer_combo = QComboBox()
        self.customer_combo.currentIndexChanged.connect(self._assign_customer)
        self.customer_row = QWidget()
        customer_row_layout = QHBoxLayout(self.customer_row)
        customer_row_layout.setContentsMargins(0, 0, 0, 0)
        customer_row_layout.addWidget(QLabel(tr("Kunde:")))
        customer_row_layout.addWidget(self.customer_combo, 1)
        self.customer_row.hide()

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(tr("Titel der Notiz…"))
        self.body_edit = QPlainTextEdit()
        self.body_edit.setPlaceholderText(tr("Notiz…"))

        self.issue_btn = QPushButton(tr("Issue aus Notiz erstellen (mit Claude)…"))
        self.issue_btn.setToolTip(
            tr("Öffnet eine Claude-Code-Session, die aus dieser Notiz ein "
               "GitHub-Issue formuliert"))
        self.issue_btn.clicked.connect(self._create_issue)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.context_label)
        right_layout.addWidget(self.customer_row)
        right_layout.addWidget(self.title_edit)
        right_layout.addWidget(self.body_edit, 1)
        right_layout.addWidget(self.issue_btn)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(middle)
        splitter.addWidget(right)
        splitter.setSizes([200, 200, 420])

        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        self._set_editor_enabled(False)
        self.reload()

    # ---- Baum -----------------------------------------------------------

    def reload(self):
        self._save_current_note()
        self._loading = True
        self.tree.clear()

        customers = self.db.customers()
        projects = self.db.projects_with_customers()

        customer_items: dict[int, QTreeWidgetItem] = {}
        for c in customers:
            item = QTreeWidgetItem([c["name"]])
            item.setData(0, ROLE_KIND, "customer")
            item.setData(0, ROLE_ID, c["id"])
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            self.tree.addTopLevelItem(item)
            customer_items[c["id"]] = item

        orphan = QTreeWidgetItem([tr("— ohne Kunde —")])
        orphan.setFlags(orphan.flags() & ~Qt.ItemFlag.ItemIsSelectable)

        for p in projects:
            item = QTreeWidgetItem([p["name"]])
            item.setData(0, ROLE_KIND, "project")
            item.setData(0, ROLE_ID, p["id"])
            if p["customer_id"] in customer_items:
                customer_items[p["customer_id"]].addChild(item)
            else:
                orphan.addChild(item)

        if orphan.childCount():
            self.tree.addTopLevelItem(orphan)
        self.tree.expandAll()

        self._reload_customer_combo()
        self._loading = False
        self._selection_changed(self.tree.currentItem(), None)

    def _reload_customer_combo(self):
        self.customer_combo.blockSignals(True)
        self.customer_combo.clear()
        self.customer_combo.addItem(tr("— kein Kunde —"), None)
        for c in self.db.customers():
            self.customer_combo.addItem(c["name"], c["id"])
        self.customer_combo.blockSignals(False)

    def _new_customer(self):
        name, ok = QInputDialog.getText(self, tr("Neuer Kunde"),
                                        tr("Name des Kunden:"))
        if ok and name.strip():
            self.db.ensure_customer(name.strip())
            self.reload()

    def _selection_changed(self, current: QTreeWidgetItem | None, _prev=None):
        if self._loading:
            return
        self._save_current_note()
        self.current_note_id = None

        kind = current.data(0, ROLE_KIND) if current else None
        if kind not in ("customer", "project"):
            self.context_label.setText(tr("Wähle links einen Kunden oder ein Projekt."))
            self.customer_row.hide()
            self.note_list.clear()
            self._set_editor_enabled(False)
            return

        label = tr("Kunde") if kind == "customer" else tr("Projekt")
        self.context_label.setText(f"{label}: {current.text(0)}")

        if kind == "project":
            project = next(
                (p for p in self.db.projects_with_customers()
                 if p["id"] == current.data(0, ROLE_ID)), None)
            self.customer_combo.blockSignals(True)
            idx = self.customer_combo.findData(project["customer_id"] if project else None)
            self.customer_combo.setCurrentIndex(max(0, idx))
            self.customer_combo.blockSignals(False)
            self.customer_row.show()
        else:
            self.customer_row.hide()

        self._reload_notes()

    def _assign_customer(self):
        current = self.tree.currentItem()
        if self._loading or not current or current.data(0, ROLE_KIND) != "project":
            return
        self.db.set_project_customer(
            current.data(0, ROLE_ID), self.customer_combo.currentData())
        project_id = current.data(0, ROLE_ID)
        self.reload()
        self._select_project(project_id)

    def _select_project(self, project_id: int):
        for item in self.tree.findItems("", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchRecursive):
            if item.data(0, ROLE_KIND) == "project" and item.data(0, ROLE_ID) == project_id:
                self.tree.setCurrentItem(item)
                return

    # ---- Notizen --------------------------------------------------------

    def _current_target(self) -> dict | None:
        item = self.tree.currentItem()
        if not item:
            return None
        kind = item.data(0, ROLE_KIND)
        if kind == "customer":
            return {"customer_id": item.data(0, ROLE_ID)}
        if kind == "project":
            return {"project_id": item.data(0, ROLE_ID)}
        return None

    def _reload_notes(self, select_id: int | None = None):
        target = self._current_target()
        self.note_list.blockSignals(True)
        self.note_list.clear()
        self._clear_editor()
        if target is None:
            self.note_list.blockSignals(False)
            self._set_editor_enabled(False)
            return
        for note in self.db.notes_for(**target):
            item = QListWidgetItem(note["title"] or tr("(ohne Titel)"))
            item.setData(ROLE_ID, note["id"])
            item.setToolTip(tr("Geändert: {}").format(
                note["updated_at"].strftime("%d.%m.%Y %H:%M")))
            self.note_list.addItem(item)
            if note["id"] == select_id:
                self.note_list.setCurrentItem(item)
        self.note_list.blockSignals(False)
        if select_id is None and self.note_list.count():
            self.note_list.setCurrentRow(0)
        elif select_id is not None:
            self._load_selected_note()
        self._set_editor_enabled(self.note_list.currentItem() is not None)

    def _note_selected(self, current: QListWidgetItem | None, _prev=None):
        self._save_current_note()
        self._load_selected_note()

    def _load_selected_note(self):
        item = self.note_list.currentItem()
        if item is None:
            self._clear_editor()
            self._set_editor_enabled(False)
            return
        target = self._current_target()
        note = next(
            (n for n in self.db.notes_for(**target) if n["id"] == item.data(ROLE_ID)), None)
        if note is None:
            return
        self._loading = True
        self.current_note_id = note["id"]
        self.title_edit.setText(note["title"])
        self.body_edit.setPlainText(note["body"])
        self._loading = False
        self._set_editor_enabled(True)

    def _new_note(self):
        target = self._current_target()
        if target is None:
            return
        self._save_current_note()
        note_id = self.db.create_note(**target, title=tr("Neue Notiz"))
        self._reload_notes(select_id=note_id)
        self.title_edit.selectAll()
        self.title_edit.setFocus()

    def _delete_note(self):
        if self.current_note_id is None:
            return
        answer = QMessageBox.question(
            self, tr("Notiz löschen"), tr("Diese Notiz wirklich löschen?"))
        if answer == QMessageBox.StandardButton.Yes:
            self.db.delete_note(self.current_note_id)
            self.current_note_id = None
            self._reload_notes()

    def _create_issue(self):
        target = self._current_target()
        if self.current_note_id is None or not target or "project_id" not in target:
            return
        self._save_current_note()
        project = self.db.project_by_id(target["project_id"])
        note = {"id": self.current_note_id,
                "title": self.title_edit.text().strip(),
                "body": self.body_edit.toPlainText()}
        dialog = IssueDialog(self.db, project, note, self)
        if dialog.exec() == IssueDialog.DialogCode.Accepted and dialog.created_issue:
            issue = dialog.created_issue
            self.body_edit.appendPlainText(
                f"\n→ Issue #{issue['number']} ({issue['repo']}): {issue['url']}")
            self._save_current_note()

    def _save_current_note(self):
        if self.current_note_id is None or self._loading:
            return
        self.db.update_note(
            self.current_note_id,
            self.title_edit.text().strip(),
            self.body_edit.toPlainText(),
        )
        item = self.note_list.currentItem()
        if item is not None and item.data(ROLE_ID) == self.current_note_id:
            item.setText(self.title_edit.text().strip() or tr("(ohne Titel)"))

    def _clear_editor(self):
        self._loading = True
        self.current_note_id = None
        self.title_edit.clear()
        self.body_edit.clear()
        self._loading = False

    def _set_editor_enabled(self, enabled: bool):
        self.title_edit.setEnabled(enabled)
        self.body_edit.setEnabled(enabled)
        self.del_note_btn.setEnabled(enabled)
        self.new_note_btn.setEnabled(self._current_target() is not None)
        target = self._current_target() or {}
        is_project_note = enabled and "project_id" in target
        self.issue_btn.setEnabled(is_project_note)
        if enabled and not is_project_note:
            self.issue_btn.setToolTip(
                tr("Issues brauchen ein Projekt – diese Notiz hängt an einem Kunden"))

    def closeEvent(self, event):
        self._save_current_note()
        event.accept()

    def hideEvent(self, event):
        self._save_current_note()
        super().hideEvent(event)
