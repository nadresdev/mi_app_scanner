import os
import subprocess

def configure_tesseract():
    """Configura Tesseract automáticamente en Windows"""
    try:
        # Rutas comunes de Tesseract
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
        
        tesseract_path = None
        for path in possible_paths:
            if os.path.exists(path):
                tesseract_path = path
                break
        
        # Buscar en PATH
        if not tesseract_path:
            result = subprocess.run(['where', 'tesseract'], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                tesseract_path = result.stdout.strip().split('\n')[0]
        
        # Configurar
        if tesseract_path and os.path.exists(tesseract_path):
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            return True, tesseract_path
        else:
            return False, None
            
    except Exception as e:
        print(f"Error configurando Tesseract: {e}")
        return False, None

# ⚡⚡⚡ ESTAS SON LAS VARIABLES QUE SE EXPORTAN ⚡⚡⚡
TESSERACT_AVAILABLE, TESSERACT_PATH = configure_tesseract()

# Si Tesseract está disponible, hacer disponible pytesseract
if TESSERACT_AVAILABLE:
    import pytesseract