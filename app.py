import streamlit as st
import cv2
import numpy as np
import os
import time
import subprocess
import sys
from PIL import Image

# ========== CONFIGURACIÓN TESSERACT PARA STREAMLIT CLOUD ==========
def setup_tesseract():
    """Configura Tesseract específicamente para Streamlit Cloud"""
    try:
        # En Streamlit Cloud, Tesseract está preinstalado en esta ruta
        tesseract_path = '/usr/bin/tesseract'
        
        if os.path.exists(tesseract_path):
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            
            # Verificar que funciona
            version = pytesseract.get_tesseract_version()
            st.success(f"✅ Tesseract configurado. Versión: {version}")
            return True, tesseract_path
        else:
            # Fallback: buscar en el sistema
            try:
                result = subprocess.run(
                    ['which', 'tesseract'], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                if result.returncode == 0:
                    tesseract_path = result.stdout.strip()
                    import pytesseract
                    pytesseract.pytesseract.tesseract_cmd = tesseract_path
                    st.success(f"✅ Tesseract encontrado via which: {tesseract_path}")
                    return True, tesseract_path
            except:
                pass
            
            st.error("❌ Tesseract no encontrado")
            return False, None
            
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return False, None

# Configurar Tesseract
TESSERACT_AVAILABLE, TESSERACT_PATH = setup_tesseract()

if TESSERACT_AVAILABLE:
    import pytesseract

# ========== FUNCIONES DE LA APLICACIÓN ==========
def draw_scanner_zone(frame, x, y, width, height):
    """Dibuja el rectángulo de escaneo"""
    # Rectángulo principal
    cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 0), 2)
    
    # Esquinas decorativas
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

def get_roi(image, x, y, width, height):
    """Extrae región de interés"""
    return image[y:y + height, x:x + width]

def preprocess_image_for_ocr(image):
    """Preprocesamiento para OCR"""
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Mejorar contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Threshold adaptativo
        processed = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        return processed
        
    except Exception as e:
        return image

def extract_digits(image):
    """Extrae dígitos de la imagen"""
    if not TESSERACT_AVAILABLE:
        return "Tesseract no disponible", None
    
    try:
        processed_image = preprocess_image_for_ocr(image)
        
        # Configuración optimizada para dígitos
        config = '--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789'
        
        text = pytesseract.image_to_string(processed_image, config=config)
        digits = ''.join(filter(str.isdigit, text.strip()))
        
        return digits, processed_image
        
    except Exception as e:
        return f"Error: {str(e)}", None

# ========== APLICACIÓN STREAMLIT ==========
st.set_page_config(
    page_title="Escáner de Dígitos",
    page_icon="🔢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado
st.markdown("""
<style>
    .main {
        background-color: #f0f2f6;
    }
    .stButton>button {
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }
    .digits-result {
        font-size: 2.5em;
        font-weight: bold;
        color: #00cc00;
        text-align: center;
        padding: 20px;
        background-color: #000000;
        border-radius: 10px;
        border: 2px solid #00cc00;
        margin: 10px 0;
    }
    .info-box {
        background-color: #e8f4fd;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #2196F3;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔢 Escáner de Dígitos con OCR")
st.markdown("---")

def main():
    # Información sobre Tesseract
    if not TESSERACT_AVAILABLE:
        st.error("""
        ❌ Tesseract OCR no está disponible en este momento.
        
        **Solución:**
        - Streamlit Cloud está configurando el entorno
        - Recarga la página en 1-2 minutos
        - Si el problema persiste, contacta con soporte
        """)
    else:
        st.success("✅ Tesseract OCR está listo para usar!")

    # Sidebar
    st.sidebar.title("⚙️ Configuración")
    
    # Configuración área de escaneo
    st.sidebar.subheader("Área de Escaneo")
    rect_x = st.sidebar.slider("Posición X", 50, 600, 150, 10)
    rect_y = st.sidebar.slider("Posición Y", 50, 400, 150, 10)
    rect_width = st.sidebar.slider("Ancho", 200, 500, 300, 10)
    rect_height = st.sidebar.slider("Alto", 80, 300, 120, 10)
    
    show_processed = st.sidebar.checkbox("Mostrar imagen procesada", value=True)
    
    # Estado de la aplicación
    if 'captured_digits' not in st.session_state:
        st.session_state.captured_digits = ""
        st.session_state.captured_image = None
        st.session_state.processed_image = None
    
    # Área principal - Solo modo subir imagen (para Streamlit Cloud)
    st.subheader("📤 Subir Imagen para Escanear Dígitos")
    
    uploaded_file = st.file_uploader(
        "Selecciona una imagen que contenga dígitos",
        type=['png', 'jpg', 'jpeg'],
        help="La imagen debe tener dígitos claros y buen contraste"
    )
    
    if uploaded_file is not None:
        # Leer imagen
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # Dibujar rectángulo en la imagen
        image_with_rect = draw_scanner_zone(image.copy(), rect_x, rect_y, rect_width, rect_height)
        
        # Mostrar imagen
        st.image(cv2.cvtColor(image_with_rect, cv2.COLOR_BGR2RGB), 
                use_column_width=True,
                caption="Imagen con área de escaneo - Los dígitos deben estar dentro del rectángulo verde")
        
        # Procesar al hacer clic
        if st.button("🔍 Escanear Dígitos", type="primary", use_container_width=True):
            with st.spinner("Procesando imagen con OCR..."):
                # Extraer ROI
                roi = get_roi(image, rect_x, rect_y, rect_width, rect_height)
                
                if roi.size > 0:
                    digits, processed = extract_digits(roi)
                    
                    st.session_state.captured_digits = digits
                    st.session_state.captured_image = roi
                    st.session_state.processed_image = processed
                    
                    if digits:
                        st.success(f"✅ Dígitos detectados: **{digits}**")
                        st.balloons()
                    else:
                        st.warning("⚠️ No se detectaron dígitos. Intenta con:")
                        st.markdown("""
                        - Mejor iluminación
                        - Dígitos más contrastados  
                        - Ajustar el área de escaneo
                        - Fuentes más simples
                        """)
                else:
                    st.error("❌ El área de escaneo está fuera de los límites de la imagen")
    
    # Mostrar resultados
    st.markdown("---")
    st.subheader("📊 Resultados")
    
    if st.session_state.captured_digits:
        st.markdown(f'<div class="digits-result">{st.session_state.captured_digits}</div>', 
                   unsafe_allow_html=True)
        
        # Mostrar imagen procesada
        if show_processed and st.session_state.processed_image is not None:
            with st.expander("🖼️ Ver imagen procesada por OCR"):
                st.image(st.session_state.processed_image, 
                        use_column_width=True,
                        caption="Imagen después del preprocesamiento para OCR",
                        clamp=True)
        
        # Botones de acción
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Copiar Resultados", use_container_width=True):
                st.code(st.session_state.captured_digits)
                st.success("✅ Resultados copiados al portapapeles")
        with col2:
            if st.button("🔄 Nueva Imagen", use_container_width=True):
                st.session_state.captured_digits = ""
                st.session_state.captured_image = None
                st.session_state.processed_image = None
                st.rerun()
    
    else:
        st.info("""
        <div class="info-box">
            <h3>👆 Cómo usar esta aplicación:</h3>
            <ol>
                <li><strong>Sube una imagen</strong> que contenga dígitos</li>
                <li><strong>Ajusta el área de escaneo</strong> en la barra lateral para que el rectángulo verde cubra los dígitos</li>
                <li><strong>Haz clic en "Escanear Dígitos"</strong> para procesar la imagen</li>
                <li><strong>Copia los resultados</strong> o sube una nueva imagen</li>
            </ol>
            
            <p><strong>💡 Consejos para mejor detección:</strong></p>
            <ul>
                <li>Usa imágenes con buen contraste</li>
                <li>Dígitos oscuros sobre fondo claro</li>
                <li>Evita sombras y reflejos</li>
                <li>Fuentes simples funcionan mejor</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Información técnica
    with st.expander("ℹ️ Información Técnica"):
        st.markdown(f"""
        **Estado del sistema:**
        - Tesseract OCR: {'✅ Disponible' if TESSERACT_AVAILABLE else '❌ No disponible'}
        - Ruta: {TESSERACT_PATH if TESSERACT_AVAILABLE else 'N/A'}
        
        **Características:**
        - 🟩 Rectángulo de escaneo ajustable
        - 🔢 Detección de dígitos con OCR
        - 📤 Subida de imágenes
        - 📋 Copia de resultados
        
        **Tecnologías:**
        - Streamlit para la interfaz
        - OpenCV para procesamiento de imágenes  
        - Tesseract OCR para reconocimiento de texto
        - Python para la lógica de la aplicación
        """)

if __name__ == "__main__":
    main()