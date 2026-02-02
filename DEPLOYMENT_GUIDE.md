# 🚀 GUÍA DE DESPLIEGUE COMPLETA

## Opción 1: Render.com (⭐ RECOMENDADO - Más fácil)

### ✅ Ventajas:
- Completamente gratuito
- Fácil de configurar
- Soporta dependencias del sistema (Tesseract, Poppler)
- SSL automático

### 📋 Pasos:

1. **Sube tu código a GitHub:**
   ```bash
   # Crear repositorio en GitHub primero, luego:
   git init
   git add .
   git commit -m "App OCR PDF"
   git remote add origin https://github.com/TU_USUARIO/pdf-ocr-app.git
   git push -u origin main
   ```

2. **Despliega en Render:**
   - Ve a [https://render.com](https://render.com)
   - Crea cuenta gratuita
   - Click en "New +" → "Web Service"
   - Conecta tu repositorio de GitHub
   - Configura:
     * **Name**: `pdf-ocr-app` (o tu nombre preferido)
     * **Environment**: `Python 3`
     * **Build Command**: `pip install -r requirements.txt`
     * **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
   
3. **Añadir Paquetes del Sistema:**
   - En la sección "Environment", añade estas variables:
     ```
     PYTHON_VERSION=3.11.6
     ```
   - Crea un archivo `render.yaml` en la raíz:
     ```yaml
     services:
       - type: web
         name: pdf-ocr-app
         env: python
         buildCommand: |
           apt-get update
           apt-get install -y tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng poppler-utils
           pip install -r requirements.txt
         startCommand: gunicorn app:app
         plan: free
     ```

4. **Despliega:**
   - Click en "Create Web Service"
   - Espera 5-10 minutos
   - ¡Tu app estará en: `https://pdf-ocr-app.onrender.com`!

---

## Opción 2: Railway.app (⚡ Muy rápido)

### ✅ Ventajas:
- Deploy super rápido
- $5 USD gratis al mes
- Auto-detección de dependencias

### 📋 Pasos:

1. **Sube a GitHub** (mismo proceso que Render)

2. **Despliega en Railway:**
   - Ve a [https://railway.app](https://railway.app)
   - Login con GitHub
   - "New Project" → "Deploy from GitHub repo"
   - Selecciona tu repositorio
   - Railway auto-detecta Python

3. **Configura Nixpacks:**
   - Crea archivo `nixpacks.toml` en la raíz:
     ```toml
     [phases.setup]
     aptPkgs = ["tesseract-ocr", "tesseract-ocr-spa", "tesseract-ocr-eng", "poppler-utils"]
     
     [phases.install]
     cmds = ["pip install -r requirements.txt"]
     
     [start]
     cmd = "gunicorn app:app --bind 0.0.0.0:$PORT"
     ```

4. **Variables de entorno:**
   - En el dashboard, añade:
     ```
     PORT=8080
     TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
     ```

5. **Deploy:**
   - Railway desplegará automáticamente
   - Te dará una URL tipo: `https://pdf-ocr-app.up.railway.app`

---

## Opción 3: Heroku (🔧 Requiere más configuración)

### ⚠️ Nota: Heroku ya no ofrece plan gratuito, pero incluyo las instrucciones

### 📋 Pasos:

1. **Instala Heroku CLI:**
   ```bash
   # macOS
   brew tap heroku/brew && brew install heroku
   
   # Ubuntu/Debian
   curl https://cli-assets.heroku.com/install.sh | sh
   ```

2. **Deploy:**
   ```bash
   heroku login
   heroku create tu-app-ocr-pdf
   
   # Añadir buildpack para apt
   heroku buildpacks:add --index 1 https://github.com/heroku/heroku-buildpack-apt
   heroku buildpacks:add --index 2 heroku/python
   
   git push heroku main
   heroku open
   ```

3. **Tu app estará en:** `https://tu-app-ocr-pdf.herokuapp.com`

---

## Opción 4: Vercel (Limitado - No recomendado para OCR)

⚠️ **No recomendado**: Vercel tiene límites de tiempo de ejecución (10s max) que no son suficientes para OCR de PDFs grandes.

---

## Opción 5: VPS Gratuito (Oracle Cloud Free Tier)

Si quieres más control y capacidad:

1. **Crea cuenta en Oracle Cloud** (siempre gratis)
2. **Crea VM gratuita** (Ampere ARM o x86)
3. **Instala dependencias:**
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng poppler-utils
   ```
4. **Sube tu código y ejecuta:**
   ```bash
   pip3 install -r requirements.txt
   gunicorn app:app --bind 0.0.0.0:80
   ```

---

## 🧪 Probar Localmente Primero

Antes de desplegar, prueba localmente:

```bash
# Instalar dependencias del sistema (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng poppler-utils

# Instalar dependencias Python
pip install -r requirements.txt

# Ejecutar
python app.py
```

Abre: http://localhost:5000

---

## 📊 Comparación de Plataformas

| Plataforma | Precio | Facilidad | Tiempo OCR | SSL | Recomendación |
|------------|--------|-----------|------------|-----|---------------|
| **Render.com** | Gratis | ⭐⭐⭐⭐⭐ | ✅ Sin límite | ✅ Auto | **✅ MEJOR** |
| **Railway.app** | $5 gratis/mes | ⭐⭐⭐⭐ | ✅ Sin límite | ✅ Auto | ✅ Muy bueno |
| **Heroku** | $7/mes | ⭐⭐⭐ | ✅ Sin límite | ✅ Auto | ⚠️ De pago |
| **Vercel** | Gratis | ⭐⭐⭐⭐⭐ | ❌ 10s límite | ✅ Auto | ❌ No para OCR |
| **Oracle Cloud** | Gratis | ⭐⭐ | ✅ Sin límite | ⚙️ Manual | ✅ Para avanzados |

---

## 🆘 Solución de Problemas

### Error: "Tesseract not found"
Asegúrate de que la plataforma tenga instalado `tesseract-ocr` en los buildpacks/packages del sistema.

### Error: "pdf2image failed"
Instala `poppler-utils` en los packages del sistema.

### Timeout en el procesamiento
Aumenta el timeout del servidor o divide PDFs grandes en archivos más pequeños.

### "Module not found"
Verifica que todas las dependencias estén en `requirements.txt`.

---

## 📞 Soporte

Si tienes problemas, verifica:
1. Logs de la plataforma (Render/Railway tienen logs en tiempo real)
2. Que todas las dependencias del sistema estén instaladas
3. Que el puerto esté correctamente configurado (`$PORT`)

---

## ✅ Checklist Final

- [ ] Código subido a GitHub
- [ ] Cuenta creada en la plataforma elegida
- [ ] Repositorio conectado
- [ ] Build command configurado
- [ ] Start command configurado
- [ ] Dependencias del sistema añadidas
- [ ] Deploy iniciado
- [ ] URL funcionando
- [ ] Prueba con un PDF de ejemplo

¡Éxito! 🎉
