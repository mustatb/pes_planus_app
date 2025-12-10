# Modern Slate Theme QSS

DARK_THEME = """
/* Global Reset */
* {
    font-family: 'Segoe UI', 'Roboto', sans-serif;
    font-size: 14px;
    color: #dfe6e9; /* Soft White */
}

/* Main Window Background */
QMainWindow, QWidget {
    background-color: #2d3436; /* Slate Gray */
}

/* Toolbar Styling */
QToolBar {
    background-color: #353b48; /* Lighter Slate */
    border-bottom: 2px solid #2d3436;
    padding: 10px;
    spacing: 15px;
}

QToolButton {
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 8px 12px;
    color: #b2bec3;
    font-weight: 600;
}

QToolButton:hover {
    background-color: #636e72;
    color: white;
}

QToolButton:checked {
    background-color: #0984e3; /* Electron Blue */
    color: white;
    border: 1px solid #0984e3;
}

/* Canvas Area */
QGraphicsView {
    background-color: #1e272e; /* Very Dark Slate */
    border: 2px solid #353b48;
    border-radius: 8px;
}

/* Right Panel Group Box */
QGroupBox {
    background-color: #353b48;
    border: 1px solid #636e72;
    border-radius: 8px;
    margin-top: 24px;
    font-weight: bold;
    color: #74b9ff; /* Soft Blue */
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
    left: 15px;
    background-color: #353b48; /* Match groupbox bg */
}

/* Labels */
QLabel {
    color: #dfe6e9;
    padding: 2px;
}

/* Status Bar */
QStatusBar {
    background-color: #0984e3;
    color: white;
    font-weight: bold;
}

/* Buttons */
QPushButton {
    background-color: #636e72;
    border: none;
    color: white;
    padding: 10px 20px;
    border-radius: 6px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #b2bec3;
    color: #2d3436;
}

QPushButton:pressed {
    background-color: #0984e3;
    color: white;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #2d3436;
    width: 12px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #636e72;
    min-height: 20px;
    border-radius: 6px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
