from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QShortcut, QKeySequence, QTextCharFormat, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QLabel
from ddk_commands import HELP as NUMERIC_HELP
from ddk_supplementary_commands import HELP as SUPPLEMENTARY_HELP
HELP=NUMERIC_HELP+'\n'+SUPPLEMENTARY_HELP
from qt_app.theme import font
from qt_app.widgets.common import button, RawData


class CommandInput(QPlainTextEdit):
    history_requested = Signal(int)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Down) and event.modifiers() == Qt.NoModifier:
            self.history_requested.emit(-1 if event.key() == Qt.Key_Up else 1)
        else: super().keyPressEvent(event)


class CommandDrawer(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.window = window; self.history = []; self.history_index = 0
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0)
        self.toggle = button('› Command…    Expand', self.toggle_expanded)
        layout.addWidget(self.toggle)
        self.body = QWidget(); body = QVBoxLayout(self.body)
        self.target_text='Open a title in Curate to use exact chapter commands.'
        self.context = QLabel(self.target_text);self.context.setWordWrap(True); body.addWidget(self.context)
        self.input = CommandInput(); self.input.setFont(font(True)); self.input.setMaximumHeight(100)
        self.input.setPlaceholderText('select chapter 275\nset volume 23 selected\nset verification verified selected')
        self.input.setAccessibleName('Command console'); self.input.history_requested.connect(self.cycle)
        body.addWidget(self.input)
        actions = QHBoxLayout()
        self.preview_button = button('Preview', self.preview, primary=True); actions.addWidget(self.preview_button)
        self.apply_button = button('Apply Changes', self.apply); self.apply_button.setEnabled(False); actions.addWidget(self.apply_button)
        actions.addWidget(button('Cancel', self.cancel))
        actions.addWidget(button('Undo', lambda: self.reverse(False))); actions.addWidget(button('Redo', lambda: self.reverse(True)))
        actions.addStretch(); actions.addWidget(button('Command Help', lambda: window.show_text('Command Help', HELP)))
        body.addLayout(actions)
        self.output = RawData(); self.output.setMaximumHeight(140); body.addWidget(self.output)
        layout.addWidget(self.body); self.body.hide()
        self.shortcut = QShortcut(QKeySequence('Ctrl+Return'), window); self.shortcut.activated.connect(self.preview)
        self.shortcut_enter = QShortcut(QKeySequence('Ctrl+Enter'), window); self.shortcut_enter.activated.connect(self.preview)
        self.input.textChanged.connect(self.update_context)

    def update_context(self):
        self.context.setText(self.target_text+f'\n{len(self.input.toPlainText().splitlines())} lines · guarded edits Preview then explicit Apply; other console commands keep their normal behavior.')

    def set_target(self,text):
        self.target_text=text;self.update_context()

    def set_expanded(self, expanded):
        self.body.setVisible(expanded); self.toggle.setText('› Command Console    Collapse' if expanded else '› Command…    Expand')
        if hasattr(self.window,'workflow'):self.window.workflow.adapt()
        if expanded: self.input.setFocus()

    def toggle_expanded(self): self.set_expanded(self.body.isHidden())

    def preview(self):
        self.set_expanded(True)
        text = self.input.toPlainText().strip()
        self.apply_button.setEnabled(False)
        try:
            result = self.window.command.execute(text)
            self.output.show_data(result)
            self.apply_button.setEnabled(bool(self.window.command.pending))
            self.input.setStyleSheet('')
            self.history.append(text); self.history_index = len(self.history)
        except Exception as exc:
            self.window.command.cancel(); self.output.show_data('Command blocked: '+str(exc))
            self.input.setStyleSheet('border:1px solid #E69B9B;')

    def apply(self):
        try:
            self.window.command.apply(); self.apply_button.setEnabled(False)
            self.output.show_data('\n'.join(self.window.command.messages))
        except Exception as exc: self.output.show_data('Apply blocked: '+str(exc)); self.apply_button.setEnabled(False)

    def cancel(self):
        self.window.command.cancel(); self.apply_button.setEnabled(False); self.output.show_data('Preview cancelled; saved data unchanged.')

    def reverse(self, redo):
        self.set_expanded(True)
        try:
            self.window.command.preview_reverse(redo); self.output.show_data(self.window.command.preview_text()); self.apply_button.setEnabled(True)
        except Exception as exc: self.output.show_data(str(exc)); self.apply_button.setEnabled(False)

    def cycle(self, direction):
        self.history_index = max(0, min(len(self.history), self.history_index+direction))
        self.input.setPlainText(self.history[self.history_index] if self.history_index < len(self.history) else '')
