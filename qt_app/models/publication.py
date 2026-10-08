"""A tree projection of Catalog.rows; identifiers/order are preserved verbatim."""
from collections import OrderedDict
from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QColor
from qt_app.theme import TOKENS, status_color
from ddk_supplementary import map_rows


class Node:
    def __init__(self, values=(), row=None, parent=None):
        self.values = values; self.row = row; self.parent = parent; self.children = []


class PublicationModel(QAbstractItemModel):
    headers = ('Publication', 'State', 'Source')

    def __init__(self, parent=None):
        super().__init__(parent); self.root = Node(); self.by_iid = {}

    def replace(self, rows, volumes=(), supplementary=None):
        self.beginResetModel(); self.root = Node(); self.by_iid = {}
        groups = OrderedDict()
        for row in list(rows) + map_rows(supplementary or {}):
            # Provider records are diagnostic inventory, never counted as volumes.
            name = 'Supplementary / separate identities' if row.get('supplementary') else 'Uncompiled / Serialized chapters' if 'UNCOMPILED' in row['status'] else 'Provider-only / unclassified' if ('UNCLASSIFIED' in row['status'] or 'PROVIDER ARTIFACT' in row['status']) else (
                'Unmapped' if row['effective'].get('volume') in (None, '') else 'Volume '+str(row['effective']['volume']))
            groups.setdefault(name, []).append(row)
        for volume in volumes:
            key = volume.get('key') if isinstance(volume, dict) else volume
            if key is not None: groups.setdefault('Volume '+str(key), [])
        for name, members in groups.items():
            unresolved = any(r['conflict'] or r['missing'] or r['effective'].get('volume') in (None, '') for r in members)
            boundaries = f" · {members[0]['key']}–{members[-1]['key']}" if members and not name.startswith('Supplementary') else ''
            units='publications' if name.startswith('Supplementary') else 'records' if name.startswith('Provider-only') else 'chapters'
            group = Node((f'{name} · {len(members)} {units}{boundaries}', 'UNCOMPILED' if name.startswith('Uncompiled') else 'REVIEW' if unresolved or not members else 'MAPPED', ''), parent=self.root)
            self.root.children.append(group)
            for row in members:
                eff = row['effective']; title = eff.get('title') or 'Untitled'
                curated_volume=row['curated'].get('volume')
                source='curated_database' if curated_volume and curated_volume['verification']!='UNVERIFIED' and 'INCOMPATIBLE' not in row['status'] else row.get('source') or '—'
                label = 'Supplement · '+title if row.get('supplementary') else f"{eff.get('chapter') or row['key']} · {title}"
                node = Node((label, row['status'], source), row, group)
                group.children.append(node); self.by_iid[row['iid']] = node
        self.endResetModel()

    def index(self, row, column, parent=QModelIndex()):
        node = parent.internalPointer() if parent.isValid() else self.root
        if 0 <= row < len(node.children) and 0 <= column < 3: return self.createIndex(row, column, node.children[row])
        return QModelIndex()

    def parent(self, index):
        if not index.isValid(): return QModelIndex()
        p = index.internalPointer().parent
        if p is self.root: return QModelIndex()
        return self.createIndex(p.parent.children.index(p), 0, p)

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid() and parent.column() != 0: return 0
        return len((parent.internalPointer() if parent.isValid() else self.root).children)

    def columnCount(self, parent=QModelIndex()): return 3

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        node = index.internalPointer()
        if role == Qt.ToolTipRole and node.row and node.row.get('supplementary'):
            return node.row['key']+'\n'+node.row['status']+'\n'+node.row['source']
        if role in (Qt.DisplayRole, Qt.ToolTipRole): return node.values[index.column()]
        if role == Qt.UserRole: return node.row
        if role == Qt.ForegroundRole:
            if index.column() == 1: return QColor(status_color(node.values[1]))
            if node.row and not node.row['effective'].get('title') and index.column() == 0: return QColor(TOKENS['secondary'])
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole: return self.headers[section]

    def row_index(self, iid):
        node = self.by_iid.get(iid)
        return self.createIndex(node.parent.children.index(node), 0, node) if node else QModelIndex()
