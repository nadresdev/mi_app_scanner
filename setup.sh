#!/bin/bash

# Instalar Tesseract OCR en Streamlit Cloud
sudo apt-get update
sudo apt-get install -y tesseract-ocr

# Verificar instalación
tesseract --version

echo "✅ Tesseract instalado correctamente"