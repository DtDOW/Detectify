const fileInput = document.getElementById("fileInput");
const chooseBtn = document.getElementById("chooseBtn");
const dropzone = document.getElementById("dropzone");
const statusDiv = document.getElementById("status");
const resultDiv = document.getElementById("result");
const progressBar = document.getElementById("progressBar");
const progressFill = document.getElementById("progress");

chooseBtn.addEventListener("click", () => fileInput.click());

fileInput.addEventListener("change", () => {
  if (fileInput.files.length) startUpload(fileInput.files[0]);
});

["dragenter","dragover"].forEach(event => {
  dropzone.addEventListener(event, e => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
});

["dragleave","drop"].forEach(event => {
  dropzone.addEventListener(event, e => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  });
});

dropzone.addEventListener("drop", e => {
  const file = e.dataTransfer.files[0];
  if (file) startUpload(file);
});

function startUpload(file) {
  const maxBytes = 500 * 1024 * 1024;
  if (file.size > maxBytes) {
    statusDiv.textContent = "File too large.";
    return;
  }

  statusDiv.textContent = "Uploading...";
  const form = new FormData();
  form.append("file", file);

  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/upload");

  xhr.upload.onprogress = e => {
    if (e.lengthComputable) {
      const pct = (e.loaded / e.total) * 100;
      progressBar.style.display = "block";
      progressFill.style.width = pct + "%";
    }
  };

  xhr.onload = () => {
    progressBar.style.display = "none";
    progressFill.style.width = "0%";

    let resp;
    try { resp = JSON.parse(xhr.responseText); } catch { resp = null; }

    if (!resp || !resp.success) {
      statusDiv.textContent = "Error: " + (resp?.error || "Unknown error");
      return;
    }

    const label = resp.label;
    const conf = resp.confidence;

    resultDiv.innerHTML = label === "REAL"
      ? `🟢 REAL — ${conf}%`
      : `🔴 DEEPFAKE — ${conf}%`;

    statusDiv.textContent = "Done.";
  };
  
  xhr.onerror = () => {
    statusDiv.textContent = "Upload failed.";
  };

  xhr.send(form);
}
