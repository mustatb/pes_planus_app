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
    """
    try:
        img = Image.open(image_path).convert("L")
        metadata = {
            "Filename": image_path.split("\\")[-1],
            "Format": img.format,
            "Size": f"{img.size[0]}x{img.size[1]}",
            "Mode": img.mode
        }
        return np.array(img), metadata
    except Exception as e:
        print(f"Error loading Image: {e}")
        return None, None
