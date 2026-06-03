const alertEl = document.getElementById("alert");
const form = document.getElementById("download-form");
const submitBtn = document.getElementById("submit-btn");
const statusEl = document.getElementById("status");
const statusText = document.getElementById("status-text");
const trackList = document.getElementById("track-list");
const emptyLibrary = document.getElementById("empty-library");
const libraryPath = document.getElementById("library-path");
const refreshBtn = document.getElementById("refresh-btn");
const editDialog = document.getElementById("edit-dialog");
const editForm = document.getElementById("edit-form");
const editOriginalPath = document.getElementById("edit-original-path");
const editFilename = document.getElementById("edit-filename");
const editTitle = document.getElementById("edit-title");
const editArtist = document.getElementById("edit-artist");
const editAlbum = document.getElementById("edit-album");
const editCancelBtn = document.getElementById("edit-cancel-btn");
const editSaveBtn = document.getElementById("edit-save-btn");

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

function renderMetaLine(label, value) {
  const text = value || "（未設定）";
  const valueClass = value ? "track-meta-value" : "track-meta-empty";
  return `
    <div class="track-meta-line">
      <span class="track-meta-label">${label}</span>
      <span class="${valueClass}">${escapeHtml(text)}</span>
    </div>
  `;
}

function renderTrackItem(track) {
  const li = document.createElement("li");
  li.className = "track-item";
  li.innerHTML = `
    <div class="track-info">
      ${renderMetaLine("曲名", track.title)}
      ${renderMetaLine("アーティスト", track.artist)}
      <span class="track-filename">${escapeHtml(track.filename)} · ${track.size_mb} MB</span>
    </div>
    <button type="button" class="secondary track-edit-btn">編集</button>
  `;
  li.querySelector(".track-edit-btn").addEventListener("click", () => openEditDialog(track));
  trackList.appendChild(li);
}

function renderSection(title, tracks) {
  if (tracks.length === 0) {
    return;
  }

  const heading = document.createElement("li");
  heading.className = "track-section";
  heading.textContent = title;
  trackList.appendChild(heading);

  for (const track of tracks) {
    renderTrackItem(track);
  }
}

function openEditDialog(track) {
  editOriginalPath.value = track.path;
  editFilename.value = track.name;
  editTitle.value = track.title || track.name;
  editArtist.value = track.artist || "";
  editAlbum.value = track.album || "";
  editDialog.showModal();
  editTitle.focus();
}

function closeEditDialog() {
  editDialog.close();
}

async function saveTrackEdit(event) {
  event.preventDefault();

  editSaveBtn.disabled = true;

  try {
    const res = await fetch("/api/tracks", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path: editOriginalPath.value,
        new_filename: editFilename.value.trim(),
        title: editTitle.value.trim(),
        artist: editArtist.value.trim(),
        album: editAlbum.value.trim(),
      }),
    });

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || "保存に失敗しました");
    }

    closeEditDialog();
    showAlert("曲情報を保存しました", "success");
    await loadTracks();
  } catch (err) {
    showAlert(err.message || String(err));
  } finally {
    editSaveBtn.disabled = false;
  }
}

async function loadTracks() {
  const res = await fetch("/api/tracks");
  const data = await res.json();

  trackList.innerHTML = "";
  const tracks = data.tracks || [];

  emptyLibrary.classList.toggle("hidden", tracks.length > 0);

  renderSection("ライブラリ", tracks.filter((track) => !track.synced));
  renderSection("済み", tracks.filter((track) => track.synced));
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
editForm.addEventListener("submit", saveTrackEdit);
editCancelBtn.addEventListener("click", closeEditDialog);

loadHealth();
loadTracks();
