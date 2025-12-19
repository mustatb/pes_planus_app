import os
import pydicom
import numpy as np
from PIL import Image

def load_dicom_array(dicom_path):
    """
    Reads a DICOM file and returns (pixel_array, metadata).
    metadata is a dict containing PatientName, PatientID, etc.
    """
    try:
        dcm = pydicom.dcmread(dicom_path)
        pixel_array = dcm.pixel_array.astype(float)
        
        # Extract Metadata
        metadata = {
            "Patient Name": str(dcm.get("PatientName", "N/A")),
            "Patient ID": str(dcm.get("PatientID", "N/A")),
            "Study Date": str(dcm.get("StudyDate", "N/A")),
            "Modality": str(dcm.get("Modality", "N/A")),
            "Body Part": str(dcm.get("BodyPartExamined", "N/A"))
        }

        # Apply Rescale Slope/Intercept
        slope = getattr(dcm, 'RescaleSlope', 1)
        intercept = getattr(dcm, 'RescaleIntercept', 0)
        pixel_array = pixel_array * slope + intercept

        # Apply Windowing
        # Apply Windowing
        if 'WindowCenter' in dcm and 'WindowWidth' in dcm:
            wc = dcm.WindowCenter
            ww = dcm.WindowWidth
            # Handle MultiValue (list-like)
            if hasattr(wc, '__iter__') and not isinstance(wc, (str, float, int)): wc = wc[0]
            if hasattr(ww, '__iter__') and not isinstance(ww, (str, float, int)): ww = ww[0]
            
            min_val = float(wc) - (float(ww) / 2)
            max_val = float(wc) + (float(ww) / 2)
            pixel_array = np.clip(pixel_array, min_val, max_val)
        else:
            min_val = np.min(pixel_array)
            max_val = np.max(pixel_array)
        
        # Normalize to 0-255 uint8
        if max_val != min_val:
            pixel_array = (pixel_array - min_val) / (max_val - min_val) * 255.0
        else:
            pixel_array = pixel_array * 0
            
        return np.uint8(pixel_array), metadata
        
    except Exception as e:
        print(f"Error loading DICOM: {e}")
        return None, None

def load_image_array(image_path):
    """
    Loads a standard image (JPG/PNG) as a numpy array (grayscale) + metadata.
    Uses cv2.imdecode + np.fromfile to handle Unicode paths on Windows.
    """
    try:
        import cv2
        # Robust Unicode path loading
        # OpenCV's standard imread doesn't assume utf-8 on Windows
        # Solution: Read binary -> Decode
        stream = np.fromfile(image_path, dtype=np.uint8)
        img = cv2.imdecode(stream, cv2.IMREAD_GRAYSCALE)
        
        if img is None:
             raise ValueError("Görüntü okunamadı (Decode Error).")
             
        metadata = {
            "Filename": os.path.basename(image_path),
            "Size": f"{img.shape[1]}x{img.shape[0]}",
            "Mode": "Grayscale"
        }
        return img, metadata
    except Exception as e:
        print(f"Error loading Image: {e}")
        return None, None
