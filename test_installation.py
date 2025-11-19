import streamlit as st
import cv2
import pytesseract
from PIL import Image
import numpy as np
import sys

st.write("Python version:", sys.version)
st.write("OpenCV version:", cv2.__version__)

try:
    # Verificar Tesseract
    pytesseract.get_tesseract_version()
    st.success("✅ Tesseract OCR funciona correctamente")
except Exception as e:
    st.error(f"❌ Error con Tesseract: {e}")

try:
    # Verificar Pillow
    img = Image.new('RGB', (100, 100), color='red')
    st.success("✅ Pillow funciona correctamente")
except Exception as e:
    st.error(f"❌ Error con Pillow: {e}")

try:
    # Verificar OpenCV
    test_array = np.zeros((100, 100, 3), dtype=np.uint8)
    st.success("✅ OpenCV funciona correctamente")
except Exception as e:
    st.error(f"❌ Error con OpenCV: {e}")