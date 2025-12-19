import os
import re
from PySide6.QtCore import QObject, QThread, Signal
from src.ai.analyzer import PesPlanusAnalyzer

class BatchItem:
    def __init__(self, path):
        self.path = path
        self.filename = os.path.basename(path)
        self.status = "Bekliyor" # Bekliyor, İşleniyor, Tamamlandı, Hata
        self.patient_name = ""
        self.patient_id = ""
        self.side = "" # L veya R
        self.angle = 0.0
        self.diagnosis = ""
        self.lines = [] # Analysis lines for correction
        self.is_confirmed = False
        self.error_msg = ""
        
        self.parse_metadata()

    def parse_metadata(self):
        """
        Attempts to extract metadata from filename.
        Format expectation: Name_Surname_ID_Side.ext or similar.
        """
        try:
            name_part = os.path.splitext(self.filename)[0]
            parts = re.split(r'[_\-\s]+', name_part)
            
            # Simple heuristic
            self.side = "?"
            for p in parts:
                if p.upper() in ["L", "SOL", "LEFT"]:
                    self.side = "L"
                elif p.upper() in ["R", "SAG", "RIGHT", "SAĞ"]:
                    self.side = "R"
            
            # Assuming ID is a number sequence
            id_candidates = [p for p in parts if p.isdigit()]
            self.patient_id = id_candidates[0] if id_candidates else "?"
            
            # Name: Everything that is not ID or Side
            name_parts = [p for p in parts if p not in id_candidates and p.upper() not in ["L", "R", "SOL", "SAG", "RIGHT", "LEFT", "SAĞ"]]
            self.patient_name = " ".join(name_parts)
            
        except Exception:
            self.patient_name = self.filename
            self.patient_id = "-"
            self.side = "-"

class BatchWorker(QThread):
    progress = Signal(int, int) # current, total
    item_finished = Signal(str, object) # path, BatchItem (updated)
    finished_all = Signal()
    
    def __init__(self, items, analyzer=None):
        super().__init__()
        self.items = items # List of BatchItem
        self.analyzer = analyzer or PesPlanusAnalyzer()
        self.is_running = True

    def run(self):
        total = len(self.items)
        for i, item in enumerate(self.items):
            if not self.is_running:
                break
                
            if item.status == "Tamamlandı" or item.status == "Hata":
                self.progress.emit(i+1, total)
                continue
                
            try:
                item.status = "İşleniyor"
                result = self.analyzer.analyze(item.path)
                
                if "error" in result:
                    item.status = "Hata"
                    item.error_msg = result["error"]
                else:
                    item.status = "Tamamlandı"
                    item.angle = result["angle"]
                    item.diagnosis = result["diagnosis"]
                    item.lines = result["lines"]
            except Exception as e:
                item.status = "Hata"
                item.error_msg = str(e)
                
            self.item_finished.emit(item.path, item)
            self.progress.emit(i+1, total)
            
        self.finished_all.emit()

    def stop(self):
        self.is_running = False
