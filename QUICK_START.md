# 🚀 INICIO RÁPIDO

## Para usuarios que quieren desplegar YA

### Opción 1: Render.com (3 minutos) ⭐ RECOMENDADO

1. **Descarga este proyecto** (ya lo tienes en el ZIP)

2. **Sube a GitHub:**
   - Crea un nuevo repositorio en GitHub (https://github.com/new)
   - Descomprime el ZIP
   - Ejecuta:
     ```bash
     cd pdf-ocr-app
     git init
     git add .
     git commit -m "Initial commit"
     git branch -M main
     git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
     git push -u origin main
     ```

3. **Despliega en Render:**
   - Ve a https://render.com/register
   - Click "New +" → "Web Service"
   - Conecta GitHub → Selecciona tu repositorio
   - Render detectará automáticamente `render.yaml`
   - Click "Apply" → "Create Web Service"
   - ☕ Espera 5-10 minutos

4. **¡Listo!** Tu app estará en: `https://tu-app.onrender.com`

---

### Opción 2: Railway.app (2 minutos) ⚡

1. **Sube a GitHub** (mismo proceso anterior)

2. **Deploy en Railway:**
   - Ve a https://railway.app
   - Login con GitHub
   - "New Project" → "Deploy from GitHub repo"
   - Selecciona tu repositorio
   - Railway auto-detecta `nixpacks.toml`
   - ☕ Espera 3-5 minutos

3. **Configura dominio:**
   - En el dashboard → Settings → Generate Domain
   - Tu app estará en: `https://tu-app.up.railway.app`

---

## URLs después del despliegue

Tu aplicación estará accesible desde cualquier dispositivo en:

- **Render**: `https://tu-app-nombre.onrender.com`
- **Railway**: `https://tu-app-nombre.up.railway.app`

## ¿Cómo usar la app?

1. Abre la URL en cualquier navegador
2. Arrastra o selecciona un PDF
3. Click en "Escanear PDF"
4. Descarga tu archivo con sufijo `_OCR`

## Ejemplo de uso

**Archivo de entrada:** `factura_mayo.pdf`  
**Archivo de salida:** `factura_mayo_OCR.pdf` ✅

---

## 🆘 ¿Problemas?

### "Build failed" en Render/Railway
- Verifica que todos los archivos estén en el repositorio
- Revisa los logs de build

### "Application error"
- Espera 1-2 minutos, los servicios gratuitos tardan en iniciar
- Verifica logs en el dashboard de la plataforma

### "Tesseract not found"
- Asegúrate de que `render.yaml` o `nixpacks.toml` estén en la raíz
- Verifica que los buildpacks de sistema estén configurados

---

## 📞 Necesitas ayuda?

Lee la guía completa en: `DEPLOYMENT_GUIDE.md`

---

## ✅ Checklist

- [ ] Código descargado y descomprimido
- [ ] Repositorio creado en GitHub
- [ ] Código subido a GitHub (`git push`)
- [ ] Cuenta creada en Render o Railway
- [ ] Repositorio conectado a la plataforma
- [ ] Deploy iniciado
- [ ] Esperado 5-10 minutos
- [ ] URL funcionando
- [ ] Probado con un PDF

🎉 **¡Disfruta tu app de OCR gratuita!**
