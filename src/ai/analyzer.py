import os
from src.core.dicom_loader import load_image_array, load_dicom_array
import cv2
import numpy as np
import torch
import math
import segmentation_models_pytorch as smp
from typing import Tuple, Dict, Any, List, Optional
from PIL import Image

def analyze_calcaneal_pitch(
    original_img: np.ndarray, 
    prediction_mask: np.ndarray
) -> Tuple[np.ndarray, float, Tuple[Tuple[int, int], Tuple[int, int]], Tuple[Tuple[int, int], Tuple[int, int]]]:
    """
    Analyzes the Calcaneal Pitch Angle with robust Convex Hull logic, strict tie-breaking, and virtual Ground Line.
    """
    
    # Ensure formats
    if len(original_img.shape) == 2:
        vis_img = cv2.cvtColor(original_img, cv2.COLOR_GRAY2BGR)
    else:
        vis_img = original_img.copy()

    h_img, w_img = prediction_mask.shape[:2]

    # --- 1. Morphological Cleaning ---
    kernel = np.ones((5, 5), np.uint8)
    cleaned_mask = cv2.morphologyEx(prediction_mask, cv2.MORPH_OPEN, kernel)
    
    # Keep only the largest contour
    contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return vis_img, 0.0, ((0, 0), (0, 0)), ((0, 0), (0, 0))
    
    largest_contour = max(contours, key=cv2.contourArea)
    
    # --- 2. Keypoint Detection (Vertical Split + Strict Tie-Breaking) ---
    # Find bounding box
    x, y, w, h = cv2.boundingRect(largest_contour)
    mid_x = x + w // 2
    
    # Get all points in the contour (or hull for robustness)
    hull = cv2.convexHull(largest_contour)
    hull_points = hull[:, 0, :]
    
    # Split into Posterior (Left) and Anterior (Right) halves based on Geometric Vertical Center
    left_half = [pt for pt in hull_points if pt[0] < mid_x]
    right_half = [pt for pt in hull_points if pt[0] >= mid_x]
    
    # Find Points with "Lowest 5% Slice" Logic
    # Goal: Target the corners (tubercle) rather than just the lowest pixel.
    
    # helper for finding corner in bottom slice
    def get_corner_point(points, is_left_half):
        if not points: return None
        
        # 1. Find Deepest Level
        y_values = [p[1] for p in points]
        y_max = max(y_values) # Deepest point
        
        # 2. Strict Filter: Get ALL pixels at this deepest level
        # User Request: "bu bölgedeki en alt seviyedeki tüm pikselleri (maksimum Y) belirle"
        candidates = [p for p in points if p[1] == y_max]
        
        if not candidates: 
            return points[0] # Should not happen
            
        # 3. Center of Mass: Calculate Mean X
        # User Request: "X koordinatlarının ortalamasını (mean) alarak... tam kavisin merkezine sabitle"
        avg_x = sum(p[0] for p in candidates) / len(candidates)
        
        return [int(avg_x), y_max]

    # Point A (Posterior/Heel) & Point B (Anterior/Joint) Logic
    # We identify the Heel (Point A) as the point closest to the bottom (Max Y).
    
    p1_deepest = get_corner_point(left_half, is_left_half=True)
    p2_deepest = get_corner_point(right_half, is_left_half=False)
    
    # Fallbacks
    if p1_deepest is None: p1_deepest = min(hull_points, key=lambda p: p[0])
    if p2_deepest is None: p2_deepest = max(hull_points, key=lambda p: p[0])

    p1_deepest = tuple(p1_deepest)
    p2_deepest = tuple(p2_deepest)

    # 1. Determine Orientation (Left vs Right)
    # The side with the DEEPER point is the Heel side.
    if p1_deepest[1] >= p2_deepest[1]:
        # Left is Deeper -> Heel is Left, Toes are Right
        heel_is_left = True
        pa = p1_deepest # Point A is Heel (Deepest)
        
        # Point B: Anterior-Inferior Corner (Right Half)
        # Target: Bottom-Right most point in the Right Half.
        # Score: Maximize (X + Y). (Forward + Down)
        # Large X (Right), Large Y (Down).
        if right_half:
            pb = max(right_half, key=lambda p: int(p[0]) + int(p[1]))
            pb = tuple(pb)
        else:
            pb = p2_deepest
            
    else:
        # Right is Deeper -> Heel is Right, Toes are Left
        heel_is_left = False
        pa = p2_deepest # Point A is Heel (Deepest)
        
        # Point B: Anterior-Inferior Corner (Left Half)
        # Target: Bottom-Left most point in the Left Half.
        # Score: Maximize (-X + Y) -> Minimize (X - Y).
        # Small X (Left), Large Y (Down).
        if left_half:
            pb = min(left_half, key=lambda p: int(p[0]) - int(p[1]))
            pb = tuple(pb)
        else:
            pb = p1_deepest

    # --- 3. Ground Line Detection (Fixed to Point A) ---
    # User Request: "Mavi çizgi her zaman topuğun (pa) arkasına doğru uzanmalı."
    # Ground Line must be perfectly horizontal (0 degree) at Point A's Y level.
    
    ground_y = pa[1]
    
    # Dynamic Visualization based on Heel Direction
    # Goal: Draw line from Heel (pa) extending TOWARDS the Toes (pb) for 250px.
    
    if heel_is_left:
        # Heel Left, Toes Right -> Extend Right
        vis_gx1 = pa[0]
        vis_gx2 = min(w_img, pa[0] + 250)
    else:
        # Heel Right, Toes Left -> Extend Left
        vis_gx1 = max(0, pa[0] - 250)
        vis_gx2 = pa[0]
        
    vis_gy1 = ground_y
    vis_gy2 = ground_y
    
    ground_angle = 0.0
    ground_points = ((vis_gx1, vis_gy1), (vis_gx2, vis_gy2))
    
    # Draw Ground Line (Cyan) - Short reference line
    cv2.line(vis_img, ground_points[0], ground_points[1], (255, 255, 0), 2)
    
    # --- 4. Calculation ---
    # User Request: "0 derecelik yatay hat ile pa-pb ... arasında hesapla"
    
    # Calculate vector angle for calcaneus line (pa -> pb)
    dx = pb[0] - pa[0]
    dy = pb[1] - pa[1]
    
    if dx == 0:
        pitch_angle = 90.0
    else:
        # Absolute Slope Logic (Request: "Mutlak Eğim Mantığı")
        # Use atan(abs(dy)/abs(dx)) to ensure strict 0-90 degree acute angle regardless of direction.
        pitch_angle = math.degrees(math.atan(abs(dy) / abs(dx)))
    pitch_angle = round(pitch_angle, 1)

    # --- 5. Visualization ---
    
    # Draw Calcaneus Line (Magenta)
    cv2.line(vis_img, pa, pb, (255, 0, 255), 3) 
    
    # Draw Keypoints
    # Point A - Posterior (Heel) - Red
    cv2.circle(vis_img, pa, 8, (0, 0, 255), -1) 
    cv2.circle(vis_img, pa, 10, (255, 255, 255), 2) 
    
    # Point B - Anterior (Joint) - Green
    cv2.circle(vis_img, pb, 8, (0, 255, 0), -1) 
    cv2.circle(vis_img, pb, 10, (255, 255, 255), 2) 
    
    # Text Label
    label_text = f"{pitch_angle} deg"
    mid_x = (pa[0] + pb[0]) // 2
    mid_y = (pa[1] + pb[1]) // 2 - 20
    
    # Add background box for text readability
    (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    cv2.rectangle(vis_img, (mid_x - 5, mid_y - th - 5), (mid_x + tw + 5, mid_y + 5), (0,0,0), -1)
    cv2.putText(vis_img, label_text, (mid_x, mid_y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    return vis_img, pitch_angle, (pa, pb), ground_points

class PesPlanusAnalyzer:
    def __init__(self, model_path: str = "calcaneus_unet_resnet34_best.pth"):
        self.model_path = model_path
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.model_input_size = (512, 512)
        
        try:
            self._load_model()
        except Exception as e:
            print(f"Model başlatma hatası: {e}")

    def _load_model(self):
        if not os.path.exists(self.model_path):
            print(f"Model dosyası bulunamadı: {self.model_path}")
            return

        print(f"Model yükleniyor: {self.model_path} ({self.device})...")
        
        self.model = smp.Unet(
            encoder_name="resnet34",
            encoder_weights=None, 
            in_channels=1,        
            classes=1,            
        )

        try:
            state_dict = torch.load(self.model_path, map_location=self.device)
            if 'state_dict' in state_dict:
                state_dict = state_dict['state_dict']
            
            self.model.load_state_dict(state_dict)
            self.model.to(self.device)
            self.model.eval()
            print("Model başarıyla yüklendi.")
        except Exception as e:
            print(f"Ağırlıklar yüklenemedi: {e}")
            self.model = None

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        resized = cv2.resize(image, self.model_input_size)
        
        # Check if normalization needed (0-255 -> 0-1)
        if resized.max() > 1.0:
            resized = resized / 255.0
            
        tensor = torch.from_numpy(resized).float().unsqueeze(0).unsqueeze(0)
        return tensor

    def analyze(self, image_data: Any) -> Dict[str, Any]:
        """
        Main pipeline that calls the new robust algorithm.
        """
        # 0. Load Image
        image = None
        if isinstance(image_data, str):
            # Check extension or try divers
            ext = os.path.splitext(image_data)[1].lower()
            if ext in ['.dcm', '.dicom']:
                image, _ = load_dicom_array(image_data)
            else:
                image, _ = load_image_array(image_data)
                
            if image is None:
                 return {"error": f"Görüntü okunamadı: {image_data}"}
                 
        elif isinstance(image_data, np.ndarray):
            if len(image_data.shape) == 3:
                image = cv2.cvtColor(image_data, cv2.COLOR_BGR2GRAY)
            else:
                image = image_data
        else:
             return {"error": "Geçersiz giriş formatı"}
             
        if image is None:
            return {"error": "Görüntü okunamadı"}

        original_h, original_w = image.shape[:2]

        if self.model is None:
             return {"error": "Model yüklü değil"}

        # 1. Prediction
        input_tensor = self.preprocess(image).to(self.device)
        
        with torch.no_grad():
            output = self.model(input_tensor)
            
        mask_tensor = torch.sigmoid(output) > 0.5
        mask_resized = mask_tensor.squeeze().cpu().numpy().astype(np.uint8) * 255
            
        # Resize mask back to original size for analysis
        mask_original = cv2.resize(mask_resized, (original_w, original_h), interpolation=cv2.INTER_NEAREST)
        
        # 2. Call the Algorithm
        vis_image, angle, calc_pts, ground_pts = analyze_calcaneal_pitch(image, mask_original)
        
        # 3. Classify
        # <15: Pes Planus, 15-20: Borderline, 20-30: Normal, >30: Pes Cavus (Approx)
        if angle < 15:
            cat = "Pes Planus"
            color = "#ff0000" # Red
        elif angle < 20:
             cat = "Sınırda (Borderline)"
             color = "#ffae00" # Orange
        elif angle <= 30:
             cat = "Normal"
             color = "#00ff00" # Green
        else:
             cat = "Pes Cavus"
             color = "#ff0000"

        # 4. Prepare Result
        return {
            "angle": angle,
            "diagnosis": cat,
            "raw_color": color, 
            "lines": [calc_pts, ground_pts], # For Canvas UI
            "visualized_image": vis_image    # For debugging or display if needed
        }