import streamlit as st
import cv2
import numpy as np
import os
import time
import subprocess
import sys
from PIL import Image

# ========== CONFIGURACIÓN TESSERACT OPTIMIZADA PARA STREAMLIT CLOUD ==========
def setup_tesseract():
    """Configura Tesseract para Streamlit Cloud"""
    try:
        # En Streamlit Cloud, usar ruta directa
        tesseract_cmd = '/usr/bin/tesseract'
        
        if os.path.exists(tesseract_cmd):
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            
            # Verificar que funciona
            version = pytesseract.get_tesseract_version()
            st.success(f"✅ Tesseract configurado. Versión: {version}")
            return True, tesseract_cmd
        else:
            # Intentar encontrar con which
            result = subprocess.run(['which', 'tesseract'], 
                                  capture_output=True, text=True, shell=False)
            if result.returncode == 0:
                tesseract_path = result.stdout.strip()
                import pytesseract
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
                st.success(f"✅ Tesseract encontrado en: {tesseract_path}")
                return True, tesseract_path
            else:
                st.error("❌ Tesseract no encontrado en el sistema")
                return False, None
                
    except Exception as e:
        st.error(f"❌ Error configurando Tesseract: {e}")
        return False, None

# Configurar Tesseract
TESSERACT_AVAILABLE, TESSERACT_PATH = setup_tesseract()

if TESSERACT_AVAILABLE:
    import pytesseract
# ========== FUNCIONES DE CÁMARA ==========
def initialize_camera(camera_index=0):
    """Inicializa la cámara (solo funciona localmente)"""
    try:
        cap = cv2.VideoCapture(camera_index)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            return cap
        else:
            return None
    except Exception as e:
        st.error(f"Error cámara: {e}")
        return None

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

def get_roi(frame, x, y, width, height):
    """Extrae región de interés"""
    return frame[y:y + height, x:x + width]

def release_camera(cap):
    """Libera la cámara"""
    if cap is not None:
        cap.release()

# ========== FUNCIONES OCR ==========
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

def save_captured_image(image, filename):
    """Guarda imagen capturada"""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        cv2.imwrite(filename, image)
        return True
    except Exception as e:
        return False

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
    .camera-placeholder {
        border: 2px dashed #cccccc;
        border-radius: 10px;
        padding: 50px;
        text-align: center;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔢 Escáner de Dígitos con Cámara")
st.markdown("---")

def main():
    # Verificar Tesseract
    if not TESSERACT_AVAILABLE:
        st.error("""
        ❌ Tesseract OCR no está disponible.
        
        **Para uso local:**
        1. Instala Tesseract en tu sistema
        2. Asegúrate de que esté en el PATH
        3. Reinicia la aplicación
        
        **En Streamlit Cloud:** La aplicación detectará Tesseract automáticamente.
        """)
    
    # Sidebar
    st.sidebar.title("⚙️ Configuración")
    
    # Modo de funcionamiento
    app_mode = st.sidebar.radio(
        "Modo de aplicación:",
        ["📷 Usar Cámara (Local)", "📤 Subir Imagen"],
        help="La cámara solo funciona localmente. En Streamlit Cloud usa 'Subir Imagen'"
    )
    
    # Configuración área de escaneo
    st.sidebar.subheader("Área de Escaneo")
    rect_x = st.sidebar.slider("Posición X", 50, 600, 150, 10)
    rect_y = st.sidebar.slider("Posición Y", 50, 400, 150, 10)
    rect_width = st.sidebar.slider("Ancho", 200, 500, 300, 10)
    rect_height = st.sidebar.slider("Alto", 80, 300, 120, 10)
    
    # Estado de la aplicación
    if 'camera_active' not in st.session_state:
        st.session_state.update({
            'camera_active': False,
            'captured_digits': "",
            'captured_image': None,
            'processed_image': None,
            'trigger_capture': False
        })
    
    # Área principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if app_mode == "📷 Usar Cámara (Local)":
            st.subheader("📷 Cámara en Tiempo Real")
            
            # Controles de cámara
            col1_1, col1_2 = st.columns(2)
            with col1_1:
                if not st.session_state.camera_active:
                    if st.button("🎥 Iniciar Cámara", use_container_width=True, type="primary"):
                        st.session_state.camera_active = True
                        st.rerun()
                else:
                    if st.button("⏹️ Detener Cámara", use_container_width=True):
                        st.session_state.camera_active = False
                        st.rerun()
            
            with col1_2:
                if st.session_state.camera_active:
                    if st.button("📸 Capturar", use_container_width=True, type="secondary"):
                        st.session_state.trigger_capture = True
                        st.rerun()
            
            # Video en tiempo real
            if st.session_state.camera_active:
                video_placeholder = st.empty()
                status_placeholder = st.empty()
                
                cap = initialize_camera(0)
                if cap is None:
                    st.error("""
                    ❌ No se pudo acceder a la cámara.
                    
                    **Posibles soluciones:**
                    - Verifica que la cámara esté conectada
                    - Asegúrate de que no esté siendo usada por otra aplicación
                    - En Streamlit Cloud, usa el modo 'Subir Imagen'
                    """)
                    st.session_state.camera_active = False
                    st.rerun()
                
                try:
                    # Mostrar video
                    while st.session_state.camera_active and not st.session_state.trigger_capture:
                        ret, frame = cap.read()
                        if ret:
                            frame_with_rect = draw_scanner_zone(frame.copy(), rect_x, rect_y, rect_width, rect_height)
                            frame_rgb = cv2.cvtColor(frame_with_rect, cv2.COLOR_BGR2RGB)
                            video_placeholder.image(frame_rgb, use_column_width=True,
                                                  caption="Coloca los dígitos en el rectángulo verde")
                        time.sleep(0.03)
                    
                    # Procesar captura
                    if st.session_state.trigger_capture:
                        ret, frame = cap.read()
                        if ret:
                            roi = get_roi(frame, rect_x, rect_y, rect_width, rect_height)
                            if roi.size > 0:
                                with st.spinner("Procesando imagen..."):
                                    digits, processed = extract_digits(roi)
                                    
                                    st.session_state.captured_digits = digits
                                    st.session_state.captured_image = roi
                                    st.session_state.processed_image = processed
                                    
                                    if digits:
                                        status_placeholder.success(f"✅ Dígitos detectados: {digits}")
                                        st.balloons()
                                    else:
                                        status_placeholder.warning("No se detectaron dígitos")
                                
                                # Guardar
                                timestamp = int(time.time())
                                save_captured_image(roi, f"temp/capture_{timestamp}.jpg")
                            
                            st.session_state.trigger_capture = False
                    
                    release_camera(cap)
                    
                except Exception as e:
                    st.error(f"Error con la cámara: {e}")
                    st.session_state.camera_active = False
            
            else:
                st.markdown("""
                <div class="camera-placeholder">
                    <h3>🎥 Cámara No Activa</h3>
                    <p>Presiona "Iniciar Cámara" para comenzar</p>
                    <p><small><em>Nota: La cámara solo funciona en entornos locales</em></small></p>
                </div>
                """, unsafe_allow_html=True)
        
        else:  # Modo subir imagen
            st.subheader("📤 Subir Imagen para Escanear")
            
            uploaded_file = st.file_uploader(
                "Selecciona una imagen con dígitos",
                type=['png', 'jpg', 'jpeg'],
                help="Sube una imagen que contenga dígitos para escanear"
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
                if st.button("🔍 Escanear Dígitos", type="primary"):
                    with st.spinner("Procesando imagen..."):
                        # Extraer ROI
                        roi = get_roi(image, rect_x, rect_y, rect_width, rect_height)
                        
                        if roi.size > 0:
                            digits, processed = extract_digits(roi)
                            
                            st.session_state.captured_digits = digits
                            st.session_state.captured_image = roi
                            st.session_state.processed_image = processed
                            
                            if digits:
                                st.success(f"✅ Dígitos detectados: {digits}")
                                st.balloons()
                            else:
                                st.warning("No se detectaron dígitos en la imagen")
                        else:
                            st.error("El área de escaneo está fuera de los límites de la imagen")
    
    with col2:
        st.subheader("📊 Resultados")
        
        if st.session_state.captured_digits:
            st.markdown(f'<div class="digits-result">{st.session_state.captured_digits}</div>', 
                       unsafe_allow_html=True)
            
            # Mostrar imagen procesada
            if st.session_state.processed_image is not None:
                with st.expander("🖼️ Ver imagen procesada"):
                    st.image(st.session_state.processed_image, 
                            use_column_width=True,
                            caption="Imagen después del preprocesamiento",
                            clamp=True)
            
            # Botones de acción
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                if st.button("📋 Copiar", use_container_width=True):
                    st.code(st.session_state.captured_digits)
            with col2_2:
                if st.button("🔄 Limpiar", use_container_width=True):
                    st.session_state.captured_digits = ""
                    st.session_state.captured_image = None
                    st.session_state.processed_image = None
                    st.rerun()
        
        else:
            st.info("""
            **Los resultados aparecerán aquí:**
            - Dígitos detectados
            - Opción para copiar
            - Imagen procesada
            """)
        
        # Información de la aplicación
        with st.expander("ℹ️ Información"):
            st.markdown("""
            **Características:**
            - 🟩 Rectángulo verde para ubicar dígitos
            - 📷 Modo cámara (local)
            - 📤 Subir imágenes (Streamlit Cloud)
            - 🔢 Detección de dígitos con OCR
            - 📋 Copiar resultados
            
            **Recomendaciones:**
            - Buena iluminación
            - Dígitos claros y contrastados
            - Fuentes simples
            - Evitar sombras y reflejos
            """)

if __name__ == "__main__":
    os.makedirs('temp', exist_ok=True)
    main()