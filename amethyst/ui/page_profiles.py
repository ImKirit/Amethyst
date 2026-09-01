"""Profile page: create games, define triggers, edit the values."""

from __future__ import annotations

import copy

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QInputDialog,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu,
                               QMessageBox, QPushButton, QScrollArea, QSplitter, QVBoxLayout,
                               QWidget)

from ..engine import Engine
from ..models import Profile
from ..presets import PRESETS, preset_for_process
from ..winapi import displays
from ..winapi.processes import user_processes
from . import theme
from .panels import ColorPanel, ResolutionPanel
from .widgets import Badge, Card, Toggle, label


class ProcessPicker(QDialog):
    """Pick from the programs that are running right now."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Pick a running program")
        self.setMinimumSize(420, 460)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(label("Start the game, then pick its process here.", "pageHint"))

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search")
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.itemDoubleClicked.connect(lambda _i: self.accept())
        layout.addWidget(self.list, 1)

        buttons = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("ghost")
        cancel.clicked.connect(self.reject)
        take = QPushButton("Add")
        take.setObjectName("primary")
        take.clicked.connect(self.accept)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(take)
        layout.addLayout(buttons)

        self._load()

    def _load(self) -> None:
        for process in user_processes():
            item = QListWidgetItem(f"{process.name}")
            item.setData(Qt.UserRole, process.name)
            known = preset_for_process(process.name)
            if known:
                item.setText(f"{known.icon}  {process.name}   ({known.name})")
            self.list.addItem(item)

    def _filter(self, text: str) -> None:
        text = text.lower()
        for index in range(self.list.count()):
            item = self.list.item(index)
            item.setHidden(text not in item.text().lower())

    def selection(self) -> list[str]:
        return [item.data(Qt.UserRole) for item in self.list.selectedItems()]


class ProfileListItem(QWidget):
    """One row in the profile list."""

    def __init__(self, profile: Profile, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(44)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(11)

        icon = QLabel(profile.icon or "🎮")
        icon.setStyleSheet("font-size: 20px;")
        layout.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(1)
        name = QLabel(profile.name)
        name.setStyleSheet("font-size: 13px; font-weight: 600;")
        summary = profile.summary()
        if len(summary) > 36:
            summary = summary[:35].rstrip(" ·") + "…"
        detail = QLabel(summary)
        detail.setObjectName("faint")
        text.addWidget(name)
        text.addWidget(detail)
        layout.addLayout(text, 1)

        self.badge = Badge("", theme.TEXT_FAINT)
        self.badge.hide()
        layout.addWidget(self.badge)
        if not profile.enabled:
            self.badge.set_state("off", theme.TEXT_FAINT)
            self.badge.show()

    def mark_active(self, active: bool) -> None:
        if active:
            self.badge.set_state("active", theme.SUCCESS)
            self.badge.show()


class ProfilesPage(QWidget):
    """List on the left, editor on the right."""

    statusMessage = Signal(str)
    profilesChanged = Signal()

    def __init__(self, engine: Engine, parent=None) -> None:
        super().__init__(parent)
        self.engine = engine
        self.store = engine.store
        self._current: Profile | None = None
        self._loading = False
        self._displays: list[displays.Display] = []

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(350)
        self._save_timer.timeout.connect(self._save_current)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)

        head = QVBoxLayout()
        head.setSpacing(4)
        head.addWidget(label("Profiles", "pageTitle"))
        head.addWidget(label("A profile takes over as soon as one of its processes runs. "
                             "When none of them does, the desktop values apply again.", "pageHint"))
        outer.addLayout(head)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(12)
        splitter.setChildrenCollapsible(False)

        # -- left column
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(11)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        self.new_button = QPushButton("New profile")
        self.new_button.setObjectName("primary")
        self.new_button.setCursor(Qt.PointingHandCursor)
        self.new_button.clicked.connect(self._show_new_menu)
        buttons.addWidget(self.new_button, 1)
        left_layout.addLayout(buttons)

        self.list = QListWidget()
        self.list.setSpacing(0)
        self.list.currentRowChanged.connect(self._on_selection)
        left_layout.addWidget(self.list, 1)

        tools = QHBoxLayout()
        tools.setSpacing(8)
        for text, tip, slot in (
            ("▲", "Move up (upper profiles win when several match)", lambda: self._move(-1)),
            ("▼", "Move down", lambda: self._move(1)),
            ("Duplicate", "Copy this profile", self._duplicate),
            ("Delete", "Remove this profile", self._delete),
        ):
            button = QPushButton(text)
            button.setObjectName("ghost")
            button.setCursor(Qt.PointingHandCursor)
            button.setToolTip(tip)
            button.clicked.connect(slot)
            if len(text) <= 2:
                button.setFixedWidth(46)
            tools.addWidget(button)
        left_layout.addLayout(tools)
        splitter.addWidget(left)

        # -- right column
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        self.editor_scroll = QScrollArea()
        self.editor_scroll.setWidgetResizable(True)
        self.editor_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        editor = QWidget()
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(0, 0, 8, 0)
        editor_layout.setSpacing(16)

        self.header_card = Card("Profile")
        name_row = QWidget()
        name_layout = QHBoxLayout(name_row)
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(8)
        self.icon_edit = QLineEdit()
        self.icon_edit.setMaxLength(2)
        self.icon_edit.setFixedWidth(52)
        self.icon_edit.setAlignment(Qt.AlignCenter)
        self.icon_edit.setToolTip("One character or emoji")
        self.icon_edit.setStyleSheet("font-size: 18px; padding: 4px;")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Name of the game")
        self.enabled_toggle = Toggle("Profile on", True)
        name_layout.addWidget(self.icon_edit)
        name_layout.addWidget(self.name_edit, 1)
        name_layout.addWidget(self.enabled_toggle)
        self.header_card.add(name_row)
        editor_layout.addWidget(self.header_card)

        self.process_card = Card(
            "Trigger",
            "Process names of the executables. As soon as one of them runs, Amethyst switches.")
        self.process_list = QListWidget()
        self.process_list.setObjectName("compactList")
        self.process_list.setMaximumHeight(112)
        self.process_card.add(self.process_list)
        process_buttons = QHBoxLayout()
        process_buttons.setSpacing(8)
        pick = QPushButton("From running programs")
        pick.setObjectName("ghost")
        pick.setCursor(Qt.PointingHandCursor)
        pick.clicked.connect(self._pick_process)
        manual = QPushButton("Manually")
        manual.setObjectName("ghost")
        manual.setCursor(Qt.PointingHandCursor)
        manual.clicked.connect(self._add_process_manually)
        remove = QPushButton("Remove")
        remove.setObjectName("ghost")
        remove.setCursor(Qt.PointingHandCursor)
        remove.clicked.connect(self._remove_process)
        process_buttons.addWidget(pick)
        process_buttons.addWidget(manual)
        process_buttons.addStretch(1)
        process_buttons.addWidget(remove)
        self.process_card.add_layout(process_buttons)
        editor_layout.addWidget(self.process_card)

        self.target_card = Card("Display", "Which screen this profile affects")
        self.display_box = QComboBox()
        self.display_box.currentIndexChanged.connect(self._on_display_changed)
        self.target_card.add(self.display_box)
        editor_layout.addWidget(self.target_card)

        self.color_panel = ColorPanel("Color")
        self.resolution_panel = ResolutionPanel("Resolution")
        editor_layout.addWidget(self.color_panel)
        editor_layout.addWidget(self.resolution_panel)

        self.restore_toggle = Toggle("Restore after the game closes", True)
        self.restore_toggle.setToolTip("Switch back to the desktop values once the game is gone")
        editor_layout.addWidget(self.restore_toggle)
        editor_layout.addStretch(1)
        self.editor_scroll.setWidget(editor)
        right_layout.addWidget(self.editor_scroll, 1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.test_button = QPushButton("Preview for 10 seconds")
        self.test_button.setObjectName("ghost")
        self.test_button.setCursor(Qt.PointingHandCursor)
        self.test_button.clicked.connect(self._test)
        self.apply_button = QPushButton("Apply now")
        self.apply_button.setObjectName("primary")
        self.apply_button.setCursor(Qt.PointingHandCursor)
        self.apply_button.clicked.connect(self._apply_now)
        actions.addWidget(self.test_button)
        actions.addStretch(1)
        actions.addWidget(self.apply_button)
        right_layout.addLayout(actions)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([260, 600])
        outer.addWidget(splitter, 1)

        self.empty_hint = label("No profile yet. Create one with \"New profile\", "
                                "fastest through one of the templates.", "pageHint")
        outer.addWidget(self.empty_hint)

        for widget in (self.name_edit, self.icon_edit):
            widget.textChanged.connect(self._schedule_save)
        self.enabled_toggle.toggled.connect(self._schedule_save)
        self.restore_toggle.toggled.connect(self._schedule_save)
        self.color_panel.changed.connect(self._schedule_save)
        self.resolution_panel.changed.connect(self._schedule_save)

        self.reload_displays()
        self.reload()

    # -- Data ---------------------------------------------------------
    def reload_displays(self) -> None:
        self._displays = displays.list_displays()
        self.display_box.blockSignals(True)
        self.display_box.clear()
        self.display_box.addItem("Main display", "primary")
        for display in self._displays:
            self.display_box.addItem(display.label, display.device)
        self.display_box.blockSignals(False)

    def reload(self, select_id: str | None = None) -> None:
        self.list.blockSignals(True)
        self.list.clear()
        for profile in self.store.profiles:
            item = QListWidgetItem()
            widget = ProfileListItem(profile)
            if self.engine.active and self.engine.active.id == profile.id:
                widget.mark_active(True)
            item.setSizeHint(QSize(0, max(60, widget.sizeHint().height() + 18)))
            item.setData(Qt.UserRole, profile.id)
            self.list.addItem(item)
            self.list.setItemWidget(item, widget)
        self.list.blockSignals(False)

        has_profiles = bool(self.store.profiles)
        self.editor_scroll.setVisible(has_profiles)
        self.test_button.setVisible(has_profiles)
        self.apply_button.setVisible(has_profiles)
        self.empty_hint.setVisible(not has_profiles)

        if has_profiles:
            target = 0
            if select_id:
                for index, profile in enumerate(self.store.profiles):
                    if profile.id == select_id:
                        target = index
                        break
            elif self._current:
                for index, profile in enumerate(self.store.profiles):
                    if profile.id == self._current.id:
                        target = index
                        break
            self.list.setCurrentRow(target)
        else:
            self._current = None

    def _on_selection(self, row: int) -> None:
        if row < 0 or row >= len(self.store.profiles):
            return
        self._load_profile(self.store.profiles[row])

    def _load_profile(self, profile: Profile) -> None:
        self._loading = True
        self._current = profile
        self.name_edit.setText(profile.name)
        self.icon_edit.setText(profile.icon)
        self.enabled_toggle.setChecked(profile.enabled)
        self.restore_toggle.setChecked(profile.restore_on_exit)
        self.process_list.clear()
        for process in profile.processes:
            self.process_list.addItem(process)
        index = self.display_box.findData(profile.display)
        self.display_box.setCurrentIndex(index if index >= 0 else 0)
        self._sync_resolution_display()
        self.color_panel.set_values(profile.color)
        self.resolution_panel.set_values(profile.resolution)
        caps = self.engine.capabilities
        self.color_panel.set_capabilities(caps.gamma_ok, caps.gamma_reason,
                                          caps.vibrance_ok, caps.vibrance_reason)
        self._loading = False

    def _sync_resolution_display(self) -> None:
        device = self.display_box.currentData()
        display = next((d for d in self._displays if d.device == device), None)
        if display is None:
            display = next((d for d in self._displays if d.primary), None)
        self.resolution_panel.set_display(display)

    def _on_display_changed(self, _index: int) -> None:
        self._sync_resolution_display()
        self._schedule_save()

    # -- Saving -------------------------------------------------------
    def _schedule_save(self, *_args) -> None:
        if self._loading or self._current is None:
            return
        self._save_timer.start()

    def _save_current(self) -> None:
        if self._current is None:
            return
        profile = self._current
        profile.name = self.name_edit.text().strip() or "Profile"
        profile.icon = self.icon_edit.text().strip() or "🎮"
        profile.enabled = self.enabled_toggle.isChecked()
        profile.restore_on_exit = self.restore_toggle.isChecked()
        profile.display = self.display_box.currentData() or "primary"
        profile.processes = [self.process_list.item(i).text()
                             for i in range(self.process_list.count())]
        profile.color = self.color_panel.values()
        profile.resolution = self.resolution_panel.values()
        self.store.replace(profile)
        self._refresh_row(profile)
        self.profilesChanged.emit()

    def _refresh_row(self, profile: Profile) -> None:
        for index in range(self.list.count()):
            item = self.list.item(index)
            if item.data(Qt.UserRole) == profile.id:
                widget = ProfileListItem(profile)
                if self.engine.active and self.engine.active.id == profile.id:
                    widget.mark_active(True)
                item.setSizeHint(QSize(0, max(60, widget.sizeHint().height() + 18)))
                self.list.setItemWidget(item, widget)
                break

    # -- Actions ------------------------------------------------------
    def build_new_menu(self) -> tuple[QMenu, object, dict]:
        """Template menu behind the "New profile" button."""
        menu = QMenu(self)
        menu.setStyleSheet(self.window().styleSheet())
        empty = menu.addAction("Empty profile")
        menu.addSeparator()
        actions = {}
        for preset in PRESETS:
            action = menu.addAction(f"{preset.icon}  {preset.name}")
            actions[action] = preset
        return menu, empty, actions

    def _show_new_menu(self) -> None:
        menu, empty, actions = self.build_new_menu()
        chosen = menu.exec(self.new_button.mapToGlobal(self.new_button.rect().bottomLeft()))
        if chosen is None:
            return
        if chosen is empty:
            profile = Profile(name="New profile")
        else:
            profile = actions[chosen].to_profile()
        self.store.add(profile)
        self.reload(select_id=profile.id)
        self.statusMessage.emit(f"Profile \"{profile.name}\" created")
        self.profilesChanged.emit()

    def _duplicate(self) -> None:
        if self._current is None:
            return
        clone = copy.deepcopy(self._current)
        clone.id = Profile().id
        clone.name = f"{self._current.name} (copy)"
        self.store.add(clone)
        self.reload(select_id=clone.id)
        self.profilesChanged.emit()

    def _delete(self) -> None:
        if self._current is None:
            return
        answer = QMessageBox.question(
            self, "Delete profile",
            f"Really delete the profile \"{self._current.name}\"?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        self.store.remove(self._current.id)
        self._current = None
        self.reload()
        self.profilesChanged.emit()

    def _move(self, offset: int) -> None:
        if self._current is None:
            return
        self.store.move(self._current.id, offset)
        self.reload(select_id=self._current.id)

    def _pick_process(self) -> None:
        dialog = ProcessPicker(self.window())
        if dialog.exec() != QDialog.Accepted:
            return
        existing = {self.process_list.item(i).text().lower()
                    for i in range(self.process_list.count())}
        for name in dialog.selection():
            if name.lower() not in existing:
                self.process_list.addItem(name)
        self._schedule_save()

    def _add_process_manually(self) -> None:
        name, ok = QInputDialog.getText(self, "Add a process",
                                        "File name of the application, for example cs2.exe:")
        if ok and name.strip():
            self.process_list.addItem(name.strip())
            self._schedule_save()

    def _remove_process(self) -> None:
        for item in self.process_list.selectedItems():
            self.process_list.takeItem(self.process_list.row(item))
        self._schedule_save()

    def _apply_now(self) -> None:
        if self._current is None:
            return
        self._save_current()
        notes = self.engine.activate(self._current)
        self.statusMessage.emit(notes[0] if notes else f"{self._current.name} applied")

    def _test(self) -> None:
        if self._current is None:
            return
        self._save_current()
        notes = self.engine.apply_profile(self._current)
        self.statusMessage.emit(notes[0] if notes else f"{self._current.name} runs for 10 seconds")
        QTimer.singleShot(10_000, self._end_test)

    def _end_test(self) -> None:
        if self.engine.active is None:
            desktop = self.store.settings.desktop
            if desktop.color.enabled or desktop.resolution.is_set():
                self.engine.apply_profile(desktop)
            else:
                self.engine.restore_all(clear=False)
        self.statusMessage.emit("Preview finished")
