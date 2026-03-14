import json
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# ====== EDIT ONLY IF YOUR ROOT PATH IS DIFFERENT ======
ROOT = Path(r"C:\Users\HP\Desktop\ai_mvp")
SADTALKER_DIR = ROOT / "SadTalker"

INPUT_DIR = ROOT / "jobs" / "input"
OUTPUT_DIR = ROOT / "jobs" / "output"
LOG_DIR = ROOT / "jobs" / "logs"

# Stable MVP settings (reduce flicker/jump)
SADTALKER_ARGS = [
    "--preprocess", "crop",
    "--size", "256",
    "--pose_style", "1",
    # enhancer intentionally OFF for stability (you already enhance via GFPGAN pipeline)
]

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def read_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def write_json(p: Path, data: dict):
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def update_status(job_json: Path, status: str, extra: dict | None = None):
    data = read_json(job_json)
    data["status"] = status
    data["updated_at"] = now_iso()
    if extra:
        data.update(extra)
    write_json(job_json, data)

def run_sadtalker(image_path: Path, audio_path: Path, log_file: Path) -> int:
    cmd = [
        "python", "inference.py",
        "--source_image", str(image_path),
        "--driven_audio", str(audio_path),
        "--result_dir", "results",
    ] + SADTALKER_ARGS

    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as f:
        f.write("\n" + "=" * 90 + "\n")
        f.write(f"[{now_iso()}] RUN: {' '.join(cmd)}\n")
        f.flush()
        p = subprocess.Popen(cmd, cwd=str(SADTALKER_DIR), stdout=f, stderr=f, shell=False)
        return p.wait()

def find_latest_mp4(results_dir: Path) -> Path | None:
    mp4s = list(results_dir.rglob("*.mp4"))
    if not mp4s:
        return None
    mp4s.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return mp4s[0]

def process_job(job_folder: Path):
    job_json = job_folder / "job.json"
    data = read_json(job_json)

    job_id = data.get("job_id", job_folder.name)
    image_rel = data.get("image", "image.png")
    audio_rel = data.get("audio", "audio.wav")

    image_path = job_folder / image_rel
    audio_path = job_folder / audio_rel

    if not image_path.exists() or not audio_path.exists():
        update_status(job_json, "failed", {"error": "Missing image/audio in job folder"})
        return

    log_file = LOG_DIR / f"{job_id}.log"
    update_status(job_json, "running")

    results_dir = SADTALKER_DIR / "results"
    rc = run_sadtalker(image_path, audio_path, log_file)

    if rc != 0:
        update_status(job_json, "failed", {"return_code": rc})
        return

    out_mp4 = find_latest_mp4(results_dir)
    if not out_mp4:
        update_status(job_json, "failed", {"error": "No mp4 produced"})
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    final_out = OUTPUT_DIR / f"{job_id}.mp4"
    shutil.copy2(out_mp4, final_out)

    update_status(job_json, "done", {"output": str(final_out)})

def main():
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    print("✅ Worker started")
    print("Watching:", INPUT_DIR)
    print("Outputs:", OUTPUT_DIR)

    while True:
        did_work = False

        for job_folder in sorted([p for p in INPUT_DIR.iterdir() if p.is_dir()]):
            job_json = job_folder / "job.json"
            if not job_json.exists():
                continue

            data = read_json(job_json)
            if data.get("status") == "queued":
                did_work = True
                process_job(job_folder)

        if not did_work:
            time.sleep(2)

if __name__ == "__main__":
    main()