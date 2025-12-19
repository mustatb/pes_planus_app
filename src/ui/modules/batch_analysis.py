import os
import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, 
                               QLabel, QMessageBox, QCheckBox, QDialog, QDialogButtonBox, QAbstractItemView)
from PySide6.QtCore import Qt, Signal, QSize, QThread
from PySide6.QtGui import QIcon, QColor

from src.core.batch_processor import BatchWorker, BatchItem
from src.ui.modules.pes_planus import PesPlanusWidget
from src.core.dicom_loader import load_image_array, load_dicom_array
from src.core.geometry import calculate_angle, get_angle_classification

class ReviewDialog(QDialog):
    def __init__(self, batch_item, parent=None):
        super().__init__(parent)
        self.batch_item = batch_item
        self.setWindowTitle(f"İnceleme: {batch_item.patient_name} ({batch_item.side})")
        self.resize(1200, 800)
        
        layout = QVBoxLayout(self)
        
        # Determine ROI / Image logic
        # For simplicity, load the full image in the PesPlanusWidget
        self.analyzer_widget = PesPlanusWidget(self)
        
        # Hide unnecessary buttons for Review Mode
        self.analyzer_widget.btn_ai.setVisible(False)
        self.analyzer_widget.toolbar.setVisible(True) # Keep toolbar for zoom/pan
        # We might want to hide Open File too, but toolbar is one unit. 
        # It's okay if user opens another file, it just won't save correctly to batch item.
        
        layout.addWidget(self.analyzer_widget)
        
        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
        self.load_data()
        
    def load_data(self):
        # Load Image
        ext = os.path.splitext(self.batch_item.path)[1].lower()
        if ext == '.dcm':
            arr, meta = load_dicom_array(self.batch_item.path)
        else:
            arr, meta = load_image_array(self.batch_item.path)
            
        if arr is None:
            QMessageBox.critical(self, "Hata", "Görüntü yüklenemedi.")
            self.reject()
            return

        # Manually set image
        self.analyzer_widget.current_image_array = arr
        height, width = arr.shape
        from PySide6.QtGui import QImage, QPixmap
        q_img = QImage(arr.data, width, height, width, QImage.Format.Format_Grayscale8)
        self.analyzer_widget.canvas.set_image(QPixmap.fromImage(q_img))
        
        # Load Lines
        if self.batch_item.lines:
             # Construct result dict for display_results
             res = {
                 "lines": self.batch_item.lines,
                 "angle": self.batch_item.angle
             }
             self.analyzer_widget.display_results(res)
        else:
            self.analyzer_widget.reset_drawing()

    def get_updated_data(self):
        # Extract points from canvas
        if len(self.analyzer_widget.canvas.calc_points) == 2 and len(self.analyzer_widget.canvas.ground_points) == 2:
            c1 = self.analyzer_widget.canvas.calc_points[0].pos()
            c2 = self.analyzer_widget.canvas.calc_points[1].pos()
            g1 = self.analyzer_widget.canvas.ground_points[0].pos()
            g2 = self.analyzer_widget.canvas.ground_points[1].pos()
            
            lines = [
                ((c1.x(), c1.y()), (c2.x(), c2.y())),
                ((g1.x(), g1.y()), (g2.x(), g2.y()))
            ]
            
            # Recalculate angle just in case
            # Using one_sided=True for Calcaneal Pitch as per recent fixes
            angle = calculate_angle(
                (c1.x(), c1.y()), (c2.x(), c2.y()),
                (g1.x(), g1.y()), (g2.x(), g2.y()),
                one_sided=True
            )
            
            cat, _ = get_angle_classification(angle, "calcaneal")
            
            return {
                "lines": lines,
                "angle": angle,
                "diagnosis": cat
            }
        return None

class FileScannerWorker(QThread):
    found_file = Signal(str) # path
    finished_scan = Signal(int) # count
    
    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.extensions = {'.dcm', '.dicom', '.jpg', '.jpeg', '.png', '.bmp'}
        self.is_running = True

    def run(self):
        count = 0
        for root, dirs, files in os.walk(self.folder_path):
            if not self.is_running:
                break
            for file in files:
                if not self.is_running:
                    break
                ext = os.path.splitext(file)[1].lower()
                if ext in self.extensions:
                    full_path = os.path.join(root, file)
                    self.found_file.emit(full_path)
                    count += 1
        self.finished_scan.emit(count)

    def stop(self):
        self.is_running = False

