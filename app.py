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
            'K89947096688957'  # Clave de ejemplo (puede tener límites)
        ]
        
        st.success("✅ OCR configurado usando API online")
        return True, API_KEYS[0]
    except Exception as e:
        st.error(f"❌ Error configurando OCR: {e}")
        return False, None

OCR_AVAILABLE, API_KEY = setup_ocr()

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
    page_title="Escáner de Dígitos con OCR Online",
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
</style>
""", unsafe_allow_html=True)

st.title("🔢 Escáner de Dígitos con OCR Online")
st.markdown("---")

def main():
    # Información sobre el estado
    if not OCR_AVAILABLE:
        st.error("❌ Servicio OCR no disponible")
        return
    else:
        st.success("✅ Servicio OCR online listo!")

    # Sidebar
    st.sidebar.title("⚙️ Configuración")
    
    # Configuración área de escaneo
    st.sidebar.subheader("Área de Escaneo")
    rect_x = st.sidebar.slider("Posición X", 50, 600, 150, 10)
    rect_y = st.sidebar.slider("Posición Y", 50, 400, 150, 10)
    rect_width = st.sidebar.slider("Ancho", 200, 500, 300, 10)
    rect_height = st.sidebar.slider("Alto", 80, 300, 120, 10)
    
    # Estado de la aplicación
    if 'captured_digits' not in st.session_state:
        st.session_state.captured_digits = ""
        st.session_state.captured_image = None
    
    # Área principal
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
        if st.button("🔍 Escanear Dígitos con OCR Online", type="primary", use_container_width=True):
            # Extraer ROI
            roi = get_roi(image, rect_x, rect_y, rect_width, rect_height)
            
            if roi.size > 0:
                # Preprocesar imagen
                processed_roi = preprocess_image(roi)
                
                # Mostrar imagen procesada
                with st.expander("🖼️ Ver área de escaneo (procesada)"):
                    st.image(processed_roi, 
                            use_column_width=True,
                            caption="Área que se enviará al OCR",
                            clamp=True)
                
                # Extraer dígitos usando API
                digits, _ = extract_digits_with_api(roi)
                
                st.session_state.captured_digits = digits
                st.session_state.captured_image = roi
                
                if digits and not digits.startswith("Error") and not digits.startswith("No se"):
                    st.success(f"✅ Dígitos detectados: **{digits}**")
                    st.balloons()
                else:
                    st.warning(f"⚠️ {digits}")
                    st.markdown("""
                    **💡 Consejos para mejor detección:**
                    - Asegúrate de que los dígitos estén dentro del rectángulo verde
                    - Usa imágenes con buen contraste
                    - Dígitos oscuros sobre fondo claro funcionan mejor
                    - Evita imágenes borrosas o con mucho ruido
                    """)
            else:
                st.error("❌ El área de escaneo está fuera de los límites de la imagen")
    
    # Mostrar resultados
    st.markdown("---")
    st.subheader("📊 Resultados")
    
    if st.session_state.captured_digits and not st.session_state.captured_digits.startswith("Error") and not st.session_state.captured_digits.startswith("No se"):
        st.markdown(f'<div class="digits-result">{st.session_state.captured_digits}</div>', 
                   unsafe_allow_html=True)
        
        # Botones de acción
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Copiar Resultados", use_container_width=True):
                st.code(st.session_state.captured_digits)
                st.success("✅ Resultados copiados!")
        with col2:
            if st.button("🔄 Nueva Imagen", use_container_width=True):
                st.session_state.captured_digits = ""
                st.session_state.captured_image = None
                st.rerun()
    
    else:
        st.info("""
        <div class="info-box">
            <h3>👆 Cómo usar esta aplicación:</h3>
            <ol>
                <li><strong>Sube una imagen</strong> que contenga dígitos</li>
                <li><strong>Ajusta el área de escaneo</strong> en la barra lateral</li>
                <li><strong>Haz clic en "Escanear Dígitos"</strong> para procesar con OCR online</li>
                <li><strong>Copia los resultados</strong> detectados</li>
            </ol>
            
            <p><strong>🎯 Características:</strong></p>
            <ul>
                <li>✅ No requiere instalación de Tesseract</li>
                <li>✅ Funciona inmediatamente en Streamlit Cloud</li>
                <li>✅ Procesamiento con API OCR profesional</li>
                <li>✅ Interfaz simple y rápida</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Información técnica
    with st.expander("ℹ️ Información Técnica"):
        st.markdown("""
        **Tecnologías utilizadas:**
        - 🚀 **Streamlit** - Interfaz de usuario
        - 📷 **OpenCV** - Procesamiento de imágenes
        - 🌐 **OCR.space API** - Reconocimiento óptico de caracteres
        - 🐍 **Python** - Lógica de la aplicación
        
        **Ventajas de este approach:**
        - ✅ Funciona inmediatamente en Streamlit Cloud
        - ✅ No requiere instalación de dependencias complejas
        - ✅ Usa motores OCR profesionales
        - ✅ Escalable y confiable
        
        **Límites:**
        - ⚠️ API gratuita tiene límites de uso
        - ⚠️ Requiere conexión a internet
        - ⚠️ Puede ser más lento que solución local
        
        **Para uso local:** Puedes cambiar a Tesseract local para mejor rendimiento.
        """)

if __name__ == "__main__":
    main()