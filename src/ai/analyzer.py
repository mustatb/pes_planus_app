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
    Analyzes the Calcaneal Pitch Angle with robust Convex Hull logic and correct Ground Line visualization.
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
    
    # --- 2. Keypoint Detection (Convex Hull Bridge Method) ---
    # use convex hull to bridge concave regions of the bone
    hull = cv2.convexHull(largest_contour)
    
    # Calculate Centroid of the MASK for splitting logic
    M = cv2.moments(largest_contour)
    if M["m00"] == 0:
         return vis_img, 0.0, ((0, 0), (0, 0)), ((0, 0), (0, 0))
         
    cx = int(M["m10"] / M["m00"])

    # Extract hull vertices
    # hull shape is (N, 1, 2)
    hull_points = hull[:, 0, :]
    
    # Split into Posterior (Left of centroid) and Anterior (Right of centroid)
    # assuming standard lateral view where heel is posterior.
    left_points = [pt for pt in hull_points if pt[0] < cx] 
    right_points = [pt for pt in hull_points if pt[0] >= cx]
    
    if not left_points or not right_points:
         # Fallback if split fails -> minimal logic
         return vis_img, 0.0, ((0, 0), (0, 0)), ((0, 0), (0, 0))

    # Point A: Deepest point (Max Y) in Posterior/Left
    pa = max(left_points, key=lambda p: p[1])
    pa = tuple(pa)

    # Point B: Deepest point (Max Y) in Anterior/Right
    pb = max(right_points, key=lambda p: p[1])
    pb = tuple(pb)
    
    # Ensure Left-to-Right order
    if pa[0] > pb[0]:
        pa, pb = pb, pa
        
    # --- 3. Ground Line Detection & Visualization ---
    roi_start_y = int(h_img * 0.70) # Scan bottom 30%
    roi_img = original_img[roi_start_y:, :]
    if len(roi_img.shape) == 3:
        roi_gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
    else:
        roi_gray = roi_img
        
    edges = cv2.Canny(roi_gray, 30, 100)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=40, minLineLength=w_img*0.15, maxLineGap=20)
    
    ground_angle = 0.0
    ground_points = ((0, h_img-1), (w_img, h_img-1)) 
    
    best_line = None
    if lines is not None:
        valid_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1: continue
            slope = (y2 - y1) / (x2 - x1)
            # strictly horizontal check
            if abs(slope) < 0.15:
                # Store linear length and average Y
                length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
                avg_y = (y1 + y2) / 2
                valid_lines.append((line[0], length, avg_y))
        
        if valid_lines:
            # Heuristic: Prefer lower lines (higher Y) that have decent length.
            # Sort by Y descending.
            valid_lines.sort(key=lambda x: x[2], reverse=True)
            # Pick the lowest one (highest Y)
            best_line_coords = valid_lines[0][0]
            bx1, by1, bx2, by2 = best_line_coords
            best_line = (bx1, by1, bx2, by2)

    # --- 4. Calculation ---
    # Ground Angle
    if best_line:
         bx1, by1, bx2, by2 = best_line
         gdx = bx2 - bx1
         gdy = (by2 + roi_start_y) - (by1 + roi_start_y) # relative dy same as global
         ground_angle = math.degrees(math.atan2(gdy, gdx))
         
         # --- FIX 1: Visualization using Extended Line Equation ---
         # Convert to global
         gx1_g = bx1
         gy1_g = by1 + roi_start_y
         gx2_g = bx2
         gy2_g = by2 + roi_start_y
         
         # y = mx + c
         if gdx == 0:
             # Vertical shouldn't happen due to slope filter, but good practice
             vis_gx1, vis_gy1 = gx1_g, 0
             vis_gx2, vis_gy2 = gx1_g, h_img
         else:
             m = gdy / gdx
             c = gy1_g - m * gx1_g
             
             vis_gx1 = 0
             vis_gy1 = int(c)
             vis_gx2 = w_img
             vis_gy2 = int(m * w_img + c)
             
         ground_points = ((vis_gx1, vis_gy1), (vis_gx2, vis_gy2))
         
         # Draw the line passing through detected object
         cv2.line(vis_img, ground_points[0], ground_points[1], (255, 255, 0), 2)
    else:
         # Fallback
         cv2.line(vis_img, ground_points[0], ground_points[1], (255, 255, 0), 2)

    # Calcaneus Angle
    dx = pb[0] - pa[0]
    dy = pb[1] - pa[1]
    
    if dx == 0:
        calc_angle = 90.0
    else:
        calc_angle = math.degrees(math.atan2(dy, dx))
        
    pitch_angle = abs(calc_angle - ground_angle)
    pitch_angle = round(pitch_angle, 1)

    # --- 5. Visualization (Calcaneus) ---
    # Draw logic for Calcaneus Line
    cv2.line(vis_img, pa, pb, (255, 0, 255), 3) # Magenta Bridge

    # Draw Keypoints (from Hull)
    cv2.circle(vis_img, pa, 6, (0, 0, 255), -1) 
    cv2.circle(vis_img, pb, 6, (0, 255, 0), -1)
    
    # Text Label
    label_text = f"{pitch_angle} deg"
    mid_x = (pa[0] + pb[0]) // 2
    mid_y = (pa[1] + pb[1]) // 2 - 15
    cv2.putText(vis_img, label_text, (mid_x, mid_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
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
