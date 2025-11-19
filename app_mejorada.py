import streamlit as st
import cv2
import numpy as np
import os
import time
import sys

# Configuración mejorada
sys.path.append(os.path.dirname(__file__))

try:
    from config.tesseract_config import TESSERACT_AVAILABLE, TESSERACT_PATH
    from utils.camera_utils import initialize_camera, draw_scanner_zone, get_roi, release_camera
    from utils.ocr_utils import extract_digits_advanced, extract_digits_fast, save_captured_image
except ImportError as e:
    st.error(f"❌ Error importando módulos: {e}")
    st.stop()

st.set_page_config(
    page_title="Escáner de Dígitos Mejorado",
    page_icon="🔢",
    layout="wide"
)

st.title("🔢 Escáner de Dígitos - Versión Mejorada")
st.markdown("---")

def main():
    if not TESSERACT_AVAILABLE:
        st.error("Tesseract no disponible")
        return

    # Sidebar mejorado
    st.sidebar.title("⚙️ Configuración Avanzada")
    
    # Configuración de cámara
    camera_index = st.sidebar.selectbox("Cámara:", [0, 1, 2], index=0)
    
    # Área de escaneo con valores por defecto optimizados
    st.sidebar.subheader("Área de Escaneo")
    rect_x = st.sidebar.slider("Posición X", 50, 600, 150, 10)
    rect_y = st.sidebar.slider("Posición Y", 50, 400, 150, 10)
    rect_width = st.sidebar.slider("Ancho", 200, 500, 300, 10)
    rect_height = st.sidebar.slider("Alto", 80, 300, 120, 10)
    
    # Configuración OCR avanzada
    st.sidebar.subheader("Procesamiento OCR")
    processing_mode = st.sidebar.radio(
        "Modo:",
        ["🚀 Velocidad", "🎯 Precisión"],
        index=0,
        help="Velocidad: Procesamiento rápido\nPrecisión: Análisis más detallado"
    )
    
    show_processed = st.sidebar.checkbox("Mostrar imagen procesada", value=False)
    auto_retry = st.sidebar.checkbox("Reintentar automáticamente", value=True)
    
    # Estado de la aplicación
    if 'camera_active' not in st.session_state:
        st.session_state.update({
            'camera_active': False,
            'captured_digits': "",
            'captured_image': None,
            'processed_image': None,
            'trigger_capture': False,
            'confidence': "",
            'attempt_count': 0
        })
    
    # Interfaz principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📷 Vista en Tiempo Real")
        
        # Controles
        col1_1, col1_2 = st.columns(2)
        with col1_1:
            if not st.session_state.camera_active:
                if st.button("🎥 Iniciar Cámara", use_container_width=True, type="primary"):
                    st.session_state.camera_active = True
                    st.rerun()
            else:
                if st.button("⏹️ Detener", use_container_width=True):
                    st.session_state.camera_active = False
                    st.rerun()
        
        with col1_2:
            if st.session_state.camera_active:
                if st.button("📸 Capturar", use_container_width=True, type="secondary"):
                    st.session_state.trigger_capture = True
                    st.session_state.attempt_count = 0
                    st.rerun()
        
        # Video en tiempo real
        if st.session_state.camera_active:
            video_placeholder = st.empty()
            status_placeholder = st.empty()
            
            try:
                cap = initialize_camera(camera_index)
                if not cap.isOpened():
                    st.error("No se pudo acceder a la cámara")
                    st.session_state.camera_active = False
                    st.rerun()
                
                # Mostrar video hasta captura
                while st.session_state.camera_active and not st.session_state.trigger_capture:
                    ret, frame = cap.read()
                    if ret:
                        frame_with_rect = draw_scanner_zone(frame.copy(), rect_x, rect_y, rect_width, rect_height)
                        frame_rgb = cv2.cvtColor(frame_with_rect, cv2.COLOR_BGR2RGB)
                        video_placeholder.image(frame_rgb, use_column_width=True,
                                              caption="Alinea los dígitos en el rectángulo verde")
                    time.sleep(0.03)
                
                # Procesar captura
                if st.session_state.trigger_capture:
                    ret, frame = cap.read()
                    if ret:
                        roi = get_roi(frame, rect_x, rect_y, rect_width, rect_height)
                        if roi.size > 0:
                            with st.spinner("Procesando..."):
                                if processing_mode == "🎯 Precisión":
                                    digits, processed, confidence = extract_digits_advanced(roi)
                                    if digits:
                                        st.session_state.confidence = f" (Confianza: {confidence:.1f}%)"
                                else:
                                    digits, processed = extract_digits_fast(roi)
                                    st.session_state.confidence = ""
                                
                                st.session_state.captured_digits = digits
                                st.session_state.captured_image = roi
                                st.session_state.processed_image = processed
                                
                                if digits:
                                    status_placeholder.success(f"✅ Dígitos: {digits}{st.session_state.confidence}")
                                    st.balloons()
                                else:
                                    status_placeholder.warning("No se detectaron dígitos")
                            
                            # Guardar captura
                            timestamp = int(time.time())
                            save_captured_image(roi, f"temp/capture_{timestamp}.jpg")
                        
                        st.session_state.trigger_capture = False
                
                release_camera(cap)
                
            except Exception as e:
                st.error(f"Error: {e}")
                st.session_state.camera_active = False
    
    with col2:
        st.subheader("📊 Resultados")
        
        if st.session_state.captured_digits:
            st.markdown(f"""
            <div style='
                font-size: 2.5em; 
                font-weight: bold; 
                color: #00cc00; 
                text-align: center; 
                padding: 20px; 
                background: #000; 
                border-radius: 10px; 
                border: 2px solid #00cc00;
                margin: 10px 0;
            '>
                {st.session_state.captured_digits}
            </div>
            """, unsafe_allow_html=True)
            
            if show_processed and st.session_state.processed_image is not None:
                st.image(st.session_state.processed_image, 
                        use_column_width=True,
                        caption="Imagen procesada")
            
            # Botones de acción
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                if st.button("📋 Copiar", use_container_width=True):
                    st.code(st.session_state.captured_digits)
            with col2_2:
                if st.button("🔄 Nueva", use_container_width=True):
                    st.session_state.trigger_capture = False
                    st.rerun()
        
        else:
            st.info("Los dígitos aparecerán aquí después de capturar")

if __name__ == "__main__":
    os.makedirs('temp', exist_ok=True)
    main()