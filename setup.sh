#!/bin/bash

# Instalar Tesseract OCR y lenguajes en Streamlit Cloud
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-spa

# Verificar instalación
echo "=== Verificando instalación de Tesseract ==="
tesseract --version

# Verificar que pytesseract pueda encontrar tesseract
echo "=== Verificando rutas ==="
which tesseract

echo "✅ Tesseract instalado correctamente "