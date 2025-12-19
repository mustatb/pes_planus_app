import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QTabWidget)
from src.ui.styles import DARK_THEME
from src.ui.modules.pes_planus import PesPlanusWidget
from src.ui.modules.free_drawing import FreeDrawingWidget
from src.ui.modules.batch_analysis import BatchAnalysisWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pes Planus Analiz & Medical Workstation")
        self.resize(1400, 900)
        self.setStyleSheet(DARK_THEME)
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 0; }
            QTabBar::tab { 
                background: #2d2d30; 
                color: #ccc; 
                padding: 10px 20px; 
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected { 
                background: #3e3e42; 
                color: white; 
                font-weight: bold;
            }
            QTabBar::tab:hover { background: #3e3e42; }
        """)
        
        # Modules
        self.pes_planus_widget = PesPlanusWidget()
        self.free_drawing_widget = FreeDrawingWidget()
        self.batch_analysis_widget = BatchAnalysisWidget()
        
        self.tabs.addTab(self.pes_planus_widget, "Pes Planus Analizi")
        self.tabs.addTab(self.batch_analysis_widget, "Toplu Analiz")
        self.tabs.addTab(self.free_drawing_widget, "Serbest Çizim & Cetvel")
        
        layout.addWidget(self.tabs)

