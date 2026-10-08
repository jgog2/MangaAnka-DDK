"""Small original monochrome navigation glyphs; no external icon assets."""
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

PATHS = {
 'Workflow':'M4 5h5v5H4z M15 14h5v5h-5z M9 7h8v7 M7 10v7h8',
 'Catalog':'M4 4h16v16H4z M4 9h16 M9 9v11',
 'Audit':'M5 18V12 M12 18V5 M19 18V8',
 'Problems':'M12 3L2 21h20z M12 9v5 M12 17v1',
 'Curate':'M4 6h16 M4 12h16 M4 18h16 M8 3v6 M16 9v6 M10 15v6',
 'History':'M5 7a9 9 0 1 1-2 7 M3 3v5h5 M12 7v6l4 2',
 'Details':'M5 3h14v18H5z M8 7h8 M8 11h8 M8 15h5'}


def icon(name,color='#A7ADB7'):
    svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24"><path d="{PATHS[name]}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    renderer=QSvgRenderer(QByteArray(svg.encode()));pixmap=QPixmap(24,24);pixmap.fill(__import__('PySide6.QtCore',fromlist=['Qt']).Qt.transparent)
    painter=QPainter(pixmap);renderer.render(painter);painter.end();return QIcon(pixmap)
