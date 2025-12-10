import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QFileDialog, QMessageBox, QToolBar, QGroupBox, QListWidget, QListWidgetItem, QInputDialog, QColorDialog, QCheckBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QActionGroup, QImage, QPixmap

from src.ui.canvas import DrawingCanvas
from src.core.dicom_loader import load_dicom_array, load_image_array

class FreeDrawingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_array = None
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
        
        # Toolbar
        self.toolbar = QToolBar("Araçlar")
        self.toolbar.setIconSize(QSize(24, 24))
        canvas_layout.addWidget(self.toolbar)
        
        self.canvas = DrawingCanvas()
        self.canvas.selection_changed.connect(self.on_selection_changed)
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
        lbl_header = QLabel("SERBEST ÇİZİM")
        lbl_header.setStyleSheet("color: #666; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        side_layout.addWidget(lbl_header)
        
        # Object List
        grp_objects = QGroupBox("Nesneler")
        obj_layout = QVBoxLayout()
        self.list_objects = QListWidget()
        self.list_objects.itemDoubleClicked.connect(self.rename_object)
        obj_layout.addWidget(self.list_objects)
        
        # Helper label
        lbl_hint = QLabel("Yeniden adlandırmak için çift tıklayın.")
        lbl_hint.setStyleSheet("color: #888; font-size: 10px;")
        obj_layout.addWidget(lbl_hint)
        
        grp_objects.setLayout(obj_layout)
        side_layout.addWidget(grp_objects)
        
        # Status Box
        grp_status = QGroupBox("Durum")
        status_layout = QVBoxLayout()
        self.lbl_status = QLabel("Görüntü bekleniyor...")
        self.lbl_status.setWordWrap(True)
        status_layout.addWidget(self.lbl_status)
        grp_status.setLayout(status_layout)
        side_layout.addWidget(grp_status)
        
        # Selection Properties
        self.grp_properties = QGroupBox("Seçim Özellikleri")
        self.grp_properties.hide()
        prop_layout = QVBoxLayout()
        
        self.lbl_sel_name = QLabel()
        prop_layout.addWidget(self.lbl_sel_name)
        
        self.chk_show_length = QCheckBox("Uzunluğu Göster")
        self.chk_show_length.toggled.connect(self.toggle_length_display)
        prop_layout.addWidget(self.chk_show_length)
        
        self.lbl_sel_angle = QLabel()
        self.lbl_sel_angle.setStyleSheet("color: yellow; font-weight: bold;")
        prop_layout.addWidget(self.lbl_sel_angle)
        
        self.grp_properties.setLayout(prop_layout)
        side_layout.addWidget(self.grp_properties)
        
        side_layout.addStretch()
        
        main_layout.addWidget(side_panel)
        
        self.setup_toolbar()
        
        # Timer or Signal to update object list
        # For now we use a manual refresh button
        
        btn_refresh = QAction("🔄 Listeyi Güncelle", self)
        btn_refresh.triggered.connect(self.update_object_list)
        # Add to toolbar? No, side panel.
        
        from PySide6.QtWidgets import QPushButton
        self.btn_refresh = QPushButton("Listeyi Güncelle")
        self.btn_refresh.clicked.connect(self.update_object_list)
        obj_layout.addWidget(self.btn_refresh)

    def setup_toolbar(self):
        # File Actions
        action_open = QAction("📂 Dosya Aç", self)
        action_open.triggered.connect(self.open_file)
        self.toolbar.addAction(action_open)
        
        action_new = QAction("📄 Boş Tuval", self)
        action_new.triggered.connect(self.new_blank_canvas)
        self.toolbar.addAction(action_new)
        
        self.toolbar.addSeparator()
        
        # Drawing Tools
        self.action_line = QAction("✏️ Çizgi", self)
        self.action_line.setCheckable(True)
        self.action_line.triggered.connect(lambda: self.set_tool("free_line"))
        self.toolbar.addAction(self.action_line)
        
        self.action_ruler = QAction("📏 Cetvel", self)
        self.action_ruler.setCheckable(True)
        self.action_ruler.triggered.connect(lambda: self.set_tool("ruler"))
        self.toolbar.addAction(self.action_ruler)
        
        self.action_angle = QAction("📐 Açı", self)
        self.action_angle.setCheckable(True)
        self.action_angle.triggered.connect(lambda: self.set_tool("angle"))
        self.toolbar.addAction(self.action_angle)
        
        self.toolbar.addSeparator()
        
        # Color Picker
        self.action_color = QAction("🎨 Renk", self)
        self.action_color.triggered.connect(self.choose_color)
        self.toolbar.addAction(self.action_color)
        
        self.tool_group = QActionGroup(self)
        self.tool_group.addAction(self.action_line)
        self.tool_group.addAction(self.action_ruler)
        self.tool_group.addAction(self.action_angle)
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
        
        action_delete = QAction("🗑️ Sil", self)
        action_delete.setShortcut("Delete")
        action_delete.triggered.connect(self.canvas.delete_selected_items)
        self.toolbar.addAction(action_delete)
        
        self.toolbar.addSeparator()
        
        action_reset = QAction("🔄 Temizle", self)
        action_reset.triggered.connect(self.reset_drawing)
        self.toolbar.addAction(action_reset)

    def set_tool(self, tool_name):
        self.canvas.set_tool(tool_name)
        if tool_name == "free_line":
            self.lbl_status.setText("Çizgi Aracı\nBaşlangıç ve bitiş noktalarına tıklayın.")
        elif tool_name == "ruler":
            self.lbl_status.setText("Cetvel Aracı\nÖlçüm yapmak için iki noktaya tıklayın.")
        elif tool_name == "angle":
            self.lbl_status.setText("Açı Aracı\nÖlçüm yapmak için iki çizgiye tıklayın.")

    def new_blank_canvas(self):
        self.canvas.create_blank_canvas()
        self.reset_drawing()
        self.lbl_status.setText("Boş tuval oluşturuldu.\nÇizim yapabilirsiniz.")

    def choose_color(self):
        color = QColorDialog.getColor(self.canvas.current_color, self, "Renk Seç")
        if color.isValid():
            self.canvas.current_color = color

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
        
        height, width = arr.shape
        bytes_per_line = width
        q_img = QImage(arr.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
        self.canvas.set_image(QPixmap.fromImage(q_img))
        
        self.reset_drawing()
        self.lbl_status.setText("Görüntü yüklendi.\nÇizim için araç seçin.")

    def reset_drawing(self):
        self.canvas.reset_drawing()
        self.list_objects.clear()
        if self.tool_group.checkedAction():
            self.tool_group.checkedAction().setChecked(False)
        self.canvas.set_tool(None)

    def update_object_list(self):
        self.list_objects.clear()
        for i, item in enumerate(self.canvas.custom_items):
            label = f"{item.name}"
            if item.is_ruler:
                # Get length from label text if possible, or recalculate
                # item.label.toPlainText() might contain "123.4 px"
                label += f" ({item.label.toPlainText()})"
            
            list_item = QListWidgetItem(label)
            list_item.setData(Qt.ItemDataRole.UserRole, i) # Store index
            self.list_objects.addItem(list_item)

    def rename_object(self, item):
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx < len(self.canvas.custom_items):
            custom_item = self.canvas.custom_items[idx]
            new_name, ok = QInputDialog.getText(self, "Yeniden Adlandır", "Yeni isim:", text=custom_item.name)
            if ok and new_name:
                custom_item.name = new_name
                custom_item.update_geometry() # Updates label
                custom_item.update_geometry() # Updates label
                self.update_object_list()

    def on_selection_changed(self, selected_items):
        if not selected_items:
            self.grp_properties.hide()
            return
            
        self.grp_properties.show()
        
        # Single Selection
        if len(selected_items) == 1:
            item = selected_items[0]
            self.lbl_sel_name.setText(f"İsim: {item.name}")
            self.chk_show_length.blockSignals(True)
            self.chk_show_length.setChecked(item.is_ruler) # Reuse is_ruler logic for showing length
            self.chk_show_length.blockSignals(False)
            self.lbl_sel_angle.hide()
            
        # Two Items Selection (Angle)
        elif len(selected_items) == 2:
            self.lbl_sel_name.setText(f"Seçili: {len(selected_items)} Öğe")
            self.lbl_sel_angle.show()
            
            # Calculate angle
            line1 = selected_items[0]
            line2 = selected_items[1]
            
            l1_p1 = line1.point1.pos()
            l1_p2 = line1.point2.pos()
            l2_p1 = line2.point1.pos()
            l2_p2 = line2.point2.pos()
            
            v1 = l1_p2 - l1_p1
            v2 = l2_p2 - l2_p1
            
            import math
            angle1 = math.atan2(v1.y(), v1.x())
            angle2 = math.atan2(v2.y(), v2.x())
            
            angle_deg = math.degrees(abs(angle1 - angle2))
            if angle_deg > 180: angle_deg = 360 - angle_deg
            
            self.lbl_sel_angle.setText(f"Açı: {angle_deg:.1f}°")
            
        else:
            self.lbl_sel_name.setText(f"Seçili: {len(selected_items)} Öğe")
            self.lbl_sel_angle.hide()

    def toggle_length_display(self, checked):
        # Apply to all selected items
        for item in self.canvas.custom_items:
            if item.is_selected:
                item.is_ruler = checked
                item.update_geometry()
        self.update_object_list()
