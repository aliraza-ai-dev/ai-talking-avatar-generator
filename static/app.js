const photoEl = document.getElementById("photo");
const videoEl = document.getElementById("video");
const btn = document.getElementById("generate");

const statusBox = document.getElementById("statusBox");
const statusText = document.getElementById("status");
const stageText = document.getElementById("stage");

const percentText = document.getElementById("percent");
const barFill = document.getElementById("barFill");
const hint = document.getElementById("hint");

const outVideo = document.getElementById("outVideo");
const outAudio = document.getElementById("outAudio");
const audioLink = document.getElementById("audioLink");

const downloadLink = document.getElementById("downloadLink");

let pollTimer = null;

function setProgress(p) {
  percentText.textContent = String(p);
  barFill.style.width = `${p}%`;
}

function setStatus(s) {
  statusText.textContent = s;
  hint.textContent =
    s === "queued" ? "Queued…" :
    s === "processing" ? "Processing…" :
    s === "done" ? "Done ✅" :
    s === "failed" ? "Failed ❌" : "-";
}

async function startJob() {
  const photo = photoEl.files[0];
  const video = videoEl.files[0];

  if (!photo || !video) {
    alert("Please upload both Photo and Video.");
    return;
  }

  btn.disabled = true;
  outVideo.classList.add("hidden");
  downloadLink.classList.add("hidden");

  statusBox.classList.remove("hidden");
  setStatus("queued");
  stageText.textContent = "-";
  setProgress(0);

  const fd = new FormData();
  fd.append("photo", photo);
  fd.append("video", video);

  const res = await fetch("/api/start", { method: "POST", body: fd });
  const data = await res.json();
  if (!res.ok) {
    btn.disabled = false;
    alert(data.error || "Failed to start job");
    return;
  }

  const jobId = data.job_id;
  poll(jobId);
}

async function poll(jobId) {
  if (pollTimer) clearInterval(pollTimer);

  pollTimer = setInterval(async () => {
    const r = await fetch(`/api/progress/${jobId}`);
    const d = await r.json();
    if (!r.ok) {
      setStatus("failed");
      hint.textContent = d.error || "Job not found";
      btn.disabled = false;
      clearInterval(pollTimer);
      return;
    }

    setStatus(d.status);
    stageText.textContent = d.stage || "-";
    setProgress(d.progress ?? 0);
    


    if (d.status === "done") {
      clearInterval(pollTimer);
      const rr = await fetch(`/api/result/${jobId}`);
      const dd = await rr.json();
      if (rr.ok) {
        outVideo.src = dd.video_url;
        
        if (dd.audio_url) {
           outAudio.src = dd.audio_url;
           outAudio.classList.remove("hidden");
           audioLink.href = dd.audio_url;
           audioLink.classList.remove("hidden");
    }
        outVideo.classList.remove("hidden");
        downloadLink.href = dd.video_url;
        downloadLink.classList.remove("hidden");
      } else {
        hint.textContent = dd.error || "Result not available";
      }
      btn.disabled = false;
    }

    if (d.status === "failed") {
      clearInterval(pollTimer);
      hint.textContent = d.error || "Processing failed";
      btn.disabled = false;
    }
  }, 1200);
}

btn.addEventListener("click", startJob);
