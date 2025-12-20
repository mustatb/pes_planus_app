import cv2
import numpy as np
import easyocr
import torch

class MarkerDetector:
    _reader = None

    @classmethod
    def get_reader(cls):
        """Lazy load EasyOCR reader to save resources if not used."""
        if cls._reader is None:
            # Check for CUDA
            use_gpu = torch.cuda.is_available()
            print(f"Initializing EasyOCR (GPU={use_gpu})...")
            # Only English is usually enough for L/R, but maybe Turkish for "SOL/SAG"
            cls._reader = easyocr.Reader(['en'], gpu=use_gpu, verbose=False) 
        return cls._reader

    @staticmethod
    def detect_side(image_array: np.ndarray) -> str:
        """
        Detects 'L' or 'R' markers in the top corners of the image.
        Returns 'L', 'R', or None.
        Attempts multiple preprocessing techniques for robustness.
        """
        try:
            reader = MarkerDetector.get_reader()
            
            # Ensure Grayscale
            if len(image_array.shape) == 3:
                gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
            else:
                gray = image_array
            
            h, w = gray.shape

            # Resize for speed if too large (Safe limit)
            if w > 1200:
                scale = 1200 / w
                new_w, new_h = 1200, int(h * scale)
                gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
                h, w = new_h, new_w
            
            # Define ROI: Top 40% height
            roi_h = int(h * 0.40)
            
            # Split into two overlapping halves to cover center
            # Left: 0% to 60% width
            w_60 = int(w * 0.60)
            roi_tl = gray[0:roi_h, 0:w_60] 
            
            # Right: 40% to 100% width
            w_40 = int(w * 0.40)
            roi_tr = gray[0:roi_h, w_40:w]
            
            # Helper: Add padding
            def pad_roi(roi):
                # Add 20px border to help OCR with edge characters
                return cv2.copyMakeBorder(roi, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=[0])

            roi_tl = pad_roi(roi_tl)
            roi_tr = pad_roi(roi_tr)
            
            # Helper to check text with multiple preprocessings
            def check_roi_robust(roi):
                # Preprocessing variants to try
                variants = []
                
                # 1. Original (Gray)
                variants.append(("Original", roi))
                
                # 2. Inverted (White text on Black background becomes Black on White)
                # This is CRITICAL for X-rays where markers are often white.
                roi_inv = cv2.bitwise_not(roi)
                variants.append(("Inverted", roi_inv))
                
                # 3. Thresholded (Otsu)
                try:
                    roi_blur = cv2.GaussianBlur(roi, (3,3), 0)
                    _, roi_thresh = cv2.threshold(roi_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    variants.append(("ThreshOtsu", roi_thresh))
                    variants.append(("ThreshOtsuInv", cv2.bitwise_not(roi_thresh)))
                except: pass

                # 4. Fixed Threshold (Good for high contrast markers)
                try:
                    _, roi_fixed = cv2.threshold(roi, 180, 255, cv2.THRESH_BINARY)
                    variants.append(("Fixed180", roi_fixed))
                    variants.append(("Fixed180Inv", cv2.bitwise_not(roi_fixed)))
                except: pass
                
                # 5. Adaptive Threshold (Good for varying lighting)
                try:
                    roi_adapt = cv2.adaptiveThreshold(roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                    variants.append(("Adaptive", roi_adapt))
                except: pass

                # 6. Upscaled (For small markers)
                try:
                    h_r, w_r = roi.shape
                    roi_up = cv2.resize(roi, (w_r*2, h_r*2), interpolation=cv2.INTER_LINEAR)
                    variants.append(("Upscaled", roi_up))
                    variants.append(("UpscaledInv", cv2.bitwise_not(roi_up)))
                except: pass

                # Run OCR on each variant
                for name, img_variant in variants:
                    # Allow slightly lower confidence
                    results = reader.readtext(img_variant)
                    for (bbox, text, prob) in results:
                        if prob < 0.3: continue # Lowered from 0.4
                        
                        text_upper = text.upper().strip()
                        
                        # Direct Matches
                        if text_upper in ["L", "LT", "LEFT", "SOL", "L."]:
                            # print(f"Detected 'L' in {name} with prob {prob}")
                            return "L"
                        if text_upper in ["R", "RT", "RIGHT", "SAG", "SAĞ", "R."]:
                            # print(f"Detected 'R' in {name} with prob {prob}")
                            return "R"
                
                return None
            
            # Check Left Overlap Region
            side = check_roi_robust(roi_tl)
            if side: return side
            
            # Check Right Overlap Region
            side = check_roi_robust(roi_tr)
            if side: return side
            
            return None
            
        except Exception as e:
            print(f"OCR Error: {e}")
            return None
