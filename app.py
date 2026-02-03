from __future__ import annotations

import os
import uuid
import time
import tempfile
import subprocess
from threading import Thread
from pathlib import Path

from flask import Flask, request, send_file, render_template, jsonify
from werkzeug.utils import secure_filename


app = Flask(__name__)

# ---- Config (tunable via env vars) ----
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "/tmp/uploads")
app.config["OUTPUT_FOLDER"] = os.getenv("OUTPUT_FOLDER", "/tmp/outputs")

# Safety/ops limits (avoid killing tiny servers)
MAX_PAGES_TOTAL = int(os.getenv("MAX_PAGES_TOTAL", "300"))
PAGES_PER_CHUNK = int(os.getenv("PAGES_PER_CHUNK", "25"))
OCR_LANGUAGE = os.getenv("OCR_LANGUAGE", "spa+eng")
OCR_TIMEOUT_SECONDS = int(os.getenv("OCR_TIMEOUT_SECONDS", "1200"))  # 20 min

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}

# In-memory job tracker (fine for single-instance; for multi-instance use Redis)
jobs: dict[str, dict] = {}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def looks_like_pdf(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(5) == b"%PDF-"
    except Exception:
        return False


def _require_deps() -> None:
    """Fail fast with a helpful message if OCR deps are missing."""
    missing = []
    for cmd in ("ocrmypdf", "tesseract", "qpdf", "gs"):
        if not _which(cmd):
            missing.append(cmd)
    if missing:
        raise RuntimeError(
            "Faltan dependencias del sistema: "
            + ", ".join(missing)
            + ". En Render/Ubuntu instala: tesseract-ocr (+idiomas), ocrmypdf, ghostscript (gs), qpdf."
        )


def _which(cmd: str) -> bool:
    from shutil import which

    return which(cmd) is not None


def pdf_page_count(pdf_path: str) -> int:
    # pikepdf is the most reliable for counting pages
    import pikepdf

    with pikepdf.open(pdf_path) as pdf:
        return len(pdf.pages)


def split_pdf(pdf_path: str, out_dir: str, pages_per_chunk: int) -> list[str]:
    """Split a PDF into chunks of N pages. Returns chunk paths in order."""
    import pikepdf

    out = []
    with pikepdf.open(pdf_path) as src:
        total = len(src.pages)
        if total <= pages_per_chunk:
            # Copy as a single chunk (so we have a unified pipeline)
            chunk_path = os.path.join(out_dir, "chunk_0001.pdf")
            src.save(chunk_path)
            return [chunk_path]

        for i, start in enumerate(range(0, total, pages_per_chunk), 1):
            end = min(start + pages_per_chunk, total)
            dst = pikepdf.Pdf.new()
            dst.pages.extend(src.pages[start:end])
            chunk_path = os.path.join(out_dir, f"chunk_{i:04d}.pdf")
            dst.save(chunk_path)
            out.append(chunk_path)
    return out


def merge_pdfs(pdf_paths: list[str], output_pdf_path: str) -> None:
    import pikepdf

    merged = pikepdf.Pdf.new()
    for p in pdf_paths:
        with pikepdf.open(p) as part:
            merged.pages.extend(part.pages)
    merged.save(output_pdf_path)


def run_ocrmypdf(input_pdf: str, output_pdf: str, job_id: str) -> None:
    """Run ocrmypdf as a subprocess. Keeps images and adds a text layer."""
    # NOTE: --skip-text avoids re-OCR on pages that already have text.
    # --rotate-pages / --deskew improves real scans without user effort.
    cmd = [
        "ocrmypdf",
        "--language",
        OCR_LANGUAGE,
        "--skip-text",
        "--rotate-pages",
        "--deskew",
        "--clean-final",
        "--optimize",
        "1",
        "--output-type",
        "pdf",
        input_pdf,
        output_pdf,
    ]

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=OCR_TIMEOUT_SECONDS,
    )
    if proc.returncode != 0:
        # Keep a short tail of logs for diagnosis
        tail = (proc.stdout or "").strip().splitlines()[-25:]
        raise RuntimeError("ocrmypdf falló. Log (últimas líneas):\n" + "\n".join(tail))


def process_pdf(job_id: str, input_pdf_path: str, output_pdf_path: str) -> None:
    """Main pipeline: validate -> split -> OCR each chunk -> merge -> cleanup."""
    try:
        _require_deps()

        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 3
        jobs[job_id]["message"] = "Analizando PDF…"

        total_pages = pdf_page_count(input_pdf_path)
        jobs[job_id]["total_pages"] = total_pages

        if total_pages == 0:
            raise RuntimeError("El PDF no tiene páginas.")
        if total_pages > MAX_PAGES_TOTAL:
            raise RuntimeError(
                f"PDF demasiado grande ({total_pages} páginas). Límite actual: {MAX_PAGES_TOTAL}. "
                "Súbelo en partes o sube el límite con MAX_PAGES_TOTAL."
            )

        # Heurística: si es enorme, baja el chunk para no reventar RAM/CPU
        file_size_mb = os.path.getsize(input_pdf_path) / (1024 * 1024)
        pages_per_chunk = PAGES_PER_CHUNK
        if file_size_mb > 25:
            pages_per_chunk = max(10, min(pages_per_chunk, 15))
        if total_pages > 150:
            pages_per_chunk = max(10, min(pages_per_chunk, 15))

        jobs[job_id]["progress"] = 8
        jobs[job_id]["message"] = "Preparando trabajo (dividiendo en partes)…"

        with tempfile.TemporaryDirectory(prefix="ocrjob_") as tmp:
            chunk_dir = os.path.join(tmp, "chunks")
            out_dir = os.path.join(tmp, "out")
            os.makedirs(chunk_dir, exist_ok=True)
            os.makedirs(out_dir, exist_ok=True)

            chunks = split_pdf(input_pdf_path, chunk_dir, pages_per_chunk)
            ocr_outputs: list[str] = []

            total_chunks = len(chunks)
            jobs[job_id]["total_chunks"] = total_chunks

            for idx, chunk_path in enumerate(chunks, 1):
                # Progress mapping: 10%..95% across chunks
                base = 10
                span = 85
                prog = base + int(((idx - 1) / max(1, total_chunks)) * span)
                jobs[job_id]["progress"] = prog
                jobs[job_id]["message"] = f"OCR parte {idx}/{total_chunks}…"
                jobs[job_id]["current_chunk"] = idx

                out_part = os.path.join(out_dir, f"ocr_{idx:04d}.pdf")
                run_ocrmypdf(chunk_path, out_part, job_id)
                ocr_outputs.append(out_part)

                # Tiny pause to keep UI responsive in cheap hosts
                if idx % 3 == 0:
                    time.sleep(0.05)

            jobs[job_id]["progress"] = 95
            jobs[job_id]["message"] = "Uniendo partes en un único PDF…"
            merge_pdfs(ocr_outputs, output_pdf_path)

        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = "Completado"
        jobs[job_id]["pages_processed"] = total_pages

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["message"] = f"Error: {str(e)}"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No se seleccionó ningún archivo"}), 400

    if not (file and allowed_file(file.filename)):
        return jsonify({"error": "Tipo de archivo no permitido. Solo se aceptan PDFs"}), 400

    filename = secure_filename(file.filename)
    input_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(input_path)

    if not looks_like_pdf(input_path):
        try:
            os.remove(input_path)
        except Exception:
            pass
        return jsonify({"error": "El archivo no parece un PDF válido"}), 400

    base_name = os.path.splitext(filename)[0]
    output_filename = f"{base_name}_OCR.pdf"
    output_path = os.path.join(app.config["OUTPUT_FOLDER"], output_filename)

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "queued",
        "progress": 0,
        "message": "En cola…",
        "filename": output_filename,
        "input_path": input_path,
        "output_path": output_path,
    }

    thread = Thread(target=process_pdf, args=(job_id, input_path, output_path), daemon=True)
    thread.start()

    return jsonify(
        {
            "success": True,
            "job_id": job_id,
            "message": "Procesamiento iniciado",
            "method": "ocrmypdf",
        }
    )


@app.route("/status/<job_id>")
def job_status(job_id: str):
    if job_id not in jobs:
        return jsonify({"error": "Job no encontrado"}), 404

    job = jobs[job_id]
    response = {
        "status": job["status"],
        "progress": job.get("progress", 0),
        "message": job.get("message", ""),
        "total_pages": job.get("total_pages", 0),
        "pages_processed": job.get("pages_processed", 0),
        "total_chunks": job.get("total_chunks", 0),
        "current_chunk": job.get("current_chunk", 0),
    }

    if job["status"] == "completed":
        response["filename"] = job["filename"]
    if job["status"] == "error":
        response["error"] = job.get("error", "Error desconocido")

    return jsonify(response)


@app.route("/download/<filename>")
def download_file(filename: str):
    file_path = os.path.join(app.config["OUTPUT_FOLDER"], filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "Archivo no encontrado"}), 404

    response = send_file(file_path, as_attachment=True, download_name=filename)

    # Cleanup on successful download
    @response.call_on_close
    def cleanup():
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            for jid, job_data in list(jobs.items()):
                if job_data.get("filename") == filename:
                    in_path = job_data.get("input_path")
                    if in_path and os.path.exists(in_path):
                        os.remove(in_path)
                    del jobs[jid]
                    break
        except Exception as e:
            print(f"Error en cleanup: {e}")

    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