class BatchAnalysisWidget(QWidget):
    patient_selected = Signal(str, str, str) # name, id, side

    def __init__(self):
        super().__init__()
        self.items = [] # List of BatchItem
        self.worker = None
        self.scanner = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 1. Top Control Bar
        top_layout = QHBoxLayout()
        
        self.lbl_count = QLabel("0 Dosya")
        self.lbl_count.setStyleSheet("font-weight: bold; color: #aaa;")
        
        btn_load = QPushButton("📂 Klasör Yükle")
        btn_load.clicked.connect(self.load_folder)
        btn_load.setStyleSheet("background-color: #0984e3; color: white;")
        
        self.btn_start = QPushButton("▶ Analizi Başlat")
        self.btn_start.clicked.connect(self.start_analysis)
        self.btn_start.setStyleSheet("background-color: #00b894; color: white;")
        self.btn_start.setEnabled(False)
        
        self.btn_stop = QPushButton("⏹ Durdur")
        self.btn_stop.clicked.connect(self.stop_analysis)
        self.btn_stop.setStyleSheet("background-color: #d63031; color: white;")
        self.btn_stop.setEnabled(False)
        
        top_layout.addWidget(btn_load)
        top_layout.addWidget(self.btn_start)
        top_layout.addWidget(self.btn_stop)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_count)
        
        layout.addLayout(top_layout)
        
        # 2. Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Onay", "Durum", "ID", "İsim", "Taraf", "Açı", "Tanı", "İşlem", "Dosya Yolu"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch) # Name stretches
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.hideColumn(8) # Hide Path
        self.table.itemClicked.connect(self.on_table_clicked)
        
        layout.addWidget(self.table)
        
        # 3. Bottom Bar
        bottom_layout = QHBoxLayout()
        
        btn_export = QPushButton("📊 Excel'e Aktar")
        btn_export.clicked.connect(self.export_excel)
        
        btn_report = QPushButton("📑 Rapor Oluştur (Zip)")
        btn_report.clicked.connect(self.create_report) # Placeholder
        
        bottom_layout.addWidget(btn_export)
        bottom_layout.addWidget(btn_report)
        bottom_layout.addStretch()
        
        layout.addLayout(bottom_layout)
    
    def on_table_clicked(self, item):
        row = item.row()
        path = self.table.item(row, 8).text()
        # Find item
        batch_item = next((i for i in self.items if i.path == path), None)
        if batch_item:
            self.patient_selected.emit(batch_item.patient_name, batch_item.patient_id, batch_item.side)

    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç")
        if not folder:
            return
            
        self.items = []
        self.table.setRowCount(0)
        self.lbl_count.setText("Taranıyor...")
        self.btn_start.setEnabled(False)
        
        # Start Scanner Thread
        self.scanner = FileScannerWorker(folder)
        self.scanner.found_file.connect(self.on_file_found)
        self.scanner.finished_scan.connect(self.on_scan_finished)
        self.scanner.start()

    def on_file_found(self, path):
        item = BatchItem(path)
        self.items.append(item)
        self.add_row(item)
        self.lbl_count.setText(f"{len(self.items)} dosya bulundu...")

    def on_scan_finished(self, count):
        self.lbl_count.setText(f"{count} Dosya Hazır")
        if count > 0:
            self.btn_start.setEnabled(True)
        else:
            QMessageBox.information(self, "Bilgi", "Seçilen klasörde uygun görsel bulunamadı.")
            
    def add_row(self, item: BatchItem):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        # 0. Checkbox
        chk_widget = QWidget()
        chk_layout = QHBoxLayout(chk_widget)
        chk_layout.setContentsMargins(0,0,0,0)
        chk_layout.setAlignment(Qt.AlignCenter)
        chk = QCheckBox()
        chk.setChecked(item.is_confirmed)
        chk.stateChanged.connect(lambda s, i=item: self.update_confirm(i, s))
        chk_layout.addWidget(chk)
        self.table.setCellWidget(row, 0, chk_widget)
        
        # 1. Status
        self.table.setItem(row, 1, QTableWidgetItem(item.status))
        
        # 2. ID
        self.table.setItem(row, 2, QTableWidgetItem(item.patient_id))
        
        # 3. Name
        self.table.setItem(row, 3, QTableWidgetItem(item.patient_name))
        
        # 4. Side
        self.table.setItem(row, 4, QTableWidgetItem(item.side))
        
        # 5. Angle
        self.table.setItem(row, 5, QTableWidgetItem(f"{item.angle:.1f}°" if item.angle else "-"))
        
        # 6. Diagnosis
        self.table.setItem(row, 6, QTableWidgetItem(item.diagnosis))
        
        # 7. Action
        btn_review = QPushButton("Kontrol Et")
        btn_review.setStyleSheet("height: 20px; font-size: 11px;")
        btn_review.clicked.connect(lambda _, i=item: self.review_item(i))
        self.table.setCellWidget(row, 7, btn_review)
        
        # 8. Path (Hidden) - Tip: We can verify this stores the full path.
        self.table.setItem(row, 8, QTableWidgetItem(item.path))

    def update_confirm(self, item, state):
        item.is_confirmed = (state == 2) # 2 is Checked

    def start_analysis(self):
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        
        # Only process "Bekliyor" items or re-process? Re-process all or just pending?
        # Let's just create worker for all, but worker logic skips "Tamamlandı".
        # If user wants to re-run, they reload? Or we reset status.
        # For now, just run.
        
        self.worker = BatchWorker(self.items)
        self.worker.progress.connect(self.on_progress)
        self.worker.item_finished.connect(self.on_item_finished)
        self.worker.finished_all.connect(self.on_finished)
        self.worker.start()
        
    def stop_analysis(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        self.on_finished()

    def on_progress(self, current, total):
        self.lbl_count.setText(f"İşleniyor: {current}/{total}")

    def on_item_finished(self, path, updated_item):
        # Update Row
        row = -1
        # Optimize search? Linear is fine for <1000 items
        for r in range(self.table.rowCount()):
            if self.table.item(r, 8).text() == path:
                row = r
                break
        
        if row != -1:
            self.table.item(row, 1).setText(updated_item.status)
            self.table.item(row, 2).setText(updated_item.patient_id)
            self.table.item(row, 3).setText(updated_item.patient_name)
            self.table.item(row, 4).setText(updated_item.side)
            self.table.item(row, 5).setText(f"{updated_item.angle:.1f}°")
            
            # Diagnosis Coloring
            diag_item = QTableWidgetItem(updated_item.diagnosis)
            if updated_item.diagnosis == "Pes Planus":
                diag_item.setForeground(QColor("red"))
            elif updated_item.diagnosis == "Normal":
                 diag_item.setForeground(QColor("green"))
            self.table.setItem(row, 6, diag_item)
            
            # Confirm if error? No.
            if updated_item.status == "Hata":
                 self.table.item(row, 1).setBackground(QColor("#ff7675"))
            else:
                 self.table.item(row, 1).setBackground(QColor("transparent"))

    def on_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_count.setText(f"{len(self.items)} Dosya (Tamamlandı)")

    def review_item(self, item):
        dlg = ReviewDialog(item, self)
        if dlg.exec():
            # Save logic
            data = dlg.get_updated_data()
            if data:
                item.lines = data["lines"]
                item.angle = data["angle"]
                item.diagnosis = data["diagnosis"]
                item.is_confirmed = True # Auto-confirm
                
                # Update UI row immediately
                self.on_item_finished(item.path, item)
                
                # Update checkbox
                row = -1
                for r in range(self.table.rowCount()):
                    if self.table.item(r, 8).text() == item.path:
                        row = r
                        break
                if row != -1:
                    widget = self.table.cellWidget(row, 0)
                    if widget:
                         # Find checkbox in layout
                         chk = widget.findChild(QCheckBox)
                         if chk: chk.setChecked(True)

    def export_excel(self):
        if not self.items: return
        
        path, _ = QFileDialog.getSaveFileName(self, "Excel Olarak Kaydet", "", "Excel Files (*.xlsx)")
        if not path: return
        
        data = []
        for item in self.items:
            data.append({
                "Dosya Adı": item.filename,
                "Hasta ID": item.patient_id,
                "Dizi Adı": item.patient_name,
                "Taraf": item.side,
                "Açı": item.angle,
                "Tanı": item.diagnosis,
                "Durum": item.status,
                "Onaylandı": "Evet" if item.is_confirmed else "Hayır"
            })
            
        # Custom Sort: ID/Name Ascending, Side Descending (R first) or custom priority
        # Let's use a lambda: (Name, 0 if R else 1)
        data.sort(key=lambda x: (
            x["Dizi Adı"], 
            x["Hasta ID"],
            0 if x["Taraf"] in ["R", "Right", "Sag", "Sağ"] else 1
        ))

        df = pd.DataFrame(data)
        try:
            df.to_excel(path, index=False)
            QMessageBox.information(self, "Başarılı", "Excel dosyası başarıyla kaydedildi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Excel kaydedilemedi:\n{e}")

    def create_report(self):
        if not self.items: return
        
        # Select Save Path
        zip_path, _ = QFileDialog.getSaveFileName(self, "Raporu Kaydet (Zip)", "", "Zip Files (*.zip)")
        if not zip_path: return
        
        # Dependencies locally
        import zipfile
        import tempfile
        import shutil
        import cv2
        import numpy as np
        
        # Create Temp Dir
        temp_dir = tempfile.mkdtemp()
        images_dir = os.path.join(temp_dir, "Incelenen_Goruntuler")
        os.makedirs(images_dir)
        
        processed_data = [] # For Excel inside Zip
        
        try:
            # Sort items first? No, we might as well process them all then sort the list of dicts.
            # But maybe sorting `self.items` helps images appear in order in folder?
            # Let's sort the `processed_data` list before saving excel.
            
            # Process Items
            for item in self.items:
                # Filter: Only processed ones or all? Let's take anything with valid angle or status
                if item.status == "Hata" or not item.lines:
                     continue
                     
                # 1. Load Image
                try:
                    if os.path.splitext(item.path)[1].lower() in ['.dcm', '.dicom']:
                        img_arr, _ = load_dicom_array(item.path)
                    else:
                        img_arr, _ = load_image_array(item.path)
                        
                    if img_arr is None: continue
                    
                    # Convert to BGR for drawing
                    vis_img = cv2.cvtColor(img_arr, cv2.COLOR_GRAY2BGR)
                    
                    # 2. Draw Lines
                    lines = item.lines
                    if len(lines) >= 2:
                        calc_pts = lines[0] # ((x1,y1), (x2,y2))
                        ground_pts = lines[1]
                        
                        # Convert float/tuples to int points
                        c1 = (int(calc_pts[0][0]), int(calc_pts[0][1]))
                        c2 = (int(calc_pts[1][0]), int(calc_pts[1][1]))
                        g1 = (int(ground_pts[0][0]), int(ground_pts[0][1]))
                        g2 = (int(ground_pts[1][0]), int(ground_pts[1][1]))
                        
                        # Draw Calcaneus (Magenta)
                        cv2.line(vis_img, c1, c2, (255, 0, 255), 3)
                        # Draw Ground (Cyan)
                        cv2.line(vis_img, g1, g2, (255, 255, 0), 2)
                        
                        # Draw Text Box
                        angle_txt = f"{item.angle:.1f} deg"
                        diag_txt = item.diagnosis
                        
                        # Position text
                        txt_x = (c1[0] + c2[0]) // 2
                        txt_y = (c1[1] + c2[1]) // 2 - 40
                        
                        # Draw background for text
                        (tw, th), _ = cv2.getTextSize(f"{angle_txt} | {diag_txt}", cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                        cv2.rectangle(vis_img, (txt_x-10, txt_y-th-10), (txt_x+tw+10, txt_y+10), (0,0,0), -1)
                        
                        cv2.putText(vis_img, f"{angle_txt}", (txt_x, txt_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)
                        
                        # Color for diagnosis
                        d_color = (0, 255, 0) # Green default
                        if "Pes Planus" in diag_txt: d_color = (0, 0, 255) # Red (BGR)
                        elif "Sınırda" in diag_txt: d_color = (0, 165, 255) # Orange
                        
                        cv2.putText(vis_img, f"{diag_txt}", (txt_x, txt_y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, d_color, 2)
                        
                        # Draw Patient Info Top Left
                        info_txt = f"{item.patient_name} ({item.side})"
                        cv2.putText(vis_img, info_txt, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 200), 2)

                    # 3. Save Image
                    safe_name = f"{item.patient_name}_{item.patient_id}_{item.side}_{item.angle:.1f}".replace(" ", "_")
                    safe_name = "".join([c for c in safe_name if c.isalnum() or c in ('_', '-')])
                    out_path = os.path.join(images_dir, f"{safe_name}.jpg")
                    
                    # Use imencode to support unicode paths in imwrite if needed, though temp path is usually safe.
                    # But patient name might have unicode.
                    is_success, buffer = cv2.imencode(".jpg", vis_img)
                    if is_success:
                        with open(out_path, "wb") as f:
                            f.write(buffer)
                            
                    processed_data.append({
                        "Dosya": item.filename,
                        "Hasta İsim": item.patient_name,
                        "ID": item.patient_id,
                        "Taraf": item.side,
                        "Açı": item.angle,
                        "Tanı": item.diagnosis,
                        "Görsel": f"Incelenen_Goruntuler/{safe_name}.jpg"
                    })
                    
                except Exception as e:
                    print(f"Error processing {item.filename}: {e}")
                    continue
            
            # 4. Create Excel inside Temp
            if processed_data:
                # Custom Sort: ID/Name Ascending, Side Descending (R first)
                processed_data.sort(key=lambda x: (
                    x["Hasta İsim"], 
                    x["ID"],
                    0 if x["Taraf"] in ["R", "Right", "Sag", "Sağ"] else 1
                ))
                
                df = pd.DataFrame(processed_data)
                excel_path = os.path.join(temp_dir, "Ozet_Tablo.xlsx")
                df.to_excel(excel_path, index=False)
                
            # 5. Zip It
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Archive name (relative to temp_dir)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
                        
            QMessageBox.information(self, "Başarılı", f"Rapor oluşturuldu:\n{zip_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Rapor oluşturulurken hata: {e}")
        finally:
            shutil.rmtree(temp_dir)
