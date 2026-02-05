from __future__ import annotations

import os
import uuid
import time
import shutil
import tempfile
import subprocess
from threading import Thread
from typing import Dict, Any, List

from flask import Flask, request, send_file, render_template, jsonify
from werkzeug.utils import secure_filename
from PyPDF2 import PdfReader, PdfWriter

app = Flask(__name__)

# Configuration from environment
MAX_UPLOAD_MB = int(os.environ.get('MAX_UPLOAD_MB', '50'))
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp/uploads')
app.config['OUTPUT_FOLDER'] = os.environ.get('OUTPUT_FOLDER', '/tmp/outputs')

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

# Job tracking dictionary
jobs: Dict[str, Dict[str, Any]] = {}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def looks_like_pdf(path: str) -> bool:
    try:
        with open(path, 'rb') as f:
            return f.read(5) == b'%PDF-'
    except Exception:
        return False


def check_system_dependencies() -> List[str]:
    deps = {
        'tesseract': 'tesseract',
        'qpdf': 'qpdf',
        'ghostscript': 'gs',
        'ocrmypdf': 'ocrmypdf',
    }
    missing: List[str] = []
    for name, cmd in deps.items():
        if shutil.which(cmd) is None:
            missing.append(name)
    return missing


def pdf_page_count(pdf_path: str) -> int:
    reader = PdfReader(pdf_path)
    return len(reader.pages)


def split_pdf(pdf_path: str, out_dir: str, pages_per_chunk: int) -> List[str]:
    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    chunk_paths: List[str] = []
    idx = 1
    for start in range(0, total, pages_per_chunk):
        end = min(start + pages_per_chunk, total)
        writer = PdfWriter()
        for i in range(start, end):
            writer.add_page(reader.pages[i])
        chunk_path = os.path.join(out_dir, f"chunk_{idx:04d}.pdf")
        with open(chunk_path, 'wb') as f:
            writer.write(f)
        chunk_paths.append(chunk_path)
        idx += 1
    return chunk_paths


def merge_pdfs(pdf_paths: List[str], output_pdf_path: str) -> None:
    writer = PdfWriter()
    for path in pdf_paths:
        r = PdfReader(path)
        for page in r.pages:
            writer.add_page(page)
    with open(output_pdf_path, 'wb') as f:
        writer.write(f)


def run_ocrmypdf(input_path: str, output_path: str, lang: str, timeout: int) -> None:
    cmd = [
        'ocrmypdf',
        '--redo-ocr',
        '--rotate-pages',
        '--deskew',
        '--clean-final',
        '--optimize', '1',
        '-l', lang,
        input_path,
        output_path
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout
    )
    if result.returncode != 0:
        tail = (result.stdout or '').splitlines()[-30:]
        raise RuntimeError("ocrmypdf falló. Log (últimas líneas):\n" + "\n".join(tail))


def process_pdf_with_ocr(job_id: str, input_pdf_path: str, output_pdf_path: str) -> None:
    try:
        missing = check_system_dependencies()
        if missing:
            missing_list = ", ".join(missing)
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = missing_list
            jobs[job_id]['message'] = (
                f"Faltan dependencias del sistema: {missing_list}. "
                "En Render/Ubuntu instala: tesseract-ocr (+idiomas), ocrmypdf, ghostscript (gs), qpdf."
            )
            return

        jobs[job_id]['status'] = 'processing'
        jobs[job_id]['progress'] = 3
        jobs[job_id]['message'] = "Analizando PDF..."

        if not looks_like_pdf(input_pdf_path):
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = "Archivo no parece un PDF válido"
            jobs[job_id]['message'] = "El archivo subido no parece un PDF válido."
            return

        max_pages_total = int(os.environ.get('MAX_PAGES_TOTAL', '300'))
        pages_per_chunk = int(os.environ.get('PAGES_PER_CHUNK', '25'))
        lang = os.environ.get('OCR_LANGUAGE', 'spa+eng')
        ocr_timeout = int(os.environ.get('OCR_TIMEOUT_SECONDS', '1200'))

        total_pages = pdf_page_count(input_pdf_path)
        jobs[job_id]['total_pages'] = total_pages

        if total_pages <= 0:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = "PDF sin páginas"
            jobs[job_id]['message'] = "El PDF no tiene páginas."
            return

        if total_pages > max_pages_total:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = "Exceso de páginas"
            jobs[job_id]['message'] = (
                f"El PDF tiene {total_pages} páginas, supera el límite de {max_pages_total}. "
                "Reduce el PDF o aumenta MAX_PAGES_TOTAL."
            )
            return

        file_size_mb = os.path.getsize(input_pdf_path) / (1024 * 1024)
        if file_size_mb > 25 or total_pages > 150:
            pages_per_chunk = max(10, min(pages_per_chunk, 15))

        jobs[job_id]['progress'] = 8
        jobs[job_id]['message'] = "Preparando trabajo (dividiendo en partes)..."

        with tempfile.TemporaryDirectory(prefix="ocrjob_") as tmp:
            chunk_dir = os.path.join(tmp, "chunks")
            out_dir = os.path.join(tmp, "out")
            os.makedirs(chunk_dir, exist_ok=True)
            os.makedirs(out_dir, exist_ok=True)

            chunk_paths = split_pdf(input_pdf_path, chunk_dir, pages_per_chunk)
            n_chunks = len(chunk_paths)
            ocr_parts: List[str] = []
            for idx, chunk_path in enumerate(chunk_paths, start=1):
                jobs[job_id]['message'] = f"OCR parte {idx} de {n_chunks}..."
                jobs[job_id]['progress'] = 10 + int(((idx - 1) / max(n_chunks, 1)) * 75)
                part_output = os.path.join(out_dir, f"chunk_{idx:04d}_ocr.pdf")
                run_ocrmypdf(chunk_path, part_output, lang=lang, timeout=ocr_timeout)
                ocr_parts.append(part_output)
                if idx % 10 == 0:
                    time.sleep(0.05)

            jobs[job_id]['message'] = "Combinando partes en un único PDF..."
            jobs[job_id]['progress'] = 92
            merge_pdfs(ocr_parts, output_pdf_path)

        jobs[job_id]['status'] = 'completed'
        jobs[job_id]['progress'] = 100
        jobs[job_id]['message'] = "Completado"
        jobs[job_id]['pages_processed'] = total_pages

    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = str(e)
        jobs[job_id]['message'] = f"Error: {str(e)}"


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No se seleccionó ningún archivo'}), 400
        if not allowed_file(file.filename):
            return jsonify({'error': 'Tipo de archivo no permitido. Solo se aceptan PDFs'}), 400
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)
        if not looks_like_pdf(input_path):
            try:
                os.remove(input_path)
            except Exception:
                pass
            return jsonify({'error': 'El archivo subido no parece un PDF válido'}), 400
        base_name = os.path.splitext(filename)[0]
        output_filename = f"{base_name}_OCR.pdf"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            'status': 'queued',
            'progress': 0,
            'message': 'En cola...',
            'filename': output_filename,
            'input_path': input_path,
            'output_path': output_path,
        }
        thread = Thread(target=process_pdf_with_ocr, args=(job_id, input_path, output_path), daemon=True)
        thread.start()
        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Procesamiento iniciado',
            'method': 'ocr'
        })
    except Exception as e:
        return jsonify({'error': f"Error en /upload: {str(e)}"}), 500


@app.route('/status/<job_id>')
def job_status(job_id: str):
    if job_id not in jobs:
        return jsonify({'error': 'Job no encontrado'}), 404
    job = jobs[job_id]
    resp = {
        'status': job.get('status', 'unknown'),
        'progress': job.get('progress', 0),
        'message': job.get('message', ''),
        'total_pages': job.get('total_pages', 0),
        'current_page': job.get('current_page', 0),
    }
    if resp['status'] == 'completed':
        resp['filename'] = job.get('filename')
        resp['pages_processed'] = job.get('pages_processed', 0)
    if resp['status'] == 'error':
        resp['error'] = job.get('error', 'Error desconocido')
    return jsonify(resp)


@app.route('/download/<filename>')
def download_file(filename: str):
    file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'Archivo no encontrado'}), 404
    response = send_file(file_path, as_attachment=True, download_name=filename)
    @response.call_on_close
    def cleanup():
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            for jid, data in list(jobs.items()):
                if data.get('filename') == filename:
                    in_path = data.get('input_path')
                    if in_path and os.path.exists(in_path):
                        os.remove(in_path)
                    del jobs[jid]
                    break
        except Exception:
            pass
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
