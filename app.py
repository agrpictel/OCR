from flask import Flask, request, send_file, render_template, jsonify
import os
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import io
import tempfile
import shutil
import json
import time
from threading import Thread
import uuid

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['OUTPUT_FOLDER'] = '/tmp/outputs'

# Crear directorios si no existen
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Diccionario para almacenar el progreso de trabajos
jobs = {}

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def has_extractable_text(pdf_path, sample_pages=3):
    """Verifica si el PDF tiene texto extraíble"""
    try:
        reader = PdfReader(pdf_path)
        total_chars = 0
        
        for i in range(min(sample_pages, len(reader.pages))):
            text = reader.pages[i].extract_text()
            total_chars += len(text.strip())
        
        # Si tiene más de 100 caracteres en las primeras páginas, tiene texto
        return total_chars > 100
    except:
        return False

def process_pdf_with_text(job_id, input_pdf_path, output_pdf_path):
    """
    Procesa PDF que ya tiene texto extraíble (mucho más rápido)
    """
    try:
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['progress'] = 10
        jobs[job_id]['message'] = 'Analizando PDF...'
        
        reader = PdfReader(input_pdf_path)
        total_pages = len(reader.pages)
        
        jobs[job_id]['total_pages'] = total_pages
        jobs[job_id]['progress'] = 20
        
        print(f"Procesando PDF con texto: {total_pages} páginas")
        
        # Crear PDF de salida
        c = canvas.Canvas(output_pdf_path, pagesize=A4)
        width, height = A4
        
        for page_num in range(total_pages):
            progress_percent = 20 + int((page_num / total_pages) * 70)
            jobs[job_id]['progress'] = progress_percent
            jobs[job_id]['message'] = f'Extrayendo texto página {page_num + 1} de {total_pages}...'
            jobs[job_id]['current_page'] = page_num + 1
            
            # Extraer texto de la página
            page = reader.pages[page_num]
            text = page.extract_text()
            
            # Añadir texto al PDF de salida
            text_object = c.beginText(40, height - 40)
            text_object.setFont("Helvetica", 9)
            
            lines = text.split('\n')
            for line in lines:
                if text_object.getY() < 40:
                    c.drawText(text_object)
                    break
                
                # Manejar líneas largas
                if len(line) > 90:
                    words = line.split()
                    current_line = ""
                    for word in words:
                        test_line = current_line + word + " "
                        if len(test_line) < 90:
                            current_line = test_line
                        else:
                            if current_line:
                                text_object.textLine(current_line.strip())
                            current_line = word + " "
                    if current_line:
                        text_object.textLine(current_line.strip())
                else:
                    text_object.textLine(line)
            
            c.drawText(text_object)
            
            if page_num < total_pages - 1:
                c.showPage()
            
            # Pausa pequeña cada 20 páginas
            if (page_num + 1) % 20 == 0:
                time.sleep(0.05)
        
        jobs[job_id]['progress'] = 95
        jobs[job_id]['message'] = 'Guardando PDF...'
        c.save()
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['progress'] = 100
        jobs[job_id]['message'] = 'Completado'
        jobs[job_id]['pages_processed'] = total_pages
        
        print(f"PDF procesado exitosamente: {total_pages} páginas")
        
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = str(e)
        jobs[job_id]['message'] = f'Error: {str(e)}'
        print(f"Error en procesamiento: {str(e)}")
        raise

