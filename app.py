import os
import time
import shutil

import uuid
import subprocess
from imageio_ffmpeg import get_ffmpeg_exe
import threading
from flask import Flask, request, jsonify, render_template, send_from_directory

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
OUTPUT_DIR = os.path.join(DATA_DIR, "outputs")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)

# In-memory jobs store (MVP)
jobs = {}  # job_id -> dict(status, progress, output_filename, error)

def simulate_processing(job_id: str, uploaded_video_filename: str):
    """
    Day-2: Extract audio from uploaded video using ffmpeg,
    update stage-based progress, then create placeholder output.
    """
    try:
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["stage"] = "Starting"
        jobs[job_id]["progress"] = 1

        # 1) Extract Audio
        jobs[job_id]["stage"] = "Extracting audio"
        jobs[job_id]["progress"] = 10

        ffmpeg_path = get_ffmpeg_exe()

        src_video = os.path.join(UPLOAD_DIR, uploaded_video_filename)
        audio_name = f"{job_id}.wav"
        out_audio = os.path.join(OUTPUT_DIR, audio_name)

        # ffmpeg command: extract wav 16kHz mono
        cmd = [
            ffmpeg_path,
            "-y",
            "-i", src_video,
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-f", "wav",
            out_audio
        ]

        # run ffmpeg
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if p.returncode != 0:
            raise RuntimeError("ffmpeg failed: " + (p.stderr[-800:] if p.stderr else "unknown error"))

        jobs[job_id]["progress"] = 40

        # 2) Preparing (placeholder for model pre-processing)
        jobs[job_id]["stage"] = "Preparing inputs"
        for pval in [45, 50, 55, 60]:
            jobs[job_id]["progress"] = pval
            time.sleep(0.4)

        # 3) Generating (placeholder for Day-3 real AI generation)
        jobs[job_id]["stage"] = "Generating video"
        for pval in [65, 70, 75, 80, 85]:
            jobs[job_id]["progress"] = pval
            time.sleep(0.5)

        # 4) Finalizing + output (Day-1 placeholder output)
        jobs[job_id]["stage"] = "Finalizing"
        jobs[job_id]["progress"] = 90
        time.sleep(0.6)

        out_name = f"{job_id}.mp4"
        out_path = os.path.join(OUTPUT_DIR, out_name)
        jobs[job_id]["stage"] = "finalizing"
        jobs[job_id]["progress"] = 90

        shutil.copyfile(src_video, out_path)
        jobs[job_id]["progress"] = 98



        jobs[job_id]["progress"] = 100
        jobs[job_id]["stage"] = "Done"

        jobs[job_id]["status"] = "done"
        jobs[job_id]["output_filename"] = out_name
        jobs[job_id]["audio_filename"] = audio_name

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["stage"] = "Failed"


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/start", methods=["POST"])
def start_job():
    """
    Expects multipart form-data:
    - photo: image file
    - video: video file
    """
    if "photo" not in request.files or "video" not in request.files:
        return jsonify({"error": "photo and video are required"}), 400

    photo = request.files["photo"]
    video = request.files["video"]

    # Basic validation
    if photo.filename == "" or video.filename == "":
        return jsonify({"error": "Both files must have a filename"}), 400

    job_id = str(uuid.uuid4())

    # Save uploads with safe unique names
    photo_ext = os.path.splitext(photo.filename)[1].lower() or ".jpg"
    video_ext = os.path.splitext(video.filename)[1].lower() or ".mp4"

    photo_name = f"{job_id}_photo{photo_ext}"
    video_name = f"{job_id}_video{video_ext}"

    photo.save(os.path.join(UPLOAD_DIR, photo_name))
    video.save(os.path.join(UPLOAD_DIR, video_name))
        # Create job record
    jobs[job_id] = {
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "output_filename": None,
        "audio_filename": None,
        "error": None,
        "photo": photo_name,
        "video": video_name
    }

    # Start background thread
    t = threading.Thread(target=simulate_processing, args=(job_id, video_name))
    t.daemon = True
    t.start()

    return jsonify({"job_id": job_id})

    video_path = os.path.join(UPLOAD_DIR, video_name)
    if os.path.getsize(video_path) > 80 * 1024 * 1024:  # 80MB
     jobs[job_id]["status"] = "failed"
     jobs[job_id]["error"] = "Video too large for demo. Please upload <= 80MB."
    return jsonify({"error": jobs[job_id]["error"]}), 400


    # Create job record
    jobs[job_id] = {
    "status": "queued",
    "stage": "queued",
    "progress": 0,
    "output_filename": None,
    "audio_filename": None,
    "error": None,
    "photo": photo_name,
    "video": video_name
    }


    # Start background thread to simulate processing
    t = threading.Thread(target=simulate_processing, args=(job_id, video_name), daemon=True)
    t.start()

    return jsonify({"job_id": job_id})

@app.route("/api/progress/<job_id>", methods=["GET"])
def job_progress(job_id):

    job = jobs.get(job_id)

    if job is None:
        return jsonify({
            "status": "not_found",
            "stage": "not_found",
            "progress": 0,
            "error": "job not found"
        })

    return jsonify({
        "status": job.get("status"),
        "stage": job.get("stage"),
        "progress": job.get("progress"),
        "error": job.get("error")
    })



@app.route("/api/jobs", methods=["GET"])
def list_jobs():
    # returns all jobs (MVP debug)
    return jsonify(jobs)


@app.route("/api/result/<job_id>", methods=["GET"])
def job_result(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "job not found"}), 404
    if job["status"] != "done":
        return jsonify({"error": "not ready", "status": job["status"]}), 400
    return jsonify({
        "video_url": f"/outputs/{job['output_filename']}",
        "audio_url": f"/outputs/{job['audio_filename']}" if job.get("audio_filename") else None
        })



# Serve uploaded/output files
@app.route("/outputs/<path:filename>")
def outputs(filename):
    return send_from_directory(OUTPUT_DIR, filename)

@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
