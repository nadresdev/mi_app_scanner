import cv2
import numpy as np
import os
import sys

# Importar configuración de Tesseract
try:
    from config.tesseract_config import TESSERACT_AVAILABLE, TESSERACT_PATH
    if TESSERACT_AVAILABLE:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
except ImportError as e:
    print(f"Error importando configuración Tesseract: {e}")
    TESSERACT_AVAILABLE = False
    TESSERACT_PATH = None

def preprocess_image_for_ocr(image):
    """Preprocesamiento avanzado para mejorar detección de dígitos"""
    try:
        # Convertir a escala de grises
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # 1. Reducir ruido con filtro bilateral (preserva bordes)
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # 2. Mejorar contraste con CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        contrast_enhanced = clahe.apply(denoised)
        
        # 3. Diferentes métodos de thresholding y elegir el mejor
        # Threshold adaptativo
        thresh_adaptive = cv2.adaptiveThreshold(
            contrast_enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Threshold Otsu
        _, thresh_otsu = cv2.threshold(contrast_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Operaciones morfológicas para limpiar la imagen
        kernel = np.ones((2,2), np.uint8)
        thresh_adaptive = cv2.morphologyEx(thresh_adaptive, cv2.MORPH_CLOSE, kernel)
        thresh_otsu = cv2.morphologyEx(thresh_otsu, cv2.MORPH_CLOSE, kernel)
        
        # Devolver ambas versiones para probar
        return thresh_adaptive, thresh_otsu
        
    except Exception as e:
        print(f"Error en preprocesamiento: {e}")
        return image, image

def extract_digits_advanced(image):
    """Extrae dígitos usando múltiples técnicas"""
    if not TESSERACT_AVAILABLE:
        return "Tesseract no disponible", None, None
    
    try:
        # Preprocesar imagen - obtener dos versiones
        processed_adaptive, processed_otsu = preprocess_image_for_ocr(image)
        
        # Configuraciones de Tesseract para probar
        configs = [
            '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789',
            '--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789',
            '--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789'
        ]
        
        best_digits = ""
        best_confidence = 0
        best_image = None
        
        # Probar diferentes combinaciones de preprocesamiento y configuraciones
        for config in configs:
            for processed_img, img_name in [(processed_adaptive, "adaptive"), (processed_otsu, "otsu")]:
                try:
                    # Ejecutar OCR
                    text = pytesseract.image_to_string(processed_img, config=config)
                    
                    # Filtrar solo dígitos
                    digits = ''.join(filter(str.isdigit, text.strip()))
                    
                    # Si encontramos dígitos, calcular confianza aproximada
                    if digits:
                        # Obtener datos de confianza (si está disponible)
                        data = pytesseract.image_to_data(processed_img, config=config, output_type=pytesseract.Output.DICT)
                        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                        
                        if confidences:
                            avg_confidence = sum(confidences) / len(confidences)
                        else:
                            avg_confidence = len(digits) * 10  # Confianza estimada
                        
                        # Mantener el resultado con mejor confianza
                        if avg_confidence > best_confidence:
                            best_confidence = avg_confidence
                            best_digits = digits
                            best_image = processed_img
                            
                except Exception as e:
                    continue
        
        return best_digits, best_image, best_confidence
        
    except Exception as e:
        return f"Error: {str(e)}", None, 0

def extract_digits_fast(image):
    """Versión rápida para uso en tiempo real - menos preciso pero más rápido"""
    if not TESSERACT_AVAILABLE:
        return "Tesseract no disponible", None
    
    try:
        # Preprocesamiento rápido
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Threshold simple y rápido
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Configuración más rápida
        config = '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789'
        
        # OCR rápido
        text = pytesseract.image_to_string(thresh, config=config)
        digits = ''.join(filter(str.isdigit, text.strip()))
        
        return digits, thresh
        
    except Exception as e:
        return f"Error: {str(e)}", None

def save_captured_image(image, filename):
    """Guarda la imagen capturada"""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        cv2.imwrite(filename, image)
        return True
    except Exception as e:
        print(f"Error guardando imagen: {e}")
        return False