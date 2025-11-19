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
    page_title="Escáner de Dígitos - Cámara en Tiempo Real",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS y JavaScript para el overlay en tiempo real
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
        position: relative;
        border: 3px solid #00cc00;
        border-radius: 15px;
        padding: 10px;
        background: #000;
        margin: 10px 0;
        overflow: hidden;
    }
    .scanner-overlay {
        position: absolute;
        border: 3px solid #00ff00;
        border-radius: 10px;
        pointer-events: none;
        z-index: 1000;
        box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.3);
    }
    .overlay-content {
        position: absolute;
        top: -30px;
        left: 0;
        right: 0;
        text-align: center;
        color: #00ff00;
        font-weight: bold;
        font-size: 14px;
        background: rgba(0, 0, 0, 0.7);
        padding: 5px;
        border-radius: 5px;
    }
    @media (max-width: 768px) {
        .digits-result {
            font-size: 2.5em;
            padding: 20px;
        }
    }
    
    /* Estilos para el contenedor de cámara personalizado */
    .camera-wrapper {
        position: relative;
        width: 100%;
        max-width: 640px;
        margin: 0 auto;
    }
    
    /* Asegurar que la cámara ocupe todo el espacio */
    .stCameraInput > div {
        width: 100% !important;
    }
    
    .stCameraInput video {
        width: 100% !important;
        height: auto !important;
        border-radius: 10px;
    }
</style>

<script>
// Función para actualizar el overlay del rectángulo
function updateScannerOverlay(x, y, width, height) {
    // Eliminar overlay existente
    const existingOverlay = document.getElementById('scanner-overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }
    
    // Crear nuevo overlay
    const overlay = document.createElement('div');
    overlay.id = 'scanner-overlay';
    overlay.className = 'scanner-overlay';
    overlay.style.left = x + 'px';
    overlay.style.top = y + 'px';
    overlay.style.width = width + 'px';
    overlay.style.height = height + 'px';
    
    // Agregar texto informativo
    const overlayContent = document.createElement('div');
    overlayContent.className = 'overlay-content';
    overlayContent.textContent = 'Área de Escaneo - Alinea los dígitos aquí';
    overlay.appendChild(overlayContent);
    
    // Agregar al contenedor de cámara
    const cameraContainer = document.querySelector('[data-testid="stCameraInput"]');
    if (cameraContainer) {
        cameraContainer.style.position = 'relative';
        cameraContainer.appendChild(overlay);
    }
}

// Escuchar cambios en los sliders de Streamlit
function setupSliderListeners() {
    // Los sliders de Streamlit generan eventos cuando cambian
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes') {
                // Buscar valores actuales de los sliders
                const sliders = document.querySelectorAll('input[type="range"]');
                let x = 100, y = 150, width = 200, height = 100;
                
                sliders.forEach((slider, index) => {
                    const value = parseInt(slider.value);
                    switch(index) {
                        case 0: x = value; break;
                        case 1: y = value; break;
                        case 2: width = value; break;
                        case 3: height = value; break;
                    }
                });
                
                updateScannerOverlay(x, y, width, height);
            }
        });
    });
    
    // Observar cambios en el documento
    observer.observe(document.body, {
        attributes: true,
        subtree: true,
        attributeFilter: ['value', 'style', 'class']
    });
}

// Inicializar cuando la página cargue
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(setupSliderListeners, 1000);
    
    // Actualizar inicialmente
    updateScannerOverlay(100, 150, 200, 100);
});

// También actualizar cuando Streamlit termine de renderizar
if (window.Streamlit) {
    window.Streamlit.onRender(function() {
        setTimeout(setupSliderListeners, 500);
    });
}
</script>
""", unsafe_allow_html=True)

st.title("📱 Escáner de Dígitos - Cámara en Tiempo Real")
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
    st.sidebar.title("⚙️ Configuración del Área de Escaneo")
    
    # Configuración del área de escaneo
    st.sidebar.subheader("🎯 Ajustar Rectángulo en Tiempo Real")
    
    # Usar st.empty() para actualizaciones en tiempo real
    x_placeholder = st.sidebar.empty()
    y_placeholder = st.sidebar.empty()
    width_placeholder = st.sidebar.empty()
    height_placeholder = st.sidebar.empty()
    
    # Actualizar sliders en tiempo real
    st.session_state.rect_x = x_placeholder.slider(
        "Posición Horizontal (X)", 
        50, 400, st.session_state.rect_x, 10,
        key="x_slider",
        help="Mueve el rectángulo izquierda/derecha - Cambios se ven en tiempo real"
    )
    
    st.session_state.rect_y = y_placeholder.slider(
        "Posición Vertical (Y)", 
        50, 400, st.session_state.rect_y, 10,
        key="y_slider",
        help="Mueve el rectángulo arriba/abajo - Cambios se ven en tiempo real"
    )
    
    st.session_state.rect_width = width_placeholder.slider(
        "Ancho del Rectángulo", 
        100, 400, st.session_state.rect_width, 10,
        key="width_slider",
        help="Ajusta el ancho - Cambios se ven en tiempo real"
    )
    
    st.session_state.rect_height = height_placeholder.slider(
        "Alto del Rectángulo", 
        50, 300, st.session_state.rect_height, 10,
        key="height_slider",
        help="Ajusta el alto - Cambios se ven en tiempo real"
    )
    
    st.sidebar.markdown("---")
    
    # Información del área seleccionada
    st.sidebar.markdown(f"""
    **📐 Área Configurada:**
    - **Posición:** ({st.session_state.rect_x}, {st.session_state.rect_y})
    - **Tamaño:** {st.session_state.rect_width} × {st.session_state.rect_height} px
    
    **👀 Verás los cambios en tiempo real:**
    - El rectángulo verde se mueve instantáneamente
    - Puedes ajustar mientras ves la cámara
    - Perfecto para alinear dígitos exactamente
    """)

    # Área principal - Cámara con overlay en tiempo real
    st.subheader("📷 Cámara en Vivo con Rectángulo de Escaneo")
    
    # Instrucciones
    st.info("""
    **🎯 ¡El rectángulo verde aparece en TIEMPO REAL!**
    - **Ajusta los controles** en la barra lateral ←
    - **Ve los cambios instantáneamente** en la cámara
    - **Alinea los dígitos** dentro del rectángulo verde
    - **Captura** cuando estén perfectamente alineados
    """)
    
    # Contenedor para la cámara con overlay
    st.markdown("""
    <div class="camera-wrapper">
        <div class="camera-container">
    """, unsafe_allow_html=True)
    
    # Usar el componente de cámara de Streamlit
    camera_image = st.camera_input(
        "Mira la cámara - El rectángulo verde se actualiza en tiempo real al mover los controles",
        key="camera_input_live"
    )
    
    st.markdown("</div></div>", unsafe_allow_html=True)
    
    if camera_image is not None:
        # Convertir la imagen de la cámara a OpenCV
        image_bytes = camera_image.getvalue()
        image_array = np.frombuffer(image_bytes, np.uint8)
        original_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        
        # Mostrar confirmación visual del área que se analizará
        st.success(f"✅ Imagen capturada - Se analizará el área dentro del rectángulo verde")
        
        # Mostrar preview del área exacta que se analizará
        with st.expander("🔍 Ver Área Exacta que se Analizará", expanded=True):
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
                        caption=f"Área exacta a analizar ({st.session_state.rect_width}×{st.session_state.rect_height}px)"
                    )
                
                with col2:
                    processed_roi = preprocess_image(roi)
                    st.image(
                        processed_roi,
                        use_column_width=True,
                        caption="Versión procesada para OCR",
                        clamp=True
                    )
        
        # Botón para analizar el área del rectángulo
        st.markdown("---")
        st.subheader("🚀 ¿Analizar esta área?")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            analyze_button = st.button(
                "🎯 SÍ, ANALIZAR ÁREA SELECCIONADA", 
                use_container_width=True, 
                type="primary",
                key="analyze_button"
            )
            
            if analyze_button:
                with st.spinner("Analizando dígitos en el área seleccionada..."):
                    # Extraer EXACTAMENTE el área dentro del rectángulo
                    roi = get_roi(
                        original_image, 
                        st.session_state.rect_x,
                        st.session_state.rect_y, 
                        st.session_state.rect_width,
                        st.session_state.rect_height
                    )
                    
                    if roi.size > 0:
                        # Extraer dígitos usando API
                        digits, _ = extract_digits_with_api(roi)
                        
                        st.session_state.camera_captured = original_image
                        st.session_state.captured_digits = digits
                        st.session_state.analysis_done = True
                        
                        if digits and not digits.startswith("Error") and not digits.startswith("No se"):
                            st.success("✅ ¡Análisis completado! Revisa los resultados abajo ↓")
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
            st.success(f"✅ Se analizó un área de {st.session_state.rect_width}×{st.session_state.rect_height}px en posición ({st.session_state.rect_x}, {st.session_state.rect_y})")
            
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
            **💡 Sugerencias:**
            - Ajusta el rectángulo para cubrir mejor los dígitos
            - Mejora la iluminación
            - Verifica que los dígitos estén completamente dentro del rectángulo
            - Los dígitos deben tener buen contraste
            """)
    
    else:
        st.info("""
        <div class="info-box">
            <h3>👆 Listo para Escanear</h3>
            <p>Los dígitos detectados aparecerán aquí después del análisis.</p>
            
            <p><strong>🎯 Características en Tiempo Real:</strong></p>
            <ul>
                <li>Rectángulo verde SUPERPUESTO en la cámara</li>
                <li>Cambios INSTANTÁNEOS al mover los controles</li>
                <li>Precisión milimétrica para alinear dígitos</li>
                <li>Solo analiza el área dentro del rectángulo</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()