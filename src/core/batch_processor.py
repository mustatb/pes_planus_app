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
        Attempts to extract metadata from filename AND folder structure.
        Priority:
        1. Folder Structure (e.g. test/NAME_ID/SUBFOLDER/file.dcm) for Name & ID.
             - Traverse parents up to find "Name..._ID..." pattern.
        2. Filename for Side (L/R) or Name if folder fails.
        """
        try:
            # 1. Path Analysis for Name & ID
            path_parts = os.path.normpath(self.path).split(os.sep)
            
            # Strategy: Look for the parent that has a long number at the end (ID)
            # User Pattern: NAME SURNAME_ID
            # Regex: Capture everything before last underscore as Name, digits after as ID.
            
            # Words that indicate a Protocol/View name, NOT a patient name
            PROTOCOL_KEYWORDS = ["AYAK", "BASARAK", "YON", "VIEW", "LAT", "AP", "SAG", "SOL", "RIGHT", "LEFT", "TEST", "STUDY", "SERIES"]

            found_metadata = False
            # Iterate parts excluding filename, bottom-up
            # e.g. [..., "AHMET_123", "AYAK_BASARAK_123", "file.dcm"] -> Check "AYAK..." then "AHMET..."
            for part in reversed(path_parts[:-1]): 
                 # Cleaning
                 part_clean = part.replace('^', ' ').strip()
                 
                 # Regex: Match (Any Text) _ (Digits 5+)
                 # This handles "AHMET EMIR DENIZ_10216976372"
                 match = re.search(r'(.+)_(\d{5,})$', part_clean)
                 if match:
                     raw_name = match.group(1).strip()
                     raw_id = match.group(2)
                     
                     # Clean Name (remove ^, extra spaces, Title Case)
                     name_clean = re.sub(r'\s+', ' ', raw_name.replace('^', ' ')).strip().title()
                     
                     # Filter: Check if this "Name" is actually a Protocol description
                     # Check against blacklist
                     is_protocol = any(k in name_clean.upper() for k in PROTOCOL_KEYWORDS)
                     
                     if is_protocol:
                         # Likely a protocol folder (e.g. "Ayak Basarak 2 Yon"), continue searching up
                         continue
                     
                     self.patient_name = name_clean
                     self.patient_id = raw_id
                     found_metadata = True
                     break
            
            # Fallback if no folder pattern found
            if not found_metadata:
                # Use filename or immediate parent as name, but ensure not empty
                name_cand = os.path.splitext(self.filename)[0]
                # If filename is just numbers or generic, try parent
                if name_cand.isdigit() or len(name_cand) < 3:
                     if len(path_parts) > 1:
                         name_cand = path_parts[-2] # Immediate parent
                
                self.patient_name = name_cand.replace('^', ' ').replace('_', ' ').title()
                self.patient_id = "?"
                
            # 2. Side Detection (Filename/Path Heuristic - Fallback)
            # This will be overwritten by DICOM or Analysis later, but good to have initial guess.
            if self.side in ["", "?"]:
                full_check = self.path.upper()
                # Check specifics first
                if "_L" in full_check or "LEFT" in full_check or "SOL" in full_check:
                    self.side = "L"
                elif "_R" in full_check or "RIGHT" in full_check or "SAG" in full_check or "SAĞ" in full_check:
                    self.side = "R"
                
        except Exception as e:
            print(f"Metadata Parse Error: {e}")
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
                    if "side" in result and result["side"] not in ["?", ""]:
                        item.side = result["side"]
            except Exception as e:
                item.status = "Hata"
                item.error_msg = str(e)
                
            self.item_finished.emit(item.path, item)
            self.progress.emit(i+1, total)
            
        self.finished_all.emit()

    def stop(self):
        self.is_running = False