def process_pdf_with_ocr(job_id, input_pdf_path, output_pdf_path):
    """
    Procesa PDF con OCR (para PDFs escaneados sin texto)
    """
    try:
        import pytesseract
        from pdf2image import convert_from_path
        
        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['progress'] = 5
        jobs[job_id]['message'] = 'Convirtiendo PDF a imágenes...'
        
        # DPI adaptativo
        file_size_mb = os.path.getsize(input_pdf_path) / (1024 * 1024)
        dpi = 200 if file_size_mb > 10 else 250
        
        images = convert_from_path(input_pdf_path, dpi=dpi)
        
        total_pages = len(images)
        jobs[job_id]['total_pages'] = total_pages
        jobs[job_id]['progress'] = 10
        
        print(f"Procesando PDF con OCR: {total_pages} páginas")
        
        # Crear PDF de salida
        c = canvas.Canvas(output_pdf_path, pagesize=A4)
        width, height = A4
        
        for page_num, image in enumerate(images, 1):
            progress_percent = 10 + int((page_num / total_pages) * 80)
            jobs[job_id]['progress'] = progress_percent
            jobs[job_id]['message'] = f'OCR página {page_num} de {total_pages}...'
            jobs[job_id]['current_page'] = page_num
            
            # OCR
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(
                image,
                lang='spa+eng',
                config=custom_config
            )
            
            # Añadir al PDF
            text_object = c.beginText(40, height - 40)
            text_object.setFont("Helvetica", 9)
            
            lines = text.split('\n')
            for line in lines:
                if text_object.getY() < 40:
                    c.drawText(text_object)
                    break
                
                if len(line) > 90:
                    words = line.split()
                    current_line = ""
                    for word in words:
                        test_line = current_line + word + " "
                        if len(test_line) < 90:
                            current_line = test_line
                        else:
                            if current_line:
                                text_object.textLine(current_line.strip())
                            current_line = word + " "
                    if current_line:
                        text_object.textLine(current_line.strip())
                else:
                    text_object.textLine(line)
            
            c.drawText(text_object)
            
            if page_num < total_pages:
                c.showPage()
            
            if page_num % 10 == 0:
                time.sleep(0.1)
        
        jobs[job_id]['progress'] = 95
        jobs[job_id]['message'] = 'Guardando PDF...'
        c.save()
        
        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['progress'] = 100
        jobs[job_id]['message'] = 'Completado'
        jobs[job_id]['pages_processed'] = total_pages
        
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = str(e)
        jobs[job_id]['message'] = f'Error: {str(e)}'
        raise

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
        
        # Crear job ID único
        job_id = str(uuid.uuid4())
        
        # Inicializar job
        jobs[job_id] = {
            'status': 'queued',
            'progress': 0,
            'message': 'Analizando archivo...',
            'filename': output_filename,
            'input_path': input_path,
            'output_path': output_path
        }
        
        # Detectar si tiene texto extraíble
        has_text = has_extractable_text(input_path)
        
        # Procesar en un hilo separado
        if has_text:
            print("PDF tiene texto extraíble - usando extracción rápida")
            thread = Thread(
                target=process_pdf_with_text,
                args=(job_id, input_path, output_path)
            )
        else:
            print("PDF requiere OCR - usando Tesseract")
            thread = Thread(
                target=process_pdf_with_ocr,
                args=(job_id, input_path, output_path)
            )
        
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Procesamiento iniciado',
            'method': 'text_extraction' if has_text else 'ocr'
        })
    
    return jsonify({'error': 'Tipo de archivo no permitido. Solo se aceptan PDFs'}), 400

@app.route('/status/<job_id>')
def job_status(job_id):
    """Endpoint para verificar el estado del trabajo"""
    if job_id not in jobs:
        return jsonify({'error': 'Job no encontrado'}), 404
    
    job = jobs[job_id]
    
    response = {
        'status': job['status'],
        'progress': job['progress'],
        'message': job.get('message', ''),
    }
    
    if job['status'] == 'completed':
        response['filename'] = job['filename']
        response['pages_processed'] = job.get('pages_processed', 0)
    
    if job['status'] == 'error':
        response['error'] = job.get('error', 'Error desconocido')
    
    if 'total_pages' in job:
        response['total_pages'] = job['total_pages']
        response['current_page'] = job.get('current_page', 0)
    
    return jsonify(response)

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    
    if os.path.exists(file_path):
        response = send_file(file_path, as_attachment=True, download_name=filename)
        
        # Limpiar archivos después de descargarlo
        @response.call_on_close
        def cleanup():
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                # Buscar y eliminar archivo de entrada asociado
                for job_id, job_data in list(jobs.items()):
                    if job_data.get('filename') == filename:
                        input_path = job_data.get('input_path')
                        if input_path and os.path.exists(input_path):
                            os.remove(input_path)
                        del jobs[job_id]
                        break
            except Exception as e:
                print(f"Error en cleanup: {e}")
        
        return response
    
    return jsonify({'error': 'Archivo no encontrado'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
