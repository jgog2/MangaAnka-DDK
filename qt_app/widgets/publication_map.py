from PySide6.QtCore import Qt, Signal, QItemSelectionModel
from PySide6.QtWidgets import QTreeView, QAbstractItemView
from qt_app.models.publication import PublicationModel


class PublicationMap(QTreeView):
    chapter_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.publication = PublicationModel(self); self.setModel(self.publication)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setUniformRowHeights(True)
        self.setColumnWidth(0, 380); self.setColumnWidth(1, 260)
        self.setAccessibleName('Publication Map: volumes and exact chapters')
        self.selectionModel().selectionChanged.connect(self._changed)

    def _changed(self):
        rows = self.selected_rows()
        if rows: self.chapter_selected.emit(rows[0])

    def selected_rows(self): return [i.data(Qt.UserRole) for i in self.selectionModel().selectedRows() if i.data(Qt.UserRole)]

    def replace(self, rows, volumes=(), supplementary=None):
        self.publication.replace(rows, volumes, supplementary)
        for i in range(self.publication.rowCount()): self.expand(self.publication.index(i, 0))

    def focus_keys(self, keys):
        nodes = [n for n in self.publication.by_iid.values() if n.row['key'] in {str(k) for k in keys} or str(n.row['effective'].get('chapter')) in {str(k) for k in keys}]
        self.selectionModel().clearSelection()
        for n in nodes:
            index = self.publication.row_index(n.row['iid'])
            self.expand(index.parent())
            self.selectionModel().select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
        if nodes:
            index = self.publication.row_index(nodes[0].row['iid'])
            self.setCurrentIndex(index); self.scrollTo(index, QAbstractItemView.PositionAtCenter); self.setFocus()
        return bool(nodes)
