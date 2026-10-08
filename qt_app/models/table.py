from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QSortFilterProxyModel
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem
from qt_app.theme import status_color


class RecordModel(QAbstractTableModel):
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.columns = columns  # (key, label, width, status)
        self.records = []

    def replace(self, records):
        self.beginResetModel()
        self.records = records
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()): return 0 if parent.isValid() else len(self.records)
    def columnCount(self, parent=QModelIndex()): return len(self.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        row = self.records[index.row()]
        value = row.get(self.columns[index.column()][0])
        if role == Qt.UserRole: return row
        if role in (Qt.DisplayRole, Qt.ToolTipRole): return '—' if value is None or value == '' else str(value)
        if role == Qt.TextAlignmentRole and index.column() > 0: return Qt.AlignLeft | Qt.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole: return self.columns[section][1]
        return None


class RecordFilter(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search = ''
        self.filters = {}
        self.setDynamicSortFilter(True)

    def update(self, search, filters=None):
        self.beginFilterChange()
        self.search = search.casefold()
        self.filters = filters or {}
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, row, parent):
        record = self.sourceModel().records[row]
        return (not self.search or self.search in ' '.join(str(v) for k, v in record.items() if not k.startswith('_')).casefold()) and all(
            str(record.get(k, '')) == str(v) for k, v in self.filters.items() if v != 'All')

    def lessThan(self, left, right):
        a = self.sourceModel().data(left); b = self.sourceModel().data(right)
        try: return float(a) < float(b)
        except (ValueError, TypeError): return str(a).casefold() < str(b).casefold()


class StatusDelegate(QStyledItemDelegate):
    """Status tint remains independent of subdued row selection."""
    def paint(self, painter, option, index):
        model = index.model()
        source = model.sourceModel() if hasattr(model, 'sourceModel') else model
        mapped = model.mapToSource(index) if hasattr(model, 'mapToSource') else index
        if source.columns[mapped.column()][3]:
            styled = QStyleOptionViewItem(option)
            self.initStyleOption(styled, index)
            color = QColor(status_color(index.data()))
            styled.palette.setColor(styled.palette.ColorRole.Text, color)
            styled.palette.setColor(styled.palette.ColorRole.HighlightedText, color)
            self.parent().style().drawControl(QStyle.CE_ItemViewItem, styled, painter, self.parent())
        else: super().paint(painter, option, index)
