import os
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
    
    # Find Points with Strict Rules
    
    # Point A (Posterior/Left): Deepest (Max Y). Tie-break: Leftmost (Min X)
    if not left_half: 
         # Fallback: Just take closest to left edge
         pa = min(hull_points, key=lambda p: p[0])
    else:
         # Sort: Primary Key = Y (descending), Secondary Key = X (ascending)
         # We want max Y, then min X.
         # Python sort is stable.
         sorted_left = sorted(left_half, key=lambda p: (-p[1], p[0]))
         pa = sorted_left[0]
         
    # Point B (Anterior/Right): Deepest (Max Y). Tie-break: Rightmost (Max X)
    if not right_half:
         # Fallback: Just take closest to right edge
         pb = max(hull_points, key=lambda p: p[0])
    else:
         # Sort: Primary Key = Y (descending), Secondary Key = X (descending)
         # We want max Y, then max X.
         sorted_right = sorted(right_half, key=lambda p: (-p[1], -p[0]))
         pb = sorted_right[0]
    
    pa = tuple(pa)
    pb = tuple(pb)
    
    # Ensure Left-to-Right order (just in case fallback failed)
    if pa[0] > pb[0]:
        pa, pb = pb, pa
        
    # --- 3. Ground Line Detection (Virtual Horizontal) ---
    # Ground Line: Virtual horizontal line passing through the LOWEST point (Max Y).
    # This ensures the floor is at the bottom of the bone structure.
    
    ground_y = max(pa[1], pb[1])
    
    vis_gx1 = 0
    vis_gy1 = ground_y
    
    vis_gx2 = w_img
    vis_gy2 = ground_y
    
    ground_angle = 0.0
    ground_points = ((vis_gx1, vis_gy1), (vis_gx2, vis_gy2))
    
    # Draw Ground Line (Cyan)
    cv2.line(vis_img, ground_points[0], ground_points[1], (255, 255, 0), 2)
    
    # --- 4. Calculation ---
    
    # Calculate vector angle for calcaneus line (pa -> pb)
    dx = pb[0] - pa[0]
    dy = pb[1] - pa[1]
    
    if dx == 0:
        calc_angle = 90.0
    else:
        # atan2 returns -180 to 180.
        # Since Y increases downwards, positive dy means downwards.
        # But we only care about the absolute angle against the horizontal.
        calc_angle = math.degrees(math.atan2(dy, dx))
        
    # Pitch Angle = Absolute angle of calcaneus vs horizontal (0)
    pitch_angle = abs(calc_angle)
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
        if isinstance(image_data, str):
            image = cv2.imread(image_data, cv2.IMREAD_GRAYSCALE)
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