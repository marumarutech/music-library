const alertEl = document.getElementById("alert");
const form = document.getElementById("download-form");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const statusText = document.getElementById("status-text");
const trackList = document.getElementById("track-list");
const emptyLibrary = document.getElementById("empty-library");
const libraryPath = document.getElementById("library-path");
const refreshBtn = document.getElementById("refresh-btn");

function showAlert(message, type = "error") {
  alertEl.textContent = message;
  alertEl.className = `alert ${type}`;
  alertEl.classList.remove("hidden");
}

function hideAlert() {
  alertEl.classList.add("hidden");
}

function setLoading(active, message = "") {
  statusEl.classList.toggle("hidden", !active);
  statusText.textContent = message;
  submitBtn.disabled = active;
}

async function pollJob(jobId) {
  const interval = 1500;

  while (true) {
    const res = await fetch(`/api/jobs/${jobId}`);
    if (!res.ok) throw new Error("ジョブ状態の取得に失敗しました");

    const job = await res.json();

    if (job.status === "running" || job.status === "pending") {
      setLoading(true, job.message || "ダウンロード中…");
      await new Promise((r) => setTimeout(r, interval));
      continue;
    }

    if (job.status === "done") {
      setLoading(false);
      showAlert(`${job.titles.length} 件ダウンロードしました`, "success");
      await loadTracks();
      return;
    }

    setLoading(false);
    throw new Error(job.message || "ダウンロードに失敗しました");
  }
}

async function loadTracks() {
  const res = await fetch("/api/tracks");
  const data = await res.json();

  trackList.innerHTML = "";
  const tracks = data.tracks || [];

  emptyLibrary.classList.toggle("hidden", tracks.length > 0);

  for (const track of tracks) {
    const li = document.createElement("li");
    li.innerHTML = `
      <span class="track-name">${escapeHtml(track.name)}</span>
      <span class="track-meta">${track.size_mb} MB</span>
    `;
    trackList.appendChild(li);
  }
}

async function loadHealth() {
  const res = await fetch("/api/health");
  const data = await res.json();

  libraryPath.textContent = `保存先: ${data.library}`;

  if (!data.ffmpeg_ok) {
    showAlert(data.ffmpeg_message);
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  hideAlert();

  const url = document.getElementById("url").value.trim();
  const quality = document.getElementById("quality").value;
  const playlist = document.getElementById("playlist").checked;
  const trimSilence = document.getElementById("trim-silence").checked;
  const normalizeLoudness = document.getElementById("normalize-loudness").checked;

  setLoading(true, "開始中…");

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        quality,
        playlist,
        trim_silence: trimSilence,
        normalize_loudness: normalizeLoudness,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "リクエストに失敗しました");
    }

    const { job_id } = await res.json();
    await pollJob(job_id);
  } catch (err) {
    setLoading(false);
    showAlert(err.message || String(err));
  }
});

refreshBtn.addEventListener("click", loadTracks);

loadHealth();
loadTracks();
