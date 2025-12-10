from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsItem, QGraphicsTextItem
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPen, QColor, QBrush, QCursor, QPainter, QWheelEvent, QMouseEvent, QFont, QPainterPath
import math

class DraggablePoint(QGraphicsEllipseItem):
    def __init__(self, x, y, radius, color, parent_canvas, parent_item=None):
        super().__init__(-radius, -radius, radius*2, radius*2)
        self.setPos(x, y)
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.GlobalColor.white, 1))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations) # Keep size constant when zooming
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setZValue(10) # On top
        self.parent_canvas = parent_canvas
        self.parent_item = parent_item # The line or object this point belongs to

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            self.parent_canvas.update_lines()
            self.parent_canvas.update_magnifier(self.pos())
            if self.parent_item:
                self.parent_item.update_geometry()
        return super().itemChange(change, value)

class Magnifier(QGraphicsItem):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.setZValue(20) # On top of everything
        self.radius = 75
        self.scale_factor = 2.0
        self.pixmap = None
        self.target_pos = QPointF(0, 0)
        self.hide()

    def boundingRect(self):
        return QRectF(-self.radius, -self.radius, self.radius*2, self.radius*2)

    def paint(self, painter, option, widget):
        if not self.pixmap:
            return

        # Draw circular clip
        path = QPainterPath()
        path.addEllipse(self.boundingRect())
        painter.setClipPath(path)
        
        # Fill background
        painter.setBrush(QColor("black"))
        painter.drawRect(self.boundingRect())

        # Draw magnified content
        # Calculate source rect centered on target_pos
        src_w = (self.radius * 2) / self.scale_factor
        src_h = (self.radius * 2) / self.scale_factor
        src_rect = QRectF(
            self.target_pos.x() - src_w/2,
            self.target_pos.y() - src_h/2,
            src_w, src_h
        )
        
        painter.drawPixmap(self.boundingRect(), self.pixmap, src_rect)
        
        # Draw crosshair
        painter.setPen(QPen(QColor("white"), 1))
        painter.drawLine(0, -10, 0, 10)
        painter.drawLine(-10, 0, 10, 0)
        
        # Draw border
        painter.setPen(QPen(QColor("white"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(self.boundingRect())

    def update_view(self, pos):
        self.target_pos = pos
        self.setPos(pos.x() + 50, pos.y() - 50)
        
        if self.view.image_item:
            self.pixmap = self.view.image_item.pixmap()
            self.update()
        else:
            self.pixmap = None
            self.update()

class CustomLineItem:
    """Helper class to manage a line with 2 points and a label."""
    def __init__(self, p1, p2, color, name, canvas, is_ruler=False):
        self.canvas = canvas
        self.name = name
        self.is_ruler = is_ruler
        self.color = color
        
        self.point1 = DraggablePoint(p1.x(), p1.y(), 6, color, canvas, self)
        self.point2 = DraggablePoint(p2.x(), p2.y(), 6, color, canvas, self)
        
        self.line = QGraphicsLineItem()
        self.line.setPen(QPen(color, 2))
        self.line.setZValue(5)
        
        self.label = QGraphicsTextItem(name)
        self.label.setDefaultTextColor(color)
        self.label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.label.setZValue(11)
        
        canvas.scene.addItem(self.point1)
        canvas.scene.addItem(self.point2)
        canvas.scene.addItem(self.line)
        canvas.scene.addItem(self.label)
        
        canvas.scene.addItem(self.label)
        
        self.is_selected = False
        self.update_geometry()
        
    def set_selected(self, selected):
        self.is_selected = selected
        if selected:
            self.line.setPen(QPen(QColor("yellow"), 3, Qt.PenStyle.DashLine))
        else:
            self.line.setPen(QPen(self.color, 2))
        
    def update_geometry(self):
        p1 = self.point1.pos()
        p2 = self.point2.pos()
        self.line.setLine(p1.x(), p1.y(), p2.x(), p2.y())
        
        # Update label position (midpoint)
        mid_x = (p1.x() + p2.x()) / 2
        mid_y = (p1.y() + p2.y()) / 2
        self.label.setPos(mid_x, mid_y)
        
        if self.is_ruler:
            # Calculate length
            dist = math.sqrt((p2.x() - p1.x())**2 + (p2.y() - p1.y())**2)
            self.label.setPlainText(f"{dist:.1f} px")
        else:
            self.label.setPlainText(self.name)

    def remove(self):
        self.canvas.scene.removeItem(self.point1)
        self.canvas.scene.removeItem(self.point2)
        self.canvas.scene.removeItem(self.line)
        self.canvas.scene.removeItem(self.label)

class DrawingCanvas(QGraphicsView):
    points_updated = Signal(list) # Emits list of QPointF
    selection_changed = Signal(list) # Emits list of selected CustomLineItems
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # State
        self.image_item = None
        self.current_tool = None # "ground", "calcaneus", "free_line", "ruler", "angle"
        self._zoom = 0
        self._empty = True
        
        # Data - Pes Planus Mode
        self.ground_points = [] 
        self.calc_points = []   
        self.ground_line = None
        self.calc_line = None
        self.angle_arc = None
        
        # Data - Free Drawing Mode
        self.custom_items = [] # List of CustomLineItem
        self.temp_point = None # First point for 2-click creation
        self.current_color = QColor("#55efc4") # Default color
        
        self.magnifier = None
        self.selected_point = None

        # Settings
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        
        # Pan settings
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def set_image(self, q_pixmap):
        self.scene.clear()
        self.ground_points = []
        self.calc_points = []
        self.ground_line = None
        self.calc_line = None
        self.custom_items = []
        self.temp_point = None
        self._zoom = 0
        self._empty = False
        
        self.image_item = QGraphicsPixmapItem(q_pixmap)
        self.image_item.setZValue(0)
        self.scene.addItem(self.image_item)
        self.setSceneRect(self.image_item.boundingRect())
        
        self.magnifier = Magnifier(self)
        self.scene.addItem(self.magnifier)
        
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def create_blank_canvas(self, width=800, height=600):
        self.scene.clear()
        self.image_item = None # Ensure image_item is None
        self.ground_points = []
        self.calc_points = []
        self.ground_line = None
        self.calc_line = None
        self.custom_items = []
        self.temp_point = None
        self._zoom = 0
        self._empty = False
        
        # Create a white background (actually black for dark theme)
        self.scene.setBackgroundBrush(QBrush(QColor("black")))
        self.setSceneRect(0, 0, width, height)
        
        # Add a border rect to define the area
        self.scene.addRect(0, 0, width, height, QPen(QColor("#333"), 1))
        
        self.magnifier = Magnifier(self)
        self.scene.addItem(self.magnifier)
        
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def set_tool(self, tool_name):
        self.current_tool = tool_name
        self.temp_point = None # Reset temp point when switching tools
        if hasattr(self, 'temp_point_item'):
            self.scene.removeItem(self.temp_point_item)
            del self.temp_point_item

    # --- Zoom & Pan Logic ---

    def wheelEvent(self, event: QWheelEvent):
        if self._empty:
            return
            
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        old_pos = self.mapToScene(event.position().toPoint())

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            
        self.scale(zoom_factor, zoom_factor)

        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())

    def mousePressEvent(self, event: QMouseEvent):
        if self._empty:
            return

        # Right click OR Middle click to Pan
        if event.button() == Qt.MouseButton.RightButton or event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._last_pan_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        
        # Left click to Draw
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if we clicked on an existing point (let DraggablePoint handle it)
            item = self.itemAt(event.position().toPoint())
            if isinstance(item, DraggablePoint):
                self.selected_point = item
                self.magnifier.show()
                self.update_magnifier(item.pos())
                super().mousePressEvent(event)
                return
            else:
                self.selected_point = None

            # Add new point
            scene_pos = self.mapToScene(event.position().toPoint())
            
            # Allow drawing if image exists OR if we are in blank canvas mode (scene rect defined)
            if not self._empty and self.scene.sceneRect().contains(scene_pos):
                self.add_point(scene_pos)
        
        # Selection Logic (Left Click without tool or with Select tool if we had one)
        # Actually, let's allow selection if no specific drawing tool is active OR if we are in "select" mode (which we might imply if tool is None)
        # But wait, we have tools "free_line", "ruler", "angle".
        # If tool is None, we can select.
        if event.button() == Qt.MouseButton.LeftButton and self.current_tool is None:
             self.handle_selection(event)

        super().mousePressEvent(event)

    def handle_selection(self, event):
        item = self.itemAt(event.position().toPoint())
        clicked_line = None
        
        # Find if we clicked a CustomLineItem part
        if isinstance(item, (QGraphicsLineItem, QGraphicsTextItem)):
            for custom_item in self.custom_items:
                if custom_item.line == item or custom_item.label == item:
                    clicked_line = custom_item
                    break
        elif isinstance(item, DraggablePoint):
             if hasattr(item, 'parent_item') and isinstance(item.parent_item, CustomLineItem):
                clicked_line = item.parent_item

        # Handle Selection modifiers
        modifiers = event.modifiers()
        is_multi = (modifiers & Qt.KeyboardModifier.ControlModifier)
        
        if clicked_line:
            if is_multi:
                # Toggle
                clicked_line.set_selected(not clicked_line.is_selected)
            else:
                # Select only this one (unless already selected, then maybe don't deselect others? standard behavior is deselect others)
                # Simple behavior: Clear others, select this one
                self.deselect_all()
                clicked_line.set_selected(True)
        else:
            # Clicked empty space
            if not is_multi:
                self.deselect_all()
                
        self.emit_selection()

    def deselect_all(self):
        for item in self.custom_items:
            item.set_selected(False)

    def emit_selection(self):
        selected = [item for item in self.custom_items if item.is_selected]
        self.selection_changed.emit(selected)

    def delete_selected_items(self):
        to_remove = [item for item in self.custom_items if item.is_selected]
        for item in to_remove:
            item.remove()
            self.custom_items.remove(item)
        
        if to_remove:
            self.emit_selection()
            self.scene.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton or event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        
        if event.button() == Qt.MouseButton.LeftButton:
            if self.magnifier:
                self.magnifier.hide()
            
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if self.selected_point:
            step = 0.5
            pos = self.selected_point.pos()
            if event.key() == Qt.Key.Key_Left:
                self.selected_point.setPos(pos.x() - step, pos.y())
            elif event.key() == Qt.Key.Key_Right:
                self.selected_point.setPos(pos.x() + step, pos.y())
            elif event.key() == Qt.Key.Key_Up:
                self.selected_point.setPos(pos.x(), pos.y() - step)
            elif event.key() == Qt.Key.Key_Down:
                self.selected_point.setPos(pos.x(), pos.y() + step)
            else:
                super().keyPressEvent(event)
        else:
            if event.key() == Qt.Key.Key_Delete:
                self.delete_selected_items()
            else:
                super().keyPressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if hasattr(self, '_panning') and self._panning:
            delta = event.position() - self._last_pan_pos
            self._last_pan_pos = event.position()
            
            hs = self.horizontalScrollBar()
            vs = self.verticalScrollBar()
            hs.setValue(int(hs.value() - delta.x()))
            vs.setValue(int(vs.value() - delta.y()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def zoom_in(self):
        self.scale(1.2, 1.2)
        
    def zoom_out(self):
        self.scale(0.8, 0.8)
        
    def fit_view(self):
        if self.image_item or not self._empty:
            self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    # --- Drawing Logic ---

    def add_point(self, pos):
        # 1. Pes Planus Mode Logic
        if self.current_tool in ["ground", "calcaneus"]:
            target_list = None
            color = None
            
            if self.current_tool == "ground":
                if len(self.ground_points) >= 2: return # Max 2 points
                target_list = self.ground_points
                color = QColor("#00FFFF") # Cyan
            elif self.current_tool == "calcaneus":
                if len(self.calc_points) >= 2: return # Max 2 points
                target_list = self.calc_points
                color = QColor("#FF00FF") # Magenta
                
            if target_list is not None:
                point_item = DraggablePoint(pos.x(), pos.y(), 6, color, self)
                self.scene.addItem(point_item)
                target_list.append(point_item)
                self.selected_point = point_item # Auto-select new point
                self.update_lines()
                
        # 2. Free Drawing Mode Logic
        elif self.current_tool in ["free_line", "ruler"]:
            if self.temp_point is None:
                # First click
                self.temp_point = pos
                # Visual feedback
                self.temp_point_item = QGraphicsEllipseItem(pos.x()-3, pos.y()-3, 6, 6)
                self.temp_point_item.setBrush(QBrush(self.current_color))
                self.temp_point_item.setPen(Qt.PenStyle.NoPen)
                self.scene.addItem(self.temp_point_item)
            else:
                # Second click - Create Line
                p1 = self.temp_point
                p2 = pos
                
                # Remove temp visual
                if hasattr(self, 'temp_point_item'):
                    self.scene.removeItem(self.temp_point_item)
                    del self.temp_point_item
                
                self.temp_point = None
                
                is_ruler = (self.current_tool == "ruler")
                name = "Cetvel" if is_ruler else f"Çizgi {len(self.custom_items) + 1}"
                color = self.current_color if not is_ruler else QColor("#fab1a0")
                
                item = CustomLineItem(p1, p2, color, name, self, is_ruler)
                self.custom_items.append(item)
        
        # 3. Angle Tool Logic
        elif self.current_tool == "angle":
            # Find which line was clicked
            clicked_item = self.scene.itemAt(pos, self.transform())
            
            # We need to find the CustomLineItem parent of the clicked graphics item
            target_line = None
            
            # Check if we clicked a part of a CustomLineItem
            if isinstance(clicked_item, (QGraphicsLineItem, QGraphicsTextItem)):
                # Find which CustomLineItem owns this
                for item in self.custom_items:
                    if item.line == clicked_item or item.label == clicked_item:
                        target_line = item
                        break
            elif isinstance(clicked_item, DraggablePoint):
                if hasattr(clicked_item, 'parent_item') and isinstance(clicked_item.parent_item, CustomLineItem):
                    target_line = clicked_item.parent_item

            if target_line:
                if self.temp_point is None:
                    # First line selected
                    self.temp_point = target_line # Store the object, not pos
                    # Highlight feedback could be added here
                else:
                    # Second line selected
                    line1 = self.temp_point
                    line2 = target_line
                    self.temp_point = None
                    
                    if line1 != line2:
                        self.create_angle_measurement(line1, line2)

    def create_angle_measurement(self, line1, line2):
        # Calculate angle between two lines
        l1_p1 = line1.point1.pos()
        l1_p2 = line1.point2.pos()
        l2_p1 = line2.point1.pos()
        l2_p2 = line2.point2.pos()
        
        # Vectors
        v1 = l1_p2 - l1_p1
        v2 = l2_p2 - l2_p1
        
        angle1 = math.atan2(v1.y(), v1.x())
        angle2 = math.atan2(v2.y(), v2.x())
        
        angle_deg = math.degrees(abs(angle1 - angle2))
        if angle_deg > 180: angle_deg = 360 - angle_deg
        
        # Visuals
        # Find intersection for arc placement
        def cross(v, w): return v.x()*w.y() - v.y()*w.x()
        r = v1
        s = v2
        r_cross_s = cross(r, s)
        
        intersection = QPointF(0,0)
        if abs(r_cross_s) > 1e-10:
            q_minus_p = l2_p1 - l1_p1
            t = cross(q_minus_p, s) / r_cross_s
            intersection = l1_p1 + r * t
            
            # Draw Arc
            arc = QGraphicsEllipseItem(intersection.x()-30, intersection.y()-30, 60, 60)
            arc.setPen(QPen(QColor("yellow"), 2, Qt.PenStyle.DashLine))
            arc.setStartAngle(int(min(math.degrees(-angle1), math.degrees(-angle2)) * 16))
            arc.setSpanAngle(int(angle_deg * 16))
            self.scene.addItem(arc)
            
            # Label
            label = QGraphicsTextItem(f"{angle_deg:.1f}°")
            label.setDefaultTextColor(QColor("yellow"))
            label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            label.setPos(intersection.x() + 10, intersection.y() - 40)
            self.scene.addItem(label)

    def update_magnifier(self, pos):
        if self.magnifier and self.magnifier.isVisible():
            self.magnifier.update_view(pos)

    def update_lines(self):
        # Update Ground Line
        if len(self.ground_points) == 2:
            p1 = self.ground_points[0].pos()
            p2 = self.ground_points[1].pos()
            if not self.ground_line:
                self.ground_line = QGraphicsLineItem()
                self.ground_line.setPen(QPen(QColor("#00FFFF"), 2))
                self.ground_line.setZValue(5)
                self.scene.addItem(self.ground_line)
            self.ground_line.setLine(p1.x(), p1.y(), p2.x(), p2.y())
        
        # Update Calcaneus Line
        if len(self.calc_points) == 2:
            p1 = self.calc_points[0].pos()
            p2 = self.calc_points[1].pos()
            if not self.calc_line:
                self.calc_line = QGraphicsLineItem()
                self.calc_line.setPen(QPen(QColor("#FF00FF"), 2))
                self.calc_line.setZValue(5)
                self.scene.addItem(self.calc_line)
            self.calc_line.setLine(p1.x(), p1.y(), p2.x(), p2.y())
            
        # Update Angle Arc
        if len(self.ground_points) == 2 and len(self.calc_points) == 2:
            l1_p1 = self.ground_points[0].pos()
            l1_p2 = self.ground_points[1].pos()
            l2_p1 = self.calc_points[0].pos()
            l2_p2 = self.calc_points[1].pos()
            
            def cross(v, w): return v.x()*w.y() - v.y()*w.x()
            
            r = l1_p2 - l1_p1
            s = l2_p2 - l2_p1
            r_cross_s = cross(r, s)
            
            if abs(r_cross_s) > 1e-10: # Not parallel
                q_minus_p = l2_p1 - l1_p1
                t = cross(q_minus_p, s) / r_cross_s
                intersection = l1_p1 + r * t
                
                if not self.angle_arc:
                    self.angle_arc = QGraphicsEllipseItem()
                    self.angle_arc.setPen(QPen(QColor("yellow"), 2, Qt.PenStyle.DashLine))
                    self.angle_arc.setZValue(4)
                    self.scene.addItem(self.angle_arc)
                
                radius = 40
                self.angle_arc.setRect(intersection.x() - radius, intersection.y() - radius, radius*2, radius*2)
                self.angle_arc.show()
            else:
                if self.angle_arc: self.angle_arc.hide()
        else:
            if self.angle_arc: self.angle_arc.hide()
            
        # Emit all points for calculation
        all_points = []
        if len(self.ground_points) == 2 and len(self.calc_points) == 2:
            all_points.append(self.ground_points[0].pos())
            all_points.append(self.ground_points[1].pos())
            all_points.append(self.calc_points[0].pos())
            all_points.append(self.calc_points[1].pos())
            
        self.points_updated.emit(all_points)

    def reset_drawing(self):
        # Reset Pes Planus
        items_to_remove = []
        
        # Collect items safely
        for p in self.ground_points + self.calc_points:
             items_to_remove.append(p)
             
        if self.ground_line: items_to_remove.append(self.ground_line)
        if self.calc_line: items_to_remove.append(self.calc_line)
        if self.angle_arc: items_to_remove.append(self.angle_arc)
        
        # Remove safely
        for item in items_to_remove:
            try:
                if item and item.scene() == self.scene:
                    self.scene.removeItem(item)
            except RuntimeError:
                pass # Already deleted
        
        self.ground_points = []
        self.calc_points = []
        self.ground_line = None
        self.calc_line = None
        self.angle_arc = None
        
        # Reset Free Drawing
        for item in self.custom_items:
            item.remove()
        self.custom_items = []
        if hasattr(self, 'temp_point_item'):
            self.scene.removeItem(self.temp_point_item)
            del self.temp_point_item
        self.temp_point = None
        
        self.points_updated.emit([])
