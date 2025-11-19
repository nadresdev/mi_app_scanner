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
        
        st.success("✅ OCR configurado usando API online")
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
        with st.spinner("🔍 Enviando imagen a OCR..."):
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
    page_title="Escáner de Dígitos - Selección Interactiva",
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
    .success-box {
        background-color: #e8f5e8;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
    }
    .selection-info {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #ffc107;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔢 Escáner de Dígitos - Selección Interactiva")
st.markdown("---")

def main():
    # Información sobre el estado
    if not OCR_AVAILABLE:
        st.error("❌ Servicio OCR no disponible")
        return
    else:
        st.success("✅ Servicio OCR online listo!")

    # Estado de la aplicación
    if 'uploaded_image' not in st.session_state:
        st.session_state.uploaded_image = None
        st.session_state.captured_digits = ""
        st.session_state.selection_made = False
        st.session_state.selection_coords = {'x': 0, 'y': 0, 'width': 200, 'height': 100}
        st.session_state.processed_roi = None

    # Sidebar
    st.sidebar.title("⚙️ Configuración")
    
    # Paso 1: Subir imagen
    st.sidebar.subheader("📤 Paso 1: Subir Imagen")
    uploaded_file = st.sidebar.file_uploader(
        "Selecciona una imagen con dígitos",
        type=['png', 'jpg', 'jpeg'],
        key="file_uploader"
    )
    
    if uploaded_file is not None:
        # Leer y almacenar la imagen
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        st.session_state.uploaded_image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        st.session_state.selection_made = False
        st.session_state.captured_digits = ""

    # Mostrar imagen subida
    if st.session_state.uploaded_image is not None:
        # Paso 2: Configurar área de selección
        st.sidebar.subheader("🎯 Paso 2: Configurar Área de Análisis")
        
        # Obtener dimensiones de la imagen
        img_height, img_width = st.session_state.uploaded_image.shape[:2]
        
        # Controles para el área de selección
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            x = st.slider("Posición X", 0, img_width - 50, 100, 10, 
                         key="x_slider")
            width = st.slider("Ancho", 50, img_width - x, 300, 10,
                             key="width_slider")
        
        with col2:
            y = st.slider("Posición Y", 0, img_height - 50, 100, 10,
                         key="y_slider")
            height = st.slider("Alto", 50, img_height - y, 150, 10,
                              key="height_slider")
        
        # Actualizar coordenadas
        st.session_state.selection_coords = {
            'x': x, 'y': y, 'width': width, 'height': height
        }
        
        # Mostrar información del área seleccionada
        st.sidebar.markdown(f"""
        <div class="selection-info">
            <strong>Área Seleccionada:</strong><br>
            • Posición: ({x}, {y})<br>
            • Tamaño: {width} × {height} px<br>
            • Área: {width * height} px²
        </div>
        """, unsafe_allow_html=True)
        
        # Botón para analizar
        st.sidebar.subheader("🔍 Paso 3: Analizar")
        if st.sidebar.button("🚀 Analizar Área Seleccionada", use_container_width=True, type="primary"):
            # Extraer ROI basado en la selección actual
            roi = get_roi(
                st.session_state.uploaded_image,
                st.session_state.selection_coords['x'],
                st.session_state.selection_coords['y'],
                st.session_state.selection_coords['width'],
                st.session_state.selection_coords['height']
            )
            
            if roi.size > 0:
                # Preprocesar imagen
                st.session_state.processed_roi = preprocess_image(roi)
                
                # Extraer dígitos usando API
                digits, _ = extract_digits_with_api(roi)
                
                st.session_state.captured_digits = digits
                st.session_state.selection_made = True
                
                if digits and not digits.startswith("Error") and not digits.startswith("No se"):
                    st.sidebar.success(f"✅ Dígitos detectados: {digits}")
                else:
                    st.sidebar.warning(f"⚠️ {digits}")
            else:
                st.sidebar.error("❌ El área seleccionada no es válida")

    # Área principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🖼️ Vista Previa de la Imagen")
        
        if st.session_state.uploaded_image is not None:
            # Dibujar rectángulo en la imagen
            image_with_rect = draw_scanner_zone(
                st.session_state.uploaded_image,
                st.session_state.selection_coords['x'],
                st.session_state.selection_coords['y'],
                st.session_state.selection_coords['width'],
                st.session_state.selection_coords['height']
            )
            
            # Mostrar imagen con el rectángulo
            st.image(
                cv2.cvtColor(image_with_rect, cv2.COLOR_BGR2RGB),
                use_column_width=True,
                caption=f"Área seleccionada para análisis - Ajusta los controles en la barra lateral"
            )
            
            # Mostrar área procesada si está disponible
            if st.session_state.processed_roi is not None:
                with st.expander("🔍 Ver Área Seleccionada (Procesada)"):
                    st.image(
                        st.session_state.processed_roi,
                        use_column_width=True,
                        caption="Esta es el área que se enviará al OCR",
                        clamp=True
                    )
        else:
            st.info("""
            <div class="info-box">
                <h3>👆 Para comenzar:</h3>
                <ol>
                    <li><strong>Sube una imagen</strong> en la barra lateral</li>
                    <li><strong>Ajusta el área de análisis</strong> con los controles deslizantes</li>
                    <li><strong>Haz clic en "Analizar Área Seleccionada"</strong></li>
                    <li><strong>Revisa los resultados</strong> en el panel derecho</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("📊 Resultados del Análisis")
        
        if st.session_state.captured_digits and not st.session_state.captured_digits.startswith("Error") and not st.session_state.captured_digits.startswith("No se"):
            st.markdown(f'<div class="digits-result">{st.session_state.captured_digits}</div>', 
                       unsafe_allow_html=True)
            
            # Botones de acción
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("📋 Copiar Resultados", use_container_width=True):
                    st.code(st.session_state.captured_digits)
                    st.success("✅ Resultados copiados!")
            with col_btn2:
                if st.button("🔄 Nueva Selección", use_container_width=True):
                    st.session_state.captured_digits = ""
                    st.session_state.processed_roi = None
                    st.session_state.selection_made = False
                    st.rerun()
            
            # Consejos para mejor detección
            with st.expander("💡 Consejos para mejor precisión"):
                st.markdown("""
                - **Ajusta el área** para que cubra solo los dígitos
                - **Evita incluir** fondo innecesario
                - **Buena iluminación** en la imagen original
                - **Contraste alto** entre dígitos y fondo
                - **Fuentes claras** y legibles
                """)
        
        elif st.session_state.selection_made:
            st.warning(f"⚠️ {st.session_state.captured_digits}")
            st.markdown("""
            **Sugerencias:**
            - Ajusta el área de selección
            - Verifica que la imagen sea clara
            - Intenta con otra región de la imagen
            """)
        
        else:
            st.info("""
            <div class="info-box">
                <h3>📝 Resultados</h3>
                <p>Los dígitos detectados aparecerán aquí después del análisis.</p>
                
                <p><strong>Características:</strong></p>
                <ul>
                    <li>✅ Selección interactiva del área</li>
                    <li>✅ Ajuste en tiempo real</li>
                    <li>✅ Procesamiento con OCR profesional</li>
                    <li>✅ Copia fácil de resultados</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    
    # Información adicional
    with st.expander("ℹ️ Instrucciones Detalladas"):
        st.markdown("""
        ### 🎯 Cómo Usar Esta Aplicación
        
        **Paso 1: Subir Imagen**
        - Ve a la barra lateral y selecciona "Selecciona una imagen con dígitos"
        - Sube cualquier imagen en formato JPG, PNG o JPEG
        - La imagen se mostrará inmediatamente en el área principal
        
        **Paso 2: Seleccionar Área de Análisis**
        - Usa los controles deslizantes en la barra lateral para ajustar:
          - **Posición X/Y**: Mueve el rectángulo verde
          - **Ancho/Alto**: Cambia el tamaño del área
        - El rectángulo verde se actualiza en tiempo real
        
        **Paso 3: Analizar**
        - Haz clic en "Analizar Área Seleccionada"
        - La aplicación enviará solo el área seleccionada al OCR
        - Los resultados aparecerán en el panel derecho
        
        **Paso 4: Refinar (Opcional)**
        - Si no detecta bien, ajusta el área y vuelve a analizar
        - Puedes copiar los resultados con el botón correspondiente
        
        ### 🚀 Características Técnicas
        - **OCR Online**: Usa API profesional para mejor precisión
        - **Selección Interactiva**: Elige exactamente qué área analizar
        - **Tiempo Real**: Los cambios se ven inmediatamente
        - **Sin Instalación**: Funciona completamente en la nube
        """)

if __name__ == "__main__":
    main()