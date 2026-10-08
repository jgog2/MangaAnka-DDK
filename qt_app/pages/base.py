from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox, QSplitter
from qt_app.widgets.common import Inspector, button


class Page(QWidget):
    def __init__(self, window, name):
        super().__init__()
        self.window = window; self.name = name
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(18, 14, 18, 12); self.layout.setSpacing(12)
        header = QHBoxLayout(); title = QLabel(name); title.setProperty('pageTitle', True)
        header.addWidget(title); header.addSpacing(12)
        self.scope_box = QComboBox(); self.scope_box.setMinimumWidth(190); self.scope_box.setAccessibleName(name+' scope')
        header.addWidget(self.scope_box); header.addStretch(); self.layout.addLayout(header)
        self.toolbar = QHBoxLayout(); self.layout.addLayout(self.toolbar)
        self.filterbar = QHBoxLayout(); self.layout.addLayout(self.filterbar)
        self.search = QLineEdit(); self.search.setPlaceholderText('Search '+name.lower()); self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName(name+' search'); self.filterbar.addWidget(self.search, 1)
        self.empty = QLabel(); self.empty.setProperty('secondary', True); self.empty.setWordWrap(True); self.layout.addWidget(self.empty)
        self.splitter = QSplitter(Qt.Horizontal); self.splitter.setChildrenCollapsible(True)
        self.inspector = Inspector(); self.splitter.addWidget(self.inspector)
        self.layout.addWidget(self.splitter, 1)
        self.scope_box.currentIndexChanged.connect(lambda: self.window.safe(self.refresh))
        self.toolbar.addStretch()
        self.toolbar.addWidget(button('Inspector', lambda: self.inspector.setVisible(self.inspector.isHidden())))

    @property
    def scope(self): return self.scope_box.currentData() or 'active'

    def set_scope(self, value):
        i = self.scope_box.findData(value)
        if i >= 0: self.scope_box.setCurrentIndex(i)

    def update_scopes(self):
        value = self.scope
        self.scope_box.blockSignals(True); self.scope_box.clear()
        for text, key in self.window.session.scopes(): self.scope_box.addItem(text, key)
        self.scope_box.setCurrentIndex(max(0, self.scope_box.findData(value))); self.scope_box.blockSignals(False)

    def add_action(self, text, callback, primary=False):
        result = button(text, lambda: self.window.safe(callback), primary=primary)
        self.toolbar.insertWidget(self.toolbar.count()-2, result)
        return result

    def add_filter(self, key, choices, callback, caption=False):
        combo = QComboBox(); combo.addItems(choices); combo.setAccessibleName(key+' filter'); combo.setToolTip(key)
        # Keep backend values intact; context stays visible even after selection.
        if caption:
            label = QLabel(key.title()); label.setProperty('secondary', True)
            label.setBuddy(combo); self.filterbar.addWidget(label)
        combo.currentTextChanged.connect(callback); self.filterbar.addWidget(combo)
        return combo

    def set_content(self, widget):
        self.splitter.insertWidget(0, widget); self.splitter.setStretchFactor(0, 1); self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([900, 310])

    def refresh(self): pass
