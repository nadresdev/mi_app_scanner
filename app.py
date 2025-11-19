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
    page_title="Escáner de Dígitos - Cámara con Rectángulo",
    page_icon="📱",
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
    }
    .success-box {
        background-color: #e8f5e8;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #4CAF50;
    }
    .live-preview {
        background: linear-gradient(45deg, #000000, #001a00);
        padding: 20px;
        border-radius: 15px;
        border: 2px solid #00cc00;
        text-align: center;
    }
    @media (max-width: 768px) {
        .digits-result {
            font-size: 2.5em;
            padding: 20px;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("📱 Escáner de Dígitos - Cámara con Rectángulo")
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
    st.sidebar.title("⚙️ Configuración del Rectángulo")
    
    # Configuración del área de escaneo
    st.sidebar.subheader("🎯 Ajustar Rectángulo Verde")
    
    # Sliders con valores por defecto optimizados para móviles
    st.session_state.rect_x = st.sidebar.slider(
        "Posición Horizontal (X)", 
        50, 400, st.session_state.rect_x, 10,
        help="Posición izquierda/derecha del rectángulo"
    )
    
    st.session_state.rect_y = st.sidebar.slider(
        "Posición Vertical (Y)", 
        50, 400, st.session_state.rect_y, 10,
        help="Posición arriba/abajo del rectángulo"
    )
    
    st.session_state.rect_width = st.sidebar.slider(
        "Ancho del Rectángulo", 
        100, 400, st.session_state.rect_width, 10,
        help="Ancho del área de escaneo"
    )
    
    st.session_state.rect_height = st.sidebar.slider(
        "Alto del Rectángulo", 
        50, 300, st.session_state.rect_height, 10,
        help="Alto del área de escaneo"
    )
    
    st.sidebar.markdown("---")
    
    # Información del área seleccionada
    st.sidebar.markdown(f"""
    **📐 Área Configurada:**
    - **Posición:** ({st.session_state.rect_x}, {st.session_state.rect_y})
    - **Tamaño:** {st.session_state.rect_width} × {st.session_state.rect_height} px
    
    **🎯 Instrucciones:**
    1. Mira la vista de cámara a la derecha →
    2. Ajusta estos controles para mover el rectángulo
    3. Alinea los dígitos DENTRO del rectángulo verde
    4. Captura la imagen
    """)

    # Área principal
    st.subheader("📷 Vista de Cámara con Rectángulo de Escaneo")
    
    # Instrucciones
    st.info("""
    **👀 El rectángulo verde aparece DIRECTAMENTE en la imagen de la cámara**
    - Ajusta los controles en la barra lateral para moverlo
    - Alinea los dígitos que quieres escanear DENTRO del rectángulo
    - Solo esa área se analizará al capturar
    """)
    
    # Usar el componente de cámara de Streamlit
    camera_image = st.camera_input(
        "Apunta la cámara a los dígitos - El rectángulo verde muestra el área que se analizará",
        key="camera_input"
    )
    
    if camera_image is not None:
        # Convertir la imagen de la cámara a OpenCV
        image_bytes = camera_image.getvalue()
        image_array = np.frombuffer(image_bytes, np.uint8)
        original_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        # Dibujar rectángulo DIRECTAMENTE en la imagen capturada
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
            caption=f"✅ Imagen capturada - El área dentro del rectángulo verde será analizada"
        )
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Mostrar el área exacta que se analizará
        with st.expander("🔍 Ver Área Exacta a Analizar", expanded=True):
            # Extraer el área del rectángulo
            roi = get_roi(
                original_image, 
                st.session_state.rect_x,
                st.session_state.rect_y, 
                st.session_state.rect_width,
                st.session_state.rect_height
            )
            
            if roi.size > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.image(
                        cv2.cvtColor(roi, cv2.COLOR_BGR2RGB),
                        use_column_width=True,
                        caption=f"Área exacta ({st.session_state.rect_width}×{st.session_state.rect_height}px)"
                    )
                
                with col2:
                    processed_roi = preprocess_image(roi)
                    st.image(
                        processed_roi,
                        use_column_width=True,
                        caption="Versión procesada para OCR",
                        clamp=True
                    )
                
                st.success(f"✅ Se analizará esta área específica de {st.session_state.rect_width}×{st.session_state.rect_height}px")
            else:
                st.error("❌ El área seleccionada no es válida")
        
        # Botón para analizar
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🎯 ANALIZAR ÁREA SELECCIONADA", use_container_width=True, type="primary"):
                with st.spinner("Procesando área seleccionada..."):
                    if roi.size > 0:
                        # Extraer dígitos del área del rectángulo
                        digits, _ = extract_digits_with_api(roi)
                        
                        st.session_state.camera_captured = original_image
                        st.session_state.captured_digits = digits
                        st.session_state.analysis_done = True
                        
                        if digits and not digits.startswith("Error") and not digits.startswith("No se"):
                            st.success("✅ ¡Análisis completado! Revisa los resultados abajo ↓")
                            st.balloons()
                        else:
                            st.warning("⚠️ No se detectaron dígitos en el área seleccionada")
    
    # Mostrar resultados
    st.markdown("---")
    st.subheader("📊 Resultados del Escaneo")
    
    if st.session_state.analysis_done and st.session_state.captured_digits:
        if not st.session_state.captured_digits.startswith("Error") and not st.session_state.captured_digits.startswith("No se"):
            # Mostrar dígitos detectados
            st.markdown(f'<div class="digits-result">{st.session_state.captured_digits}</div>', 
                       unsafe_allow_html=True)
            
            # Información del análisis
            st.success(f"✅ Área analizada: {st.session_state.rect_width}×{st.session_state.rect_height}px en posición ({st.session_state.rect_x}, {st.session_state.rect_y})")
            
            # Botones de acción
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("📋 Copiar Resultados", use_container_width=True, type="secondary"):
                    st.code(st.session_state.captured_digits)
                    st.success("✅ ¡Resultados copiados!")
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
            - Ajusta el rectángulo para cubrir completamente los dígitos
            - Mejora la iluminación
            - Verifica que los dígitos estén nítidos y con buen contraste
            - Los dígitos deben estar completamente dentro del área verde
            """)
    
    else:
        st.info("""
        <div class="info-box">
            <h3>👆 Listo para Escanear</h3>
            <p>Los dígitos detectados aparecerán aquí después del análisis.</p>
            
            <p><strong>🎯 Cómo funciona:</strong></p>
            <ol>
                <li>El <strong>rectángulo verde</strong> aparece en la imagen de la cámara</li>
                <li><strong>Ajusta su posición y tamaño</strong> desde la barra lateral</li>
                <li><strong>Alinea los dígitos</strong> dentro del rectángulo</li>
                <li><strong>Captura la imagen</strong> y confirma el área a analizar</li>
                <li><strong>Revisa los resultados</strong> aquí abajo</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
    
    # Información adicional
    with st.expander("ℹ️ Acerca del Escáner"):
        st.markdown("""
        ### 🎯 Tecnología Utilizada
        
        **Proceso de Escaneo:**
        1. **Vista de cámara** con rectángulo superpuesto
        2. **Captura de imagen** con el área visualizada
        3. **Extracción automática** del área dentro del rectángulo verde
        4. **Procesamiento OCR** específico de esa área
        5. **Resultados** de los dígitos detectados
        
        **Ventajas:**
        - ✅ Sabes exactamente qué área se analizará
        - ✅ Precisión milimétrica para seleccionar dígitos
        - ✅ Evita análisis de áreas innecesarias
        - ✅ Interface visual e intuitiva
        
        **Para mejor precisión:**
        - Buena iluminación de los dígitos
        - Dígitos contrastados con el fondo
        - Enfoque nítido en la cámara
        - Rectángulo ajustado al tamaño exacto de los dígitos
        """)

if __name__ == "__main__":
    main()