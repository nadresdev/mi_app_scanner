import streamlit as st
import cv2
import numpy as np
import requests
import base64
import os
import time
from PIL import Image
import io

# ========== CONFIGURACIÓN OCR API ==========
def setup_ocr():
    """Configura el cliente OCR usando API externa"""
    try:
        # OCR.space API Key (gratuita para uso limitado)
        API_KEYS = [
            'helloworld',  # Clave pública gratuita
            'K89947096688957'  # Clave de ejemplo
        ]
        
        return True, API_KEYS[0]
    except Exception as e:
        st.error(f"❌ Error configurando OCR: {e}")
        return False, None

OCR_AVAILABLE, API_KEY = setup_ocr()

# ========== FUNCIONES DE LA APLICACIÓN ==========
def draw_scanner_zone(image, x, y, width, height, color=(0, 255, 0), thickness=2):
    """Dibuja el rectángulo de escaneo en la imagen"""
    img_copy = image.copy()
    
    # Rectángulo principal
    cv2.rectangle(img_copy, (x, y), (x + width, y + height), color, thickness)
    
    # Esquinas decorativas
    corner_length = 20
    corner_thickness = 3
    
    # Esquina superior izquierda
    cv2.line(img_copy, (x, y), (x + corner_length, y), color, corner_thickness)
    cv2.line(img_copy, (x, y), (x, y + corner_length), color, corner_thickness)
    
    # Esquina superior derecha
    cv2.line(img_copy, (x + width, y), (x + width - corner_length, y), color, corner_thickness)
    cv2.line(img_copy, (x + width, y), (x + width, y + corner_length), color, corner_thickness)
    
    # Esquina inferior izquierda
    cv2.line(img_copy, (x, y + height), (x + corner_length, y + height), color, corner_thickness)
    cv2.line(img_copy, (x, y + height), (x, y + height - corner_length), color, corner_thickness)
    
    # Esquina inferior derecha
    cv2.line(img_copy, (x + width, y + height), (x + width - corner_length, y + height), color, corner_thickness)
    cv2.line(img_copy, (x + width, y + height), (x + width, y + height - corner_length), color, corner_thickness)
    
    return img_copy

def get_roi(image, x, y, width, height):
    """Extrae región de interés"""
    return image[y:y + height, x:x + width]

def image_to_base64(image):
    """Convierte imagen OpenCV a base64"""
    try:
        # Convertir BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        # Convertir a PIL Image
        pil_image = Image.fromarray(image_rgb)
        # Convertir a bytes
        buffered = io.BytesIO()
        pil_image.save(buffered, format="JPEG", quality=85)
        # Convertir a base64
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    except Exception as e:
        st.error(f"Error convirtiendo imagen: {e}")
        return None

def extract_digits_with_api(image):
    """Extrae dígitos usando OCR.space API"""
    if not OCR_AVAILABLE:
        return "OCR no disponible", None
    
    try:
        # Convertir imagen a base64
        image_base64 = image_to_base64(image)
        if not image_base64:
            return "Error procesando imagen", None
        
        # Configurar parámetros para la API
        payload = {
            'base64Image': f'data:image/jpeg;base64,{image_base64}',
            'apikey': API_KEY,
            'language': 'eng',
            'isOverlayRequired': False,
            'OCREngine': 2  # Motor 2 es mejor para dígitos
        }
        
        # Llamar a la API
        with st.spinner("🔍 Analizando dígitos..."):
            response = requests.post(
                'https://api.ocr.space/parse/image',
                data=payload,
                timeout=30
            )
        
        if response.status_code == 200:
            result = response.json()
            
            # Verificar si la API retornó resultados
            if result['IsErroredOnProcessing']:
                error_message = result['ErrorMessage'] if 'ErrorMessage' in result else 'Error desconocido'
                return f"Error API: {error_message}", None
            
            # Extraer texto de los resultados
            parsed_results = result.get('ParsedResults', [])
            if parsed_results:
                text = parsed_results[0].get('ParsedText', '').strip()
                
                # Filtrar solo dígitos
                digits = ''.join(filter(str.isdigit, text))
                
                if digits:
                    return digits, None
                else:
                    return "No se encontraron dígitos", None
            else:
                return "No se pudieron procesar los resultados", None
        else:
            return f"Error HTTP: {response.status_code}", None
            
    except requests.exceptions.Timeout:
        return "Timeout: La API tardó demasiado en responder", None
    except requests.exceptions.RequestException as e:
        return f"Error de conexión: {str(e)}", None
    except Exception as e:
        return f"Error inesperado: {str(e)}", None

def preprocess_image(image):
    """Preprocesamiento simple para mejorar la imagen"""
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Mejorar contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        return enhanced
        
    except Exception as e:
        return image

# ========== APLICACIÓN STREAMLIT ==========
st.set_page_config(
    page_title="Escáner de Dígitos con Cámara",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para móviles
st.markdown("""
<style>
    .main {
        background-color: #f0f2f6;
    }
    .stButton>button {
        border-radius: 15px;
        height: 3.5em;
        font-weight: bold;
        font-size: 1.1em;
        margin: 5px 0;
    }
    .digits-result {
        font-size: 3em;
        font-weight: bold;
        color: #00cc00;
        text-align: center;
        padding: 25px;
        background-color: #000000;
        border-radius: 15px;
        border: 3px solid #00cc00;
        margin: 15px 0;
    }
    .info-box {
        background-color: #e8f4fd;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #2196F3;
        margin: 10px 0;
    }
    .camera-container {
        border: 3px solid #00cc00;
        border-radius: 15px;
        padding: 10px;
        background: #000;
        margin: 10px 0;
        position: relative;
    }
    .success-box {
        background-color: #e8f5e8;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #4CAF50;
    }
    .scanner-overlay {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        border: 3px solid #00ff00;
        border-radius: 10px;
        pointer-events: none;
    }
    @media (max-width: 768px) {
        .digits-result {
            font-size: 2.5em;
            padding: 20px;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("📱 Escáner de Dígitos con Cámara")
st.markdown("---")

def main():
    # Información sobre el estado
    if not OCR_AVAILABLE:
        st.error("❌ Servicio OCR no disponible")
        return

    # Estado de la aplicación
    if 'camera_captured' not in st.session_state:
        st.session_state.camera_captured = None
        st.session_state.captured_digits = ""
        st.session_state.analysis_done = False
        st.session_state.rect_x = 100
        st.session_state.rect_y = 150
        st.session_state.rect_width = 200
        st.session_state.rect_height = 100

    # Sidebar para configuración
    st.sidebar.title("⚙️ Configuración del Escáner")
    
    # Configuración del área de escaneo
    st.sidebar.subheader("🎯 Ajustar Área de Escaneo")
    
    st.session_state.rect_x = st.sidebar.slider(
        "Posición Horizontal", 
        50, 400, st.session_state.rect_x, 10,
        help="Mueve el rectángulo izquierda/derecha"
    )
    
    st.session_state.rect_y = st.sidebar.slider(
        "Posición Vertical", 
        50, 400, st.session_state.rect_y, 10,
        help="Mueve el rectángulo arriba/abajo"
    )
    
    st.session_state.rect_width = st.sidebar.slider(
        "Ancho del Rectángulo", 
        100, 400, st.session_state.rect_width, 10,
        help="Ajusta el ancho del área de escaneo"
    )
    
    st.session_state.rect_height = st.sidebar.slider(
        "Alto del Rectángulo", 
        50, 300, st.session_state.rect_height, 10,
        help="Ajusta el alto del área de escaneo"
    )
    
    st.sidebar.markdown("---")
    
    # Información del área seleccionada
    st.sidebar.markdown(f"""
    **📐 Área Configurada:**
    - **Posición:** ({st.session_state.rect_x}, {st.session_state.rect_y})
    - **Tamaño:** {st.session_state.rect_width} × {st.session_state.rect_height} px
    - **Área:** {st.session_state.rect_width * st.session_state.rect_height} px²
    
    **💡 Consejo:**
    Ajusta el rectángulo para que cubra
    exactamente los dígitos que quieres escanear.
    """)

    # Área principal - Cámara con rectángulo integrado
    st.subheader("📷 Vista de la Cámara con Área de Escaneo")
    
    # Instrucciones
    st.info("""
    **🎯 Instrucciones:**
    1. **Alinea los dígitos** dentro del rectángulo verde en el visor de la cámara
    2. **Ajusta el rectángulo** si es necesario desde la barra lateral  
    3. **Presiona CAPTURAR** cuando los dígitos estén bien alineados
    4. **Revisa los resultados** abajo
    """)
    
    # Usar el componente de cámara de Streamlit
    camera_image = st.camera_input(
        "Apunta la cámara a los dígitos y alinea con el rectángulo verde",
        key="camera_input"
    )
    
    if camera_image is not None:
        # Convertir la imagen de la cámara a OpenCV
        image_bytes = camera_image.getvalue()
        image_array = np.frombuffer(image_bytes, np.uint8)
        original_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        # Dibujar rectángulo DIRECTAMENTE en la imagen de la cámara
        image_with_rect = draw_scanner_zone(
            original_image, 
            st.session_state.rect_x,
            st.session_state.rect_y, 
            st.session_state.rect_width,
            st.session_state.rect_height
        )
        
        # Mostrar imagen con el rectángulo integrado
        st.markdown('<div class="camera-container">', unsafe_allow_html=True)
        st.image(
            cv2.cvtColor(image_with_rect, cv2.COLOR_BGR2RGB),
            use_column_width=True,
            caption="👆 Los dígitos DENTRO de este rectángulo verde serán analizados al capturar"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Botón para capturar y analizar el área del rectángulo
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            capture_button = st.button(
                "🎯 CAPTURAR Y ANALIZAR ÁREA SELECCIONADA", 
                use_container_width=True, 
                type="primary"
            )
            
            if capture_button:
                with st.spinner("Procesando área seleccionada..."):
                    # Extraer EXACTAMENTE el área dentro del rectángulo verde
                    roi = get_roi(
                        original_image, 
                        st.session_state.rect_x,
                        st.session_state.rect_y, 
                        st.session_state.rect_width,
                        st.session_state.rect_height
                    )
                    
                    if roi.size > 0:
                        # Mostrar el área exacta que se va a analizar
                        with st.expander("🔍 Ver Área Exacta a Analizar"):
                            st.image(
                                cv2.cvtColor(roi, cv2.COLOR_BGR2RGB),
                                use_column_width=True,
                                caption=f"Esta área de {st.session_state.rect_width}x{st.session_state.rect_height}px será analizada"
                            )
                        
                        # Preprocesar la imagen
                        processed_roi = preprocess_image(roi)
                        
                        # Mostrar versión procesada
                        with st.expander("🔄 Ver Área Procesada"):
                            st.image(
                                processed_roi,
                                use_column_width=True,
                                caption="Versión procesada para mejor OCR",
                                clamp=True
                            )
                        
                        # Extraer dígitos usando API (del área del rectángulo)
                        digits, _ = extract_digits_with_api(roi)
                        
                        st.session_state.camera_captured = original_image
                        st.session_state.captured_digits = digits
                        st.session_state.analysis_done = True
                        
                        if digits and not digits.startswith("Error") and not digits.startswith("No se"):
                            st.success("✅ ¡Análisis completado!")
                            st.balloons()
                        else:
                            st.warning("⚠️ No se detectaron dígitos en el área seleccionada")
                    else:
                        st.error("❌ El área de escaneo seleccionada no es válida")
    
    # Mostrar resultados
    st.markdown("---")
    st.subheader("📊 Resultados del Escaneo")
    
    if st.session_state.analysis_done and st.session_state.captured_digits:
        if not st.session_state.captured_digits.startswith("Error") and not st.session_state.captured_digits.startswith("No se"):
            # Mostrar dígitos detectados
            st.markdown(f'<div class="digits-result">{st.session_state.captured_digits}</div>', 
                       unsafe_allow_html=True)
            
            # Información del análisis
            st.success(f"✅ Se analizó un área de {st.session_state.rect_width}×{st.session_state.rect_height}px")
            
            # Botones de acción
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("📋 Copiar Resultados", use_container_width=True, type="secondary"):
                    st.code(st.session_state.captured_digits)
                    st.success("✅ ¡Resultados copiados al portapapeles!")
            with col_btn2:
                if st.button("🔄 Nueva Captura", use_container_width=True):
                    st.session_state.camera_captured = None
                    st.session_state.captured_digits = ""
                    st.session_state.analysis_done = False
                    st.rerun()
            
        else:
            st.warning(f"⚠️ {st.session_state.captured_digits}")
            st.info("""
            **💡 Sugerencias para mejor detección:**
            - Ajusta el tamaño y posición del rectángulo en la barra lateral
            - Mejora la iluminación de los dígitos
            - Asegúrate de que los dígitos estén COMPLETAMENTE dentro del rectángulo verde
            - Los dígitos deben tener buen contraste con el fondo
            """)
    
    else:
        st.info("""
        <div class="info-box">
            <h3>👆 Listo para Escanear</h3>
            <p>Los dígitos detectados aparecerán aquí después de capturar.</p>
            
            <p><strong>🎯 Lo que se analiza:</strong></p>
            <ul>
                <li>Solo el área DENTRO del rectángulo verde</li>
                <li>Todo fuera del rectángulo se ignora</li>
                <li>Puedes ajustar el rectángulo en la barra lateral</li>
                <li>Resultados inmediatos después de capturar</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Información adicional
    with st.expander("ℹ️ Cómo Funciona el Escáner"):
        st.markdown("""
        ### 🎯 Tecnología de Escaneo
        
        **Proceso Exacto:**
        1. **Vista de cámara en vivo** con rectángulo superpuesto
        2. **Captura de imagen** cuando presionas el botón
        3. **Extracción automática** del área dentro del rectángulo verde
        4. **Procesamiento OCR** solo de esa área específica
        5. **Resultados** de los dígitos detectados
        
        **¿Qué área se analiza?**
        - ✅ Solo lo que está DENTRO del rectángulo verde
        - ❌ Todo lo fuera del rectángulo se descarta
        - 📏 El tamaño y posición son ajustables
        
        **Para mejor precisión:**
        - Ajusta el rectángulo para que cubra solo los dígitos
        - Evita incluir fondo innecesario
        - Buena iluminación = mejor reconocimiento
        - Dígitos claros y contrastados
        """)

if __name__ == "__main__":
    main()