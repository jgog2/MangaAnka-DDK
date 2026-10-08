import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
                              QScrollArea, QFormLayout, QGroupBox, QPlainTextEdit, QMenu,
                              QTableView, QAbstractItemView, QHeaderView)
from qt_app.models.table import RecordModel, RecordFilter, StatusDelegate
from qt_app.theme import font, status_color


def pretty(value): return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def button(text, callback, parent=None, primary=False):
    result = QPushButton(text, parent)
    result.setAccessibleName(text)
    result.setToolTip(text)
    result.setProperty('primary', primary)
    result.clicked.connect(callback)
    return result


def menu_button(text, entries, parent=None):
    result = QPushButton(text, parent)
    menu = QMenu(result)
    for label, callback in entries:
        if label is None: menu.addSeparator()
        else: menu.addAction(label, callback)
    result.setMenu(menu)
    return result


class StatusChip(QLabel):
    def __init__(self, text='', parent=None):
        super().__init__(parent)
        self.setText(text)

    def setText(self, text):
        super().setText(str(text))
        self.setStyleSheet(f'padding:5px 8px; border-radius:8px; background:#23272E; color:{status_color(text)};')


class RawData(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setFont(font(True))
        self.setAccessibleName('Technical data; selectable and copyable')
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def show_data(self, data): self.setPlainText(data if isinstance(data, str) else pretty(data))


class Inspector(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setMinimumWidth(0)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setAccessibleName('Context inspector')
        self.display('Select a row', {})

    def display(self, title, groups, actions=(), raw=None, publication_rows=None):
        old = self.takeWidget()
        if old: old.deleteLater()
        body = QWidget()
        layout = QVBoxLayout(body)
        empty = not groups and not actions and raw is None and publication_rows is None
        self.setProperty('empty', empty)
        if empty:
            layout.addStretch()
            label = QLabel(title); label.setWordWrap(True); label.setAlignment(Qt.AlignCenter)
            label.setProperty('secondary', True); label.setAccessibleName('Empty inspector guidance')
            layout.addWidget(label); layout.addStretch(); self.setWidget(body)
            return
        label = QLabel(title); label.setWordWrap(True); label.setProperty('pageTitle', True)
        layout.addWidget(label)
        for heading, values in groups.items():
            group = QGroupBox(heading); form = QFormLayout(group)
            form.setRowWrapPolicy(QFormLayout.WrapLongRows)
            for key, value in values.items():
                label = QLabel('—' if value is None else str(value))
                label.setWordWrap(True); label.setTextInteractionFlags(Qt.TextSelectableByMouse)
                form.addRow(str(key).replace('_', ' ').title(), label)
            layout.addWidget(group)
        if publication_rows is not None:
            from qt_app.widgets.publication_map import PublicationMap
            publication = PublicationMap(); publication.replace(publication_rows); publication.collapseAll()
            publication.hideColumn(1); publication.hideColumn(2); publication.setHeaderHidden(True)
            publication.setMinimumHeight(130); publication.setMaximumHeight(230)
            publication.setAccessibleName('Compact volume summary')
            layout.addWidget(publication)
        for text, callback in actions: layout.addWidget(button(text, callback))
        if raw is not None:
            toggle = QPushButton('Technical details'); toggle.setCheckable(True)
            text = RawData(); text.show_data(raw); text.setMinimumHeight(200); text.hide()
            toggle.toggled.connect(text.setVisible)
            layout.addWidget(toggle); layout.addWidget(text)
        layout.addStretch()
        self.setWidget(body)


class RecordTable(QTableView):
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.records = RecordModel(columns, self)
        self.proxy = RecordFilter(self); self.proxy.setSourceModel(self.records)
        self.setModel(self.proxy)
        self.setItemDelegate(StatusDelegate(self))
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSortingEnabled(True)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(38)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setStretchLastSection(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        for i, column in enumerate(columns): self.setColumnWidth(i, column[2])
        self.sortByColumn(0, Qt.AscendingOrder)

    def selected(self):
        return [self.records.records[self.proxy.mapToSource(i).row()] for i in self.selectionModel().selectedRows()]

    def current(self): return self.selected()[0] if self.selected() else None

    def select_record(self, predicate):
        for r in range(self.proxy.rowCount()):
            index = self.proxy.index(r, 0)
            if predicate(index.data(Qt.UserRole)):
                self.selectRow(r); self.scrollTo(index); return True
        return False
