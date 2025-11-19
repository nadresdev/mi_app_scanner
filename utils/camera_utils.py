import cv2
import numpy as np

def initialize_camera(camera_index=0):
    """
    Inicializa la cámara
    """
    cap = cv2.VideoCapture(camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return cap

def draw_scanner_zone(frame, x, y, width, height):
    """
    Dibuja la zona de escaneo verde en el frame
    """
    # Dibujar rectángulo principal
    cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 0), 2)
    
    # Dibujar esquinas decorativas
    corner_length = 20
    thickness = 3
    
    # Esquina superior izquierda
    cv2.line(frame, (x, y), (x + corner_length, y), (0, 255, 0), thickness)
    cv2.line(frame, (x, y), (x, y + corner_length), (0, 255, 0), thickness)
    
    # Esquina superior derecha
    cv2.line(frame, (x + width, y), (x + width - corner_length, y), (0, 255, 0), thickness)
    cv2.line(frame, (x + width, y), (x + width, y + corner_length), (0, 255, 0), thickness)
    
    # Esquina inferior izquierda
    cv2.line(frame, (x, y + height), (x + corner_length, y + height), (0, 255, 0), thickness)
    cv2.line(frame, (x, y + height), (x, y + height - corner_length), (0, 255, 0), thickness)
    
    # Esquina inferior derecha
    cv2.line(frame, (x + width, y + height), (x + width - corner_length, y + height), (0, 255, 0), thickness)
    cv2.line(frame, (x + width, y + height), (x + width, y + height - corner_length), (0, 255, 0), thickness)
    
    return frame

def get_roi(frame, x, y, width, height):
    """
    Extrae la región de interés (ROI) del frame
    """
    roi = frame[y:y + height, x:x + width]
    return roi

def release_camera(cap):
    """
    Libera los recursos de la cámara
    """
    if cap is not None:
        cap.release()