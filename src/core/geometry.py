import math

def calculate_angle(p1, p2, p3, p4):
    """
    Calculates the angle between two lines defined by (p1, p2) and (p3, p4).
    Points are tuples (x, y).
    Returns angle in degrees.
    """
    # Vector 1
    v1_x = p2[0] - p1[0]
    v1_y = p2[1] - p1[1]
    
    # Vector 2
    v2_x = p4[0] - p3[0]
    v2_y = p4[1] - p3[1]
    
    dot = v1_x * v2_x + v1_y * v2_y
    mag1 = math.sqrt(v1_x**2 + v1_y**2)
    mag2 = math.sqrt(v2_x**2 + v2_y**2)
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
        
    cos_theta = dot / (mag1 * mag2)
    cos_theta = max(min(cos_theta, 1.0), -1.0)
    
    angle = math.degrees(math.acos(cos_theta))
    
    # We typically want the acute angle for this medical measurement
    # But strictly speaking, calcaneal pitch is specific. 
    # For this tool, we'll return the raw vector angle, but ensure it's <= 180.
    # If the user draws lines in opposite directions, the angle might be obtuse.
    # We can normalize it to be <= 90 if that's the convention, but let's stick to vector angle for now.
    
    return round(angle, 2)

def get_angle_classification(angle, mode="calcaneal"):
    """
    Returns (category_name, color_hex) based on the angle and mode.
    """
    if mode == "calcaneal":
        # Calcaneal Pitch Angle (User Definition)
        # < 15: Pes Planus
        # 15-20: Borderline
        # >= 20: Normal
        if angle < 15:
            return "Pes Planus", "#ff7675" # Red
        elif 15 <= angle < 20:
            return "Borderline", "#ffeaa7" # Orange
        else:
            return "Normal", "#55efc4" # Green
            
    elif mode == "mearys":
        # Meary's Angle (Talo-First Metatarsal Angle)
        # Normal: 0° (aligned)
        # Mild Flatfoot: 1-15° (convex downward)
        # Severe Flatfoot: > 15°
        # We take absolute value for simplicity in this basic tool, 
        # assuming the user might draw lines in any order.
        # Ideally, we'd check direction, but let's assume deviation from 180 (straight) 
        # or 0 depending on how lines are drawn. 
        # Our calculate_angle returns 0-180. 
        # If lines are parallel (straight line), angle is 0 or 180.
        # Let's assume the user draws two lines that meet at a vertex.
        # A straight line would be 180 degrees if head-to-tail, or 0 if tail-to-tail.
        # For this tool, we will assume the angle returned is the intersection angle.
        # Meary's angle is typically the deviation from 0 (straight).
        # If our calculate_angle returns ~180 for a straight line (vectors opposing), 
        # then deviation is abs(180 - angle).
        # If it returns ~0 (vectors parallel), deviation is angle.
        
        # Heuristic: Meary's angle is usually small (< 30). 
        # If angle is > 150, it's likely a straight line measured as 180.
        
        deviation = angle
        if angle > 90:
            deviation = abs(180 - angle)
            
        if deviation <= 4:
            return "Normal", "#55efc4"
        elif 4 < deviation <= 15:
            return "Hafif Pes Planus", "#ffeaa7"
        elif 15 < deviation <= 30:
            return "Şiddetli Pes Planus", "#ff7675"
        else:
            return "Deformite / Hata", "#fab1a0"
            
    return "Bilinmiyor", "#b2bec3"
