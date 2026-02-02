from flask import Flask, request, send_file, render_template, jsonify
import os
from werkzeug.utils import secure_filename
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
import tempfile
import shutil

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['OUTPUT_FOLDER'] = '/tmp/outputs'

# Crear directorios si no existen
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ocr_pdf(input_pdf_path, output_pdf_path):
    """
    Procesa un PDF completo con OCR página por página
    """
    # Convertir PDF a imágenes
    images = convert_from_path(input_pdf_path, dpi=300)
    
    total_pages = len(images)
    
    # Crear PDF de salida
    c = canvas.Canvas(output_pdf_path, pagesize=A4)
    width, height = A4
    
    for page_num, image in enumerate(images, 1):
        print(f"Procesando página {page_num} de {total_pages}")
        
        # Extraer texto con OCR (soporte multiidioma)
        text = pytesseract.image_to_string(image, lang='spa+eng')
        
        # Configurar texto en el canvas
        text_object = c.beginText(40, height - 40)
        text_object.setFont("Helvetica", 10)
        
        # Dividir texto en líneas y añadir al PDF
        lines = text.split('\n')
        for line in lines:
            if text_object.getY() < 40:  # Si llegamos al final de la página
                text_object = c.beginText(40, height - 40)
                c.drawText(text_object)
                c.showPage()
                text_object = c.beginText(40, height - 40)
                text_object.setFont("Helvetica", 10)
            
            # Manejar líneas largas
            if len(line) > 80:
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line + word) < 80:
                        current_line += word + " "
                    else:
                        text_object.textLine(current_line.strip())
                        current_line = word + " "
                if current_line:
                    text_object.textLine(current_line.strip())
            else:
                text_object.textLine(line)
        
        c.drawText(text_object)
        
        # Nueva página si no es la última
        if page_num < total_pages:
            c.showPage()
    
    c.save()
    return total_pages

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No se envió ningún archivo'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Guardar archivo temporal
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        
        # Generar nombre de salida con sufijo _OCR
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_OCR.pdf"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        try:
            # Procesar OCR
            total_pages = ocr_pdf(input_path, output_path)
            
            # Limpiar archivo de entrada
            os.remove(input_path)
            
            return jsonify({
                'success': True,
                'filename': output_filename,
                'pages_processed': total_pages
            })
        
        except Exception as e:
            # Limpiar archivos en caso de error
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)
            
            return jsonify({'error': f'Error al procesar el PDF: {str(e)}'}), 500
    
    return jsonify({'error': 'Tipo de archivo no permitido. Solo se aceptan PDFs'}), 400

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    
    if os.path.exists(file_path):
        response = send_file(file_path, as_attachment=True, download_name=filename)
        
        # Limpiar archivo después de descargarlo
        @response.call_on_close
        def cleanup():
            if os.path.exists(file_path):
                os.remove(file_path)
        
        return response
    
    return jsonify({'error': 'Archivo no encontrado'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
