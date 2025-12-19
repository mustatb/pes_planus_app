import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFileDialog, QMessageBox, QToolBar, QGroupBox, QComboBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QActionGroup, QImage, QPixmap

from src.ui.canvas import DrawingCanvas, DraggablePoint
from src.core.dicom_loader import load_dicom_array, load_image_array
from src.core.geometry import calculate_angle, get_angle_classification
from src.ai.analyzer import PesPlanusAnalyzer

class PesPlanusWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_array = None
        self.analyzer = None # Lazy load
            
        self.init_ui()
        
    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Canvas Area (Left)
        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(0)
        
        # Toolbar (Moved inside widget for this module)
        self.toolbar = QToolBar("Araçlar")
        self.toolbar.setIconSize(QSize(24, 24))
        canvas_layout.addWidget(self.toolbar)
        
        self.canvas = DrawingCanvas()
        self.canvas.points_updated.connect(self.on_points_updated)
        canvas_layout.addWidget(self.canvas)
        
        main_layout.addWidget(canvas_container, stretch=4)
        
        # 2. Side Panel (Right)
        side_panel = QWidget()
        side_panel.setFixedWidth(320)
        side_panel.setStyleSheet("background-color: #252526; border-left: 1px solid #3e3e42;")
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(20, 20, 20, 20)
        side_layout.setSpacing(20)
        
        # Header
        lbl_header = QLabel("ANALİZ PANELİ")
        lbl_header.setStyleSheet("color: #666; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        side_layout.addWidget(lbl_header)
        
        # Mode Selection
        grp_mode = QGroupBox("Analiz Modu")
        mode_layout = QVBoxLayout()
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Kalkaneal Eğim Açısı", "Meary's Açısı"])
        self.combo_mode.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.combo_mode)
        grp_mode.setLayout(mode_layout)
        side_layout.addWidget(grp_mode)
        
        # Patient Info Box
        grp_patient = QGroupBox("Hasta / Dosya Bilgileri")
        patient_layout = QVBoxLayout()
        self.lbl_patient_info = QLabel("Bilgi yok")
        self.lbl_patient_info.setStyleSheet("font-size: 12px; color: #b2bec3;")
        patient_layout.addWidget(self.lbl_patient_info)
        grp_patient.setLayout(patient_layout)
        side_layout.addWidget(grp_patient)
        
        # AI Analysis Section
        grp_ai = QGroupBox("Yapay Zeka")
        ai_layout = QVBoxLayout()
        
        from PySide6.QtWidgets import QPushButton
        self.btn_ai = QPushButton("🤖 Otomatik Analiz")
        self.btn_ai.setMinimumHeight(40)
        self.btn_ai.setStyleSheet("""
            QPushButton {
                background-color: #6c5ce7; 
                color: white; 
                font-weight: bold; 
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #a29bfe; }
            QPushButton:pressed { background-color: #4834d4; }
        """)
        self.btn_ai.clicked.connect(self.run_ai_analysis)
        ai_layout.addWidget(self.btn_ai)
        
        grp_ai.setLayout(ai_layout)
        side_layout.addWidget(grp_ai)

        # Status Box
        grp_status = QGroupBox("Durum")
        status_layout = QVBoxLayout()
        self.lbl_status = QLabel("Görüntü bekleniyor...")
        self.lbl_status.setWordWrap(True)
        status_layout.addWidget(self.lbl_status)
        grp_status.setLayout(status_layout)
        side_layout.addWidget(grp_status)
        
        # Results Box
        grp_results = QGroupBox("Ölçüm Sonuçları")
        results_layout = QVBoxLayout()
        
        self.lbl_angle_title = QLabel("Kalkaneal Eğim Açısı")
        self.lbl_angle_title.setStyleSheet("color: #aaa; font-size: 12px;")
        results_layout.addWidget(self.lbl_angle_title)
        
        self.lbl_angle = QLabel("--")
        self.lbl_angle.setStyleSheet("font-size: 36px; font-weight: bold; color: #007acc;")
        self.lbl_angle.setAlignment(Qt.AlignmentFlag.AlignRight)
        results_layout.addWidget(self.lbl_angle)
        
        self.lbl_class = QLabel("")
        self.lbl_class.setAlignment(Qt.AlignmentFlag.AlignRight)
        results_layout.addWidget(self.lbl_class)
        
        grp_results.setLayout(results_layout)
        side_layout.addWidget(grp_results)
        
        # Instructions
        lbl_help = QLabel("KULLANIM:\n\n1. Dosya Açın\n2. Araç Seçin\n3. Çizim Yapın\n\n* Zoom: Mouse Tekerleği\n* Pan: Sağ Tık + Sürükle\n* Hassas: Seç + Ok Tuşları")
        lbl_help.setStyleSheet("color: #888; font-size: 12px;")
        side_layout.addWidget(lbl_help)
        
        side_layout.addStretch()
        
        main_layout.addWidget(side_panel)
        
        self.setup_toolbar()
        
    def setup_toolbar(self):
        # File Actions
        action_open = QAction("📂 Dosya Aç", self)
        action_open.triggered.connect(self.open_file)
        self.toolbar.addAction(action_open)
        
        self.toolbar.addSeparator()
        
        # Drawing Tools
        self.action_ground = QAction("Zemin (Mavi)", self)
        self.action_ground.setCheckable(True)
        self.action_ground.triggered.connect(lambda: self.set_tool("ground"))
        self.toolbar.addAction(self.action_ground)
        
        self.action_calc = QAction("Kalkaneus (Pembe)", self)
        self.action_calc.setCheckable(True)
        self.action_calc.triggered.connect(lambda: self.set_tool("calcaneus"))
        self.toolbar.addAction(self.action_calc)
        
        self.tool_group = QActionGroup(self)
        self.tool_group.addAction(self.action_ground)
        self.tool_group.addAction(self.action_calc)
        self.tool_group.setExclusive(True)
        
        self.toolbar.addSeparator()
        
        # Zoom Controls
        action_zoom_in = QAction("➕ Yakınlaş", self)
        action_zoom_in.triggered.connect(lambda: self.canvas.zoom_in())
        self.toolbar.addAction(action_zoom_in)
        
        action_zoom_out = QAction("➖ Uzaklaş", self)
        action_zoom_out.triggered.connect(lambda: self.canvas.zoom_out())
        self.toolbar.addAction(action_zoom_out)
        
        action_fit = QAction("⛶ Sığdır", self)
        action_fit.triggered.connect(lambda: self.canvas.fit_view())
        self.toolbar.addAction(action_fit)
        
        self.toolbar.addSeparator()
        
        action_reset = QAction("🔄 Temizle", self)
        action_reset.triggered.connect(self.reset_drawing)
        self.toolbar.addAction(action_reset)

    def set_tool(self, tool_name):
        self.canvas.set_tool(tool_name)
        mode = self.combo_mode.currentText()
        
        if tool_name == "ground":
            if "Meary" in mode:
                self.lbl_status.setText("Talus Ekseni (Mavi)\n2 nokta işaretleyin.")
            else:
                self.lbl_status.setText("Zemin Doğrusu (Mavi)\n2 nokta işaretleyin.")
        elif tool_name == "calcaneus":
            if "Meary" in mode:
                self.lbl_status.setText("1. Metatarsal Eksen (Pembe)\n2 nokta işaretleyin.")
            else:
                self.lbl_status.setText("Kalkaneus Doğrusu (Pembe)\n2 nokta işaretleyin.")

    def on_mode_changed(self, index):
        mode = self.combo_mode.currentText()
        if "Meary" in mode:
            self.lbl_angle_title.setText("Meary's Açısı")
            self.action_ground.setText("Talus (Mavi)")
            self.action_calc.setText("1. Metatarsal (Pembe)")
        else:
            self.lbl_angle_title.setText("Kalkaneal Eğim Açısı")
            self.action_ground.setText("Zemin (Mavi)")
            self.action_calc.setText("Kalkaneus (Pembe)")
            
        self.reset_drawing()

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Dosya Aç", "", "Images (*.dcm *.png *.jpg *.jpeg)")
        if not file_name:
            return
            
        ext = os.path.splitext(file_name)[1].lower()
        if ext == '.dcm':
            arr, metadata = load_dicom_array(file_name)
        else:
            arr, metadata = load_image_array(file_name)
            
        if arr is None:
            QMessageBox.critical(self, "Hata", "Dosya yüklenemedi!")
            return
            
        self.current_image_array = arr
        
        # Display Metadata
        if metadata:
            info_text = ""
            for k, v in metadata.items():
                info_text += f"<b>{k}:</b> {v}<br>"
            self.lbl_patient_info.setText(info_text)
        
        height, width = arr.shape
        bytes_per_line = width
        q_img = QImage(arr.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
        self.canvas.set_image(QPixmap.fromImage(q_img))
        
        self.reset_drawing()
        self.lbl_status.setText("Görüntü yüklendi.\nAnaliz için araç seçin.")

    def reset_drawing(self):
        self.canvas.reset_drawing()
        self.lbl_angle.setText("--")
        self.lbl_class.setText("")
        if self.tool_group.checkedAction():
            self.tool_group.checkedAction().setChecked(False)
        self.canvas.set_tool(None)

    def run_ai_analysis(self):
        if self.current_image_array is None:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bir görüntü yükleyin.")
            return

        self.lbl_status.setText("🤖 Analiz yapılıyor, lütfen bekleyin...")
        self.btn_ai.setEnabled(False)
        self.setCursor(Qt.CursorShape.WaitCursor)
        
        from PySide6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Lazy Load
        if not self.analyzer:
            self.lbl_status.setText("📦 Model dosyaları yükleniyor (İlk çalıştırma biraz sürebilir)...")
            QApplication.processEvents()
            try:
                self.analyzer = PesPlanusAnalyzer()
            except Exception as e:
                self.btn_ai.setEnabled(True)
                self.setCursor(Qt.CursorShape.ArrowCursor)
                QMessageBox.critical(self, "Hata", f"Yapay zeka modeli yüklenemedi:\n{e}")
                self.lbl_status.setText("Model yükleme hatası.")
                return

        try:
            # 1. Run Analysis
            result = self.analyzer.analyze(self.current_image_array)
            
            if "error" in result:
                QMessageBox.warning(self, "Analiz Hatası", result["error"])
                self.lbl_status.setText(f"Hata: {result['error']}")
            else:
                # 2. Reset and set data
                self.reset_drawing()
                
                # Get Lines from result
                lines = result.get("lines", [])
                if len(lines) >= 2:
                    calc_line_coords = lines[0]
                    ground_line_coords = lines[1]
                    
                    c1, c2 = calc_line_coords
                    g1, g2 = ground_line_coords
                     
                    # Calcaneus (Magenta)
                    from src.ui.canvas import DraggablePoint, QColor
                    
                    point_c1 = DraggablePoint(c1[0], c1[1], 6, QColor("#FF00FF"), self.canvas)
                    self.canvas.scene.addItem(point_c1)
                    self.canvas.calc_points.append(point_c1)
                    
                    point_c2 = DraggablePoint(c2[0], c2[1], 6, QColor("#FF00FF"), self.canvas)
                    self.canvas.scene.addItem(point_c2)
                    self.canvas.calc_points.append(point_c2)
                    
                    # Ground (Cyan)
                    point_g1 = DraggablePoint(g1[0], g1[1], 6, QColor("#00FFFF"), self.canvas)
                    self.canvas.scene.addItem(point_g1)
                    self.canvas.ground_points.append(point_g1)
                    
                    point_g2 = DraggablePoint(g2[0], g2[1], 6, QColor("#00FFFF"), self.canvas)
                    self.canvas.scene.addItem(point_g2)
                    self.canvas.ground_points.append(point_g2)
                    
                    # Trigger update
                    self.canvas.update_lines()
                    
                    self.lbl_status.setText(f"Analiz tamamlandı. Açı: {result['angle']}°")
                    
                    # 3. Update Classification Display
                    cat, color = get_angle_classification(result['angle'], "calcaneal")
                    self.lbl_class.setText(cat)
                    self.lbl_class.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")
                    self.lbl_angle.setText(f"{result['angle']}°")
                    self.lbl_angle.setStyleSheet(f"font-size: 36px; font-weight: bold; color: {color};")
                
        except Exception as e:
             QMessageBox.critical(self, "Hata", f"Analiz sırasında bir hata oluştu:\n{str(e)}")
             self.lbl_status.setText("Analiz hatası.")
        finally:
            self.btn_ai.setEnabled(True)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def on_points_updated(self, points):
        if len(points) == 4:
            p1 = (points[0].x(), points[0].y())
            p2 = (points[1].x(), points[1].y())
            p3 = (points[2].x(), points[2].y())
            p4 = (points[3].x(), points[3].y())
            
            mode_key = "mearys" if "Meary" in self.combo_mode.currentText() else "calcaneal"
            
            # For Calcaneal Pitch, we want strict acute angle (0-90)
            is_calcaneal = (mode_key == "calcaneal")
            angle = calculate_angle(p1, p2, p3, p4, one_sided=is_calcaneal)
            self.lbl_angle.setText(f"{angle}°")
            
            # Classification
            mode_key = "mearys" if "Meary" in self.combo_mode.currentText() else "calcaneal"
            cat, color = get_angle_classification(angle, mode_key)
            
            self.lbl_class.setText(cat)
            self.lbl_class.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")
            self.lbl_angle.setStyleSheet(f"font-size: 36px; font-weight: bold; color: {color};")
        else:
            self.lbl_angle.setText("--")
            self.lbl_class.setText("")
            self.lbl_angle.setStyleSheet("font-size: 36px; font-weight: bold; color: #74b9ff;")
