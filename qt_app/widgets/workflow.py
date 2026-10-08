"""Compact Workflow cards/guide using native Qt widgets and existing glyphs."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QHBoxLayout,QVBoxLayout,QLabel,QGridLayout
from qt_app.icons import icon

PANEL='background:#1D2026; border:1px solid #303C49; border-radius:7px;'
BLUE_BUTTON='''QPushButton {background:#2166BB;color:#FFFFFF;border:1px solid #438DF0;border-radius:6px;padding:8px 12px;text-align:left;font-weight:600;}
QPushButton:hover {background:#2975CD;} QPushButton:disabled {background:#23272E;color:#818B98;border:1px solid #30343C;}'''


class SummaryCard(QWidget):
    def __init__(self,title,glyph,color):
        super().__init__();self.setAttribute(Qt.WA_StyledBackground,True);self.setObjectName('workflowSummary');self.setStyleSheet('QWidget#workflowSummary {'+PANEL+'}')
        layout=QHBoxLayout(self);layout.setContentsMargins(12,8,12,8)
        image=QLabel();image.setPixmap(icon(glyph,color).pixmap(28,28));layout.addWidget(image)
        values=QVBoxLayout();values.setSpacing(2);self.number=QLabel('0');self.number.setStyleSheet('font-size:21px;font-weight:600;')
        self.caption=QLabel(title);self.caption.setProperty('secondary',True);values.addWidget(self.number);values.addWidget(self.caption)
        layout.addLayout(values);layout.addStretch();self.setMinimumHeight(65);self.setAccessibleName(title)

    def setText(self,text):
        title,value=text.rsplit(' ',1);self.number.setText(value);self.caption.setText(title)


class Guide(QWidget):
    def __init__(self):
        super().__init__();self.setAttribute(Qt.WA_StyledBackground,True);self.setObjectName('workflowGuide');self.setStyleSheet('QWidget#workflowGuide {'+PANEL+'}')
        layout=QGridLayout(self);layout.setContentsMargins(10,10,10,10);self.steps=[]
        for index,(title,caption) in enumerate([('Intake','Import titles'),('Run','Process & match'),('Export','Create packet'),
                ('Fix','Preview & Apply'),('Re-Audit','Validate changes'),('Accept','Approve eligible')]):
            number=QLabel(str(index+1));number.setAlignment(Qt.AlignCenter);number.setFixedSize(29,29)
            name=QLabel(title);name.setStyleSheet('font-weight:600;');detail=QLabel(caption);detail.setProperty('secondary',True)
            detail.setStyleSheet('font-size:10px;');detail.setWordWrap(True)
            step=QWidget();row=QHBoxLayout(step);row.setContentsMargins(0,0,0,0);row.addWidget(number)
            text=QVBoxLayout();text.setSpacing(2);text.addWidget(name);text.addWidget(detail);row.addLayout(text)
            layout.addWidget(step,0,index);self.steps.append(number)
        self.highlight(None)

    def highlight(self,index):
        for i,number in enumerate(self.steps):
            number.setStyleSheet('border:2px solid #438DF0;border-radius:14px;color:#D5E9FF;'+
                ('background:#2166BB;' if i==index else 'background:#202936;'))
