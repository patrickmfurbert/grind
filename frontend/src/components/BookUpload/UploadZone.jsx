import { useState } from "react";

/** Drag-and-drop (or click-to-browse) PDF upload zone; posts multipart form data to /books/upload. */
function UploadZone({ onUploaded }) {
  const [title, setTitle] = useState("");
  const [phase, setPhase] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");

  async function upload(file) {
    if (!file || busy) return;
    if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("title", title || file.name);
      if (phase) form.append("phase", phase);
      const response = await fetch("/api/books/upload", { method: "POST", body: form });
      if (!response.ok) {
        const detail = await response.text();
        throw new Error(`Upload failed (${response.status}): ${detail || response.statusText}`);
      }
      onUploaded(await response.json());
      setTitle("");
    } catch (err) {
      setError(err.message || "Upload failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className={`upload-zone ${dragging ? "dragging" : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        upload(event.dataTransfer.files[0]);
      }}
    >
      <input placeholder="Book title" value={title} onChange={(event) => setTitle(event.target.value)} />
      <input placeholder="Phase (optional)" value={phase} onChange={(event) => setPhase(event.target.value)} />
      <label className="dropzone">
        {busy ? "Uploading…" : "Drop a PDF here or click to browse"}
        <input type="file" accept="application/pdf" hidden onChange={(event) => upload(event.target.files[0])} />
      </label>
      {error && <p className="upload-error">{error}</p>}
    </div>
  );
}

export default UploadZone;
