#!/bin/bash

echo "🚀 Script de Despliegue para App OCR PDF"
echo "=========================================="
echo ""

# Verificar si git está instalado
if ! command -v git &> /dev/null; then
    echo "❌ Git no está instalado. Por favor instala Git primero."
    exit 1
fi

# Inicializar repositorio Git si no existe
if [ ! -d .git ]; then
    echo "📦 Inicializando repositorio Git..."
    git init
    git add .
    git commit -m "Initial commit: PDF OCR App"
fi

echo "Selecciona la plataforma de despliegue:"
echo "1) Render.com (Recomendado - Gratuito y fácil)"
echo "2) Railway.app (Gratuito con límites generosos)"
echo "3) Heroku (Requiere configuración adicional)"
echo "4) Crear archivo ZIP para despliegue manual"
echo ""
read -p "Opción (1-4): " option

case $option in
    1)
        echo ""
        echo "📌 INSTRUCCIONES PARA RENDER.COM:"
        echo "=================================="
        echo "1. Ve a https://render.com y crea una cuenta gratuita"
        echo "2. Haz clic en 'New +' → 'Web Service'"
        echo "3. Conecta tu repositorio de GitHub o GitLab"
        echo "   (Necesitarás subir este código a GitHub primero)"
        echo "4. Configura:"
        echo "   - Name: pdf-ocr-app (o el nombre que prefieras)"
        echo "   - Environment: Python 3"
        echo "   - Build Command: pip install -r requirements.txt"
        echo "   - Start Command: gunicorn app:app"
        echo "5. En la sección 'Advanced', añade Build Packages:"
        echo "   - tesseract-ocr"
        echo "   - tesseract-ocr-spa"
        echo "   - tesseract-ocr-eng"  
        echo "   - poppler-utils"
        echo "6. Haz clic en 'Create Web Service'"
        echo ""
        echo "Tu app estará disponible en: https://pdf-ocr-app.onrender.com"
        ;;
    2)
        echo ""
        echo "📌 INSTRUCCIONES PARA RAILWAY.APP:"
        echo "=================================="
        echo "1. Ve a https://railway.app y crea una cuenta"
        echo "2. Haz clic en 'New Project' → 'Deploy from GitHub repo'"
        echo "3. Selecciona este repositorio"
        echo "4. Railway detectará automáticamente Python"
        echo "5. Añade las siguientes variables de entorno si es necesario:"
        echo "   TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata"
        echo "6. Despliega y espera a que termine"
        echo ""
        echo "Tu app estará disponible en la URL que Railway te proporcione"
        ;;
    3)
        echo ""
        echo "📌 INSTRUCCIONES PARA HEROKU:"
        echo "============================="
        echo "1. Instala Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli"
        echo "2. Ejecuta los siguientes comandos:"
        echo ""
        echo "   heroku login"
        echo "   heroku create tu-app-ocr-pdf"
        echo "   heroku buildpacks:add --index 1 https://github.com/heroku/heroku-buildpack-apt"
        echo "   heroku buildpacks:add --index 2 heroku/python"
        echo "   git push heroku main"
        echo ""
        echo "Tu app estará disponible en: https://tu-app-ocr-pdf.herokuapp.com"
        ;;
    4)
        echo ""
        echo "📦 Creando archivo ZIP..."
        cd ..
        zip -r pdf-ocr-app.zip pdf-ocr-app -x "*.git*" "*__pycache__*" "*.pyc"
        echo "✅ Archivo creado: pdf-ocr-app.zip"
        echo ""
        echo "Puedes subir este ZIP a cualquier plataforma que soporte Python y Flask"
        ;;
    *)
        echo "❌ Opción no válida"
        exit 1
        ;;
esac

echo ""
echo "📚 Documentación adicional en README.md"
echo "✅ ¡Listo!"
