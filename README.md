# 🔍 App de Escaneo OCR de PDF Online

Aplicación web para escanear PDFs y extraer texto de todas las páginas usando tecnología OCR (Reconocimiento Óptico de Caracteres).

## ✨ Características

- 📄 **Procesa todas las páginas**: No deja ninguna página sin escanear
- 🔤 **Soporte multiidioma**: Español e inglés
- 📦 **Nomenclatura automática**: Añade "_OCR" al final del nombre del archivo
- 🚀 **Interfaz moderna**: Drag & drop y barra de progreso
- 🔒 **Privado**: Los archivos se eliminan automáticamente después del proceso
- ⚡ **Gratuito**: Alojado en plataforma gratuita

## 🚀 Despliegue

### Opción 1: Render.com (Recomendado)

1. Crear cuenta en [Render.com](https://render.com)
2. Crear nuevo Web Service
3. Conectar con repositorio Git o subir código
4. Configurar:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Environment**: Python 3
5. Añadir paquetes del sistema en configuración (si está disponible):
   - tesseract-ocr
   - tesseract-ocr-spa
   - tesseract-ocr-eng
   - poppler-utils

### Opción 2: Railway.app

1. Crear cuenta en [Railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Seleccionar repositorio
4. Railway detectará automáticamente Python
5. Añadir Nixpacks para dependencias del sistema

### Opción 3: Heroku (con buildpacks)

```bash
heroku create nombre-de-tu-app
heroku buildpacks:add --index 1 https://github.com/heroku/heroku-buildpack-apt
heroku buildpacks:add --index 2 heroku/python
git push heroku main
```

## 🛠️ Instalación Local

```bash
# Instalar dependencias del sistema (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng poppler-utils

# Instalar dependencias de Python
pip install -r requirements.txt

# Ejecutar aplicación
python app.py
```

Accede a: http://localhost:5000

## 📖 Uso

1. Abre la aplicación en tu navegador
2. Haz clic o arrastra un archivo PDF
3. Presiona "Escanear PDF"
4. Espera a que se procese (verás el progreso)
5. El archivo se descargará automáticamente con el sufijo "_OCR"

**Ejemplo**: `documento.pdf` → `documento_OCR.pdf`

## ⚙️ Tecnologías

- **Backend**: Flask (Python)
- **OCR**: Tesseract
- **Procesamiento PDF**: pdf2image, ReportLab
- **Frontend**: HTML5, CSS3, JavaScript vanilla

## 📝 Limitaciones

- Tamaño máximo de archivo: 50 MB
- Solo archivos PDF
- El tiempo de procesamiento depende del número de páginas y calidad del escaneo

## 🔐 Privacidad

- Los archivos se almacenan temporalmente solo durante el procesamiento
- Se eliminan automáticamente después de la descarga
- No se guarda ningún dato del usuario

## 📄 Licencia

MIT License - Uso libre
