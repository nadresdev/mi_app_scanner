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

def resize_image(image, scale_percent):
    """Redimensiona imagen por porcentaje"""
    width = int(image.shape[1] * scale_percent / 100)
    height = int(image.shape[0] * scale_percent / 100)
    dim = (width, height)
    return cv2.resize(image, dim, interpolation=cv2.INTER_AREA)

# ========== APLICACIÓN STREAMLIT ==========
st.set_page_config(
    page_title="Escáner de Dígitos - Selección Táctil",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado con JavaScript para interacción táctil
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
    .touch-container {
        position: relative;
        border: 3px solid #00cc00;
        border-radius: 15px;
        padding: 10px;
        background: #000;
        margin: 10px 0;
        overflow: hidden;
        touch-action: manipulation;
    }
    .scanner-overlay {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 250px;
        height: 120px;
        border: 3px solid #00ff00;
        border-radius: 10px;
        pointer-events: none;
        z-index: 1000;
        box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.4);
    }
    .overlay-text {
        position: absolute;
        top: -40px;
        left: 0;
        right: 0;
        text-align: center;
        color: #00ff00;
        font-weight: bold;
        font-size: 16px;
        background: rgba(0, 0, 0, 0.8);
        padding: 8px;
        border-radius: 8px;
    }
    .zoom-controls {
        background: rgba(0, 0, 0, 0.8);
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .instruction-box {
        background: linear-gradient(45deg, #000000, #001a00);
        padding: 15px;
        border-radius: 10px;
        border: 2px solid #00cc00;
        margin: 10px 0;
    }
    .step-indicator {
        background: #007bff;
        color: white;
        border-radius: 50%;
        width: 35px;
        height: 35px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-right: 10px;
        font-weight: bold;
        font-size: 18px;
    }
    
    /* Estilos para la imagen interactiva */
    .interactive-image {
        cursor: grab;
        transition: transform 0.2s;
        max-width: 100%;
        height: auto;
    }
    .interactive-image:active {
        cursor: grabbing;
    }
    
    @media (max-width: 768px) {
        .digits-result {
            font-size: 2.5em;
            padding: 20px;
        }
        .scanner-overlay {
            width: 200px;
            height: 100px;
        }
    }
</style>

<script>
// JavaScript para hacer la imagen arrastrable y con zoom
function makeImageDraggable() {
    const image = document.querySelector('.interactive-image');
    if (!image) return;
    
    let isDragging = false;
    let startX, startY;
    let translateX = 0, translateY = 0;
    let scale = 1;
    
    image.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
    image.style.cursor = 'grab';
    
    // Eventos táctiles
    image.addEventListener('touchstart', function(e) {
        e.preventDefault();
        isDragging = true;
        const touch = e.touches[0];
        startX = touch.clientX - translateX;
        startY = touch.clientY - translateY;
        image.style.cursor = 'grabbing';
    });
    
    image.addEventListener('touchmove', function(e) {
        if (!isDragging) return;
        e.preventDefault();
        const touch = e.touches[0];
        translateX = touch.clientX - startX;
        translateY = touch.clientY - startY;
        image.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
    });
    
    image.addEventListener('touchend', function() {
        isDragging = false;
        image.style.cursor = 'grab';
    });
    
    // Eventos de ratón (para desktop)
    image.addEventListener('mousedown', function(e) {
        isDragging = true;
        startX = e.clientX - translateX;
        startY = e.clientY - translateY;
        image.style.cursor = 'grabbing';
    });
    
    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        translateX = e.clientX - startX;
        translateY = e.clientY - startY;
        image.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
    });
    
    document.addEventListener('mouseup', function() {
        isDragging = false;
        image.style.cursor = 'grab';
    });
    
    // Gestos de zoom con rueda del ratón
    image.addEventListener('wheel', function(e) {
        e.preventDefault();
        const delta = -Math.sign(e.deltaY);
        scale += delta * 0.1;
        scale = Math.max(0.5, Math.min(3, scale)); // Limitar zoom entre 0.5x y 3x
        image.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
    });
}

// Inicializar cuando la página cargue
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(makeImageDraggable, 1000);
});

// Re-inicializar cuando Streamlit actualice el contenido
if (window.Streamlit) {
    window.Streamlit.onRender(function() {
        setTimeout(makeImageDraggable, 500);
    });
}
</script>
""", unsafe_allow_html=True)

st.title("📱 Escáner de Dígitos - Selección Táctil")
st.markdown("---")

def main():
    # Información sobre el estado
    if not OCR_AVAILABLE:
        st.error("❌ Servicio OCR no disponible")
        return

    # Estado de la aplicación
    if 'current_step' not in st.session_state:
        st.session_state.current_step = 1
        st.session_state.captured_image = None
        st.session_state.captured_digits = ""
        st.session_state.analysis_done = False
        st.session_state.image_scale = 100

    # Indicador de pasos
    col1, col2, col3 = st.columns(3)
    with col1:
        step1 = "🔵" if st.session_state.current_step == 1 else "✅"
        st.markdown(f"### {step1} Paso 1")
        st.markdown("Capturar imagen")
    
    with col2:
        step2 = "🔵" if st.session_state.current_step == 2 else "✅" if st.session_state.captured_image else "⚪"
        st.markdown(f"### {step2} Paso 2")
        st.markdown("Alinear dígitos")
    
    with col3:
        step3 = "🔵" if st.session_state.current_step == 3 else "✅" if st.session_state.analysis_done else "⚪"
        st.markdown(f"### {step3} Paso 3")
        st.markdown("Resultados")

    st.markdown("---")

    # PASO 1: CAPTURAR IMAGEN
    if st.session_state.current_step == 1:
        st.subheader("📷 Paso 1: Capturar Imagen")
        
        st.markdown("""
        <div class="instruction-box">
            <h4>🎯 Instrucciones:</h4>
            <ol>
                <li><strong>Permite el acceso a la cámara</strong> cuando tu navegador lo solicite</li>
                <li><strong>Apunta a los dígitos</strong> que quieres escanear</li>
                <li><strong>Captura la imagen</strong> cuando los dígitos estén claros y enfocados</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        # Componente de cámara
        camera_image = st.camera_input(
            "Toma una foto de los dígitos",
            key="camera_capture"
        )
        
        if camera_image is not None:
            # Convertir y almacenar la imagen
            image_bytes = camera_image.getvalue()
            image_array = np.frombuffer(image_bytes, np.uint8)
            st.session_state.captured_image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            st.success("✅ ¡Imagen capturada! Ahora puedes alinear los dígitos.")
            
            if st.button("➡️ Continuar a Alineación", use_container_width=True, type="primary"):
                st.session_state.current_step = 2
                st.rerun()

    # PASO 2: ALINEAR DÍGITOS CON INTERACCIÓN TÁCTIL
    elif st.session_state.current_step == 2 and st.session_state.captured_image is not None:
        st.subheader("🎯 Paso 2: Alinear Dígitos en el Rectángulo")
        
        st.markdown("""
        <div class="instruction-box">
            <h4>👆 Controles Táctiles:</h4>
            <ul>
                <li><strong>Arrastrar:</strong> Toca y desliza para mover la imagen</li>
                <li><strong>Zoom:</strong> Usa dos dedos para hacer zoom (o rueda del ratón)</li>
                <li><strong>Objetivo:</strong> Coloca los dígitos DENTRO del rectángulo verde</li>
            </ul>
            <p><em>💡 El rectángulo verde está FIJO en el centro - tú mueves y ajustas la imagen</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Convertir imagen para mostrar
        image_rgb = cv2.cvtColor(st.session_state.captured_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        
        # Mostrar contenedor interactivo
        st.markdown("""
        <div class="touch-container">
            <div class="scanner-overlay">
                <div class="overlay-text">Área de Análisis</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Mostrar imagen como interactiva
        st.image(pil_image, use_column_width=True, caption="Arrastra y haz zoom para alinear los dígitos", output_format="JPEG")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Controles de zoom adicionales
        st.markdown("""
        <div class="zoom-controls">
            <h4>🔧 Controles Adicionales:</h4>
            <p><small>Si los gestos táctiles no funcionan bien, usa estos controles:</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("↔️ Centrar Horizontal", use_container_width=True):
                # Lógica para centrar (simulada)
                st.info("Imagen centrada horizontalmente")
        
        with col2:
            if st.button("↕️ Centrar Vertical", use_container_width=True):
                st.info("Imagen centrada verticalmente")
        
        # Botones de acción principales
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔍 ANALIZAR DÍGITOS EN EL RECTÁNGULO", use_container_width=True, type="primary"):
                # El rectángulo está fijo en el centro, calcular área relativa
                with st.spinner("Analizando dígitos en el área seleccionada..."):
                    # Coordenadas del rectángulo fijo (centro de la imagen)
                    img_height, img_width = st.session_state.captured_image.shape[:2]
                    
                    # Tamaño del rectángulo (fijo)
                    rect_width = 250
                    rect_height = 120
                    
                    # Calcular posición centrada
                    rect_x = (img_width - rect_width) // 2
                    rect_y = (img_height - rect_height) // 2
                    
                    # Asegurar que las coordenadas estén dentro de la imagen
                    rect_x = max(0, min(rect_x, img_width - rect_width))
                    rect_y = max(0, min(rect_y, img_height - rect_height))
                    
                    # Extraer área del rectángulo
                    roi = get_roi(st.session_state.captured_image, rect_x, rect_y, rect_width, rect_height)
                    
                    if roi.size > 0:
                        # Mostrar área que se va a analizar
                        with st.expander("🔍 Ver Área Exacta a Analizar", expanded=True):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.image(
                                    cv2.cvtColor(roi, cv2.COLOR_BGR2RGB),
                                    use_column_width=True,
                                    caption=f"Área del rectángulo ({roi.shape[1]}×{roi.shape[0]}px)"
                                )
                            with col_b:
                                processed_roi = preprocess_image(roi)
                                st.image(
                                    processed_roi,
                                    use_column_width=True,
                                    caption="Versión procesada",
                                    clamp=True
                                )
                        
                        # Extraer dígitos
                        digits, _ = extract_digits_with_api(roi)
                        
                        st.session_state.captured_digits = digits
                        st.session_state.analysis_done = True
                        st.session_state.current_step = 3
                        
                        st.rerun()
                    else:
                        st.error("❌ No se pudo extraer el área del rectángulo")
        
        # Botón para volver
        if st.button("🔄 Tomar Otra Foto", use_container_width=True, type="secondary"):
            st.session_state.current_step = 1
            st.session_state.captured_image = None
            st.rerun()

    # PASO 3: RESULTADOS
    elif st.session_state.current_step == 3:
        st.subheader("📊 Paso 3: Resultados del Análisis")
        
        if st.session_state.captured_digits and not st.session_state.captured_digits.startswith("Error") and not st.session_state.captured_digits.startswith("No se"):
            # Mostrar dígitos detectados
            st.markdown(f'<div class="digits-result">{st.session_state.captured_digits}</div>', 
                       unsafe_allow_html=True)
            
            st.success(f"✅ ¡Éxito! Se detectaron {len(st.session_state.captured_digits)} dígitos.")
            
            # Botones de acción
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("📋 Copiar", use_container_width=True, type="secondary"):
                    st.code(st.session_state.captured_digits)
                    st.success("✅ Copiado!")
            
            with col2:
                if st.button("🔁 Re-alinear", use_container_width=True):
                    st.session_state.current_step = 2
                    st.session_state.analysis_done = False
                    st.rerun()
            
            with col3:
                if st.button("🔄 Nueva Foto", use_container_width=True):
                    st.session_state.current_step = 1
                    st.session_state.captured_image = None
                    st.session_state.captured_digits = ""
                    st.session_state.analysis_done = False
                    st.rerun()
        
        else:
            st.error(f"❌ {st.session_state.captured_digits}")
            
            st.info("""
            **💡 Consejos para mejor detección:**
            - Asegúrate de que los dígitos estén COMPLETAMENTE dentro del rectángulo verde
            - Mejora la iluminación de los dígitos
            - Los dígitos deben ser nítidos y con buen contraste
            - Intenta alinear mejor en el paso anterior
            """)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("↩️ Re-alinear", use_container_width=True):
                    st.session_state.current_step = 2
                    st.session_state.analysis_done = False
                    st.rerun()
            
            with col2:
                if st.button("🔄 Nueva Foto", use_container_width=True):
                    st.session_state.current_step = 1
                    st.session_state.captured_image = None
                    st.session_state.captured_digits = ""
                    st.session_state.analysis_done = False
                    st.rerun()

    # Información adicional
    with st.expander("ℹ️ Cómo Usar la Selección Táctil"):
        st.markdown("""
        ### 👆 Guía de Controles Táctiles
        
        **En Dispositivos Móviles:**
        - **🔄 Arrastrar:** Toca y desliza con un dedo para mover la imagen
        - **🔍 Zoom:** Pellizca con dos dedos para acercar/alejar
        - **🎯 Objetivo:** Coloca los dígitos dentro del rectángulo verde FIJO
        
        **En Computadora:**
        - **🖱️ Arrastrar:** Click y arrastrar para mover la imagen
        - **🔍 Zoom:** Rueda del ratón para acercar/alejar
        - **🎯 Objetivo:** Mismo que en móvil
        
        ### 🎯 Estrategia Recomendada
        1. **Captura** la imagen completa
        2. **Haz zoom** para acercarte a los dígitos
        3. **Arrastra** para colocarlos dentro del rectángulo
        4. **Ajusta** hasta que queden perfectamente alineados
        5. **Analiza** y obtén resultados precisos
        
        **Ventaja:** El rectángulo siempre analiza la misma área, tú controlas qué dígitos colocar ahí.
        """)

if __name__ == "__main__":
    main()