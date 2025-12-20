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
            
            # Define ROI: Top 25% height, 25% width
            roi_h = int(h * 0.25)
            roi_w = int(w * 0.25)
            
            # Extract ROIs
            roi_tl = gray[0:roi_h, 0:roi_w]          # Top-Left
            roi_tr = gray[0:roi_h, w-roi_w:w]        # Top-Right
            
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
                
                # 3. Thresholded (Otsu) - Removes noise
                # Apply to both original and inverted
                try:
                    _, roi_thresh = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    variants.append(("Thresh", roi_thresh))
                    
                    roi_thresh_inv = cv2.bitwise_not(roi_thresh)
                    variants.append(("ThreshInv", roi_thresh_inv))
                except:
                    pass

                # Run OCR on each variant
                for name, img_variant in variants:
                    results = reader.readtext(img_variant)
                    for (bbox, text, prob) in results:
                        if prob < 0.4: continue
                        
                        text_upper = text.upper().strip()
                        
                        # Direct Matches
                        if text_upper in ["L", "LT", "LEFT", "SOL"]:
                            # print(f"Detected 'L' in {name} with prob {prob}")
                            return "L"
                        if text_upper in ["R", "RT", "RIGHT", "SAG", "SAĞ"]:
                            # print(f"Detected 'R' in {name} with prob {prob}")
                            return "R"
                
                return None

            # Check Left Corner
            side = check_roi_robust(roi_tl)
            if side: return side
            
            # Check Right Corner
            side = check_roi_robust(roi_tr)
            if side: return side
            
            return None
            
        except Exception as e:
            print(f"OCR Error: {e}")
            return None
