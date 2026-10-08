"""Central presentation tokens and installed/local font selection."""
from pathlib import Path
import os
from PySide6.QtGui import QFont, QFontDatabase, QPalette, QColor

TOKENS = dict(background='#16181C', surface='#1D2026', raised='#23272E', hover='#292E36',
              border='#30343C', text='#F4F5F7', secondary='#A7ADB7', muted='#767D89',
              accent='#FF6740', green='#94CEAC', amber='#E3C18A', red='#E69B9B', blue='#9CBBDC')


def font_assets():
    # __file__ also resolves inside PyInstaller's extraction directory.
    return Path(__file__).resolve().parent / 'assets' / 'fonts'


def font_family(mono=False):
    available = set(QFontDatabase.families())
    candidates = ('Geist Mono', 'Cascadia Mono', 'Consolas') if mono else (
        'Geist Sans', 'Segoe UI Variable', 'Segoe UI')
    return next((f for f in candidates if f in available), QFontDatabase.systemFont(
        QFontDatabase.FixedFont if mono else QFontDatabase.GeneralFont).family())


def font(mono=False):
    result = QFont(font_family(mono))
    result.setPointSizeF(10 if mono else 10.5)
    return result


def status_color(text):
    text = str(text).upper()
    if any(s in text for s in ('ERROR', 'CONFLICT', 'INVALID', 'BLOCK')): return TOKENS['red']
    if any(s in text for s in ('REVIEW', 'STALE', 'UNMAPPED', 'SUPERSEDED', 'UNCLASSIFIED')): return TOKENS['amber']
    if text in ('PASS', 'READY', 'CURRENT', 'ACCEPTED', 'VERIFIED', 'COMPLETE'): return TOKENS['green']
    return TOKENS['blue']


def apply_theme(app):
    for path in font_assets().glob('*'):
        if path.suffix.lower() in ('.ttf', '.otf'): QFontDatabase.addApplicationFont(str(path))
    # Qt's Windows offscreen platform has no system-font enumeration. Use the
    # installed Windows fonts for deterministic headless rendering, never copies
    # or downloads. Normal Windows GUI font discovery remains QFontDatabase's.
    if not QFontDatabase.families() and os.name == 'nt':
        installed = Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts'
        for name in ('segoeui.ttf', 'segoeuib.ttf', 'consola.ttf'):
            path = installed / name
            if path.is_file(): QFontDatabase.addApplicationFont(str(path))
    app.setStyle('Fusion')
    app.setFont(font())
    palette = QPalette()
    for role, color in ((QPalette.Window, 'background'), (QPalette.Base, 'surface'),
                        (QPalette.AlternateBase, 'raised'), (QPalette.WindowText, 'text'),
                        (QPalette.Text, 'text'), (QPalette.Button, 'raised'),
                        (QPalette.ButtonText, 'text'), (QPalette.Highlight, 'hover'),
                        (QPalette.HighlightedText, 'text'), (QPalette.ToolTipBase, 'raised'),
                        (QPalette.ToolTipText, 'text')):
        palette.setColor(role, QColor(TOKENS[color]))
    app.setPalette(palette)
    t = TOKENS
    app.setStyleSheet(f'''
    QWidget {{ color:{t['text']}; }}
    QMainWindow, QDialog {{ background:{t['background']}; }}
    QLabel[secondary="true"] {{ color:{t['secondary']}; }}
    QLabel[pageTitle="true"] {{ font-size:22px; font-weight:600; }}
    QFrame[panel="true"], QGroupBox {{ background:{t['surface']}; border:1px solid {t['border']}; border-radius:12px; }}
    QGroupBox {{ margin-top:14px; padding:12px; }}
    QGroupBox::title {{ subcontrol-origin:margin; left:12px; }}
    QPushButton, QToolButton, QComboBox, QLineEdit {{ background:{t['raised']}; border:1px solid {t['border']}; border-radius:8px; padding:7px 10px; }}
    QPushButton:hover, QToolButton:hover {{ background:{t['hover']}; }}
    QPushButton:checked, QToolButton:checked {{ background:{t['hover']}; border-color:{t['secondary']}; }}
    QPushButton[primary="true"] {{ color:{t['accent']}; border-color:{t['accent']}; }}
    QPushButton[navigation="true"] {{ text-align:left; background:transparent; border:0; border-left:2px solid transparent; border-radius:5px; padding:10px 8px; }}
    QPushButton[navigation="true"]:hover {{ background:{t['surface']}; }}
    QPushButton[navigation="true"]:checked {{ background:{t['raised']}; border-left:2px solid {t['accent']}; }}
    QPushButton[destructive="true"] {{ color:{t['red']}; }}
    QWidget:disabled {{ color:{t['muted']}; }}
    QLineEdit:focus, QPlainTextEdit:focus, QPushButton:focus, QComboBox:focus, QTableView:focus, QTreeView:focus {{ border:1px solid {t['accent']}; }}
    QComboBox QAbstractItemView, QMenu {{ background:{t['raised']}; selection-background-color:{t['hover']}; selection-color:{t['text']}; border:1px solid {t['border']}; padding:5px; }}
    QMenu::item {{ padding:7px 16px; }}
    QTableView, QTreeView, QPlainTextEdit {{ background:{t['surface']}; border:1px solid {t['border']}; border-radius:8px; selection-background-color:{t['hover']}; selection-color:{t['text']}; }}
    QTableView::item, QTreeView::item {{ padding:6px; }}
    QHeaderView::section {{ background:{t['background']}; color:{t['secondary']}; border:0; border-bottom:1px solid {t['border']}; padding:9px 6px; }}
    QScrollBar:vertical {{ background:{t['surface']}; width:12px; margin:0; }}
    QScrollBar:horizontal {{ background:{t['surface']}; height:12px; margin:0; }}
    QScrollBar::handle {{ background:{t['muted']}; border-radius:5px; min-height:24px; min-width:24px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width:0; height:0; }}
    QSplitter::handle {{ background:{t['border']}; }}
    QTabWidget::pane {{ border:0; }}
    QTabBar::tab {{ padding:9px 7px; color:{t['secondary']}; }}
    QTabBar::tab:selected {{ background:{t['raised']}; color:{t['text']}; border-bottom:2px solid {t['accent']}; }}
    QProgressBar {{ border:0; background:{t['raised']}; border-radius:4px; min-height:6px; }}
    QProgressBar::chunk {{ background:{t['accent']}; border-radius:4px; }}
    ''')
