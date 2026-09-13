import { useState } from "react";

/**
 * Drag-and-drop (or click-to-browse) PDF picker. Selecting a file no longer uploads it
 * immediately — it just stages the file so the title/phase can be reviewed or edited,
 * and the actual upload only happens when "Upload book" is clicked.
 */
function UploadZone({ onUploaded }) {
  const [file, setFile] = useState(null);
  const [title, setTitle] = useState("");
  const [phase, setPhase] = useState("");
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");

  function stage(candidate) {
    if (!candidate) return;
    if (candidate.type !== "application/pdf" && !candidate.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }
    setError("");
    setFile(candidate);
    setTitle((current) => current || candidate.name.replace(/\.pdf$/i, ""));
  }

  function clear() {
    setFile(null);
    setTitle("");
    setPhase("");
    setError("");
  }

  async function submit() {
    if (!file || busy) return;
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
      clear();
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
        stage(event.dataTransfer.files[0]);
      }}
    >
      {file ? (
        <p className="staged-file">
          📄 {file.name}
          <button type="button" className="link-button" onClick={clear} disabled={busy}>
            change
          </button>
        </p>
      ) : (
        <label className="dropzone">
          Drop a PDF here or click to browse
          <input type="file" accept="application/pdf" hidden onChange={(event) => stage(event.target.files[0])} />
        </label>
      )}
      <input placeholder="Book title" value={title} onChange={(event) => setTitle(event.target.value)} disabled={busy} />
      <input placeholder="Phase (optional)" value={phase} onChange={(event) => setPhase(event.target.value)} disabled={busy} />
      <button type="button" onClick={submit} disabled={!file || busy}>
        {busy ? "Uploading…" : "Upload book"}
      </button>
      {error && <p className="upload-error">{error}</p>}
    </div>
  );
}

export default UploadZone;
