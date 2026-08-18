import { useRef, useState, type ChangeEvent, type FormEvent } from "react";

interface UploadPanelProps {
  busy: boolean;
  onUpload: (file: File) => Promise<void>;
}

export function UploadPanel({ busy, onUpload }: UploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file) return;
    await onUpload(file);
    setFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <form className="upload-panel" onSubmit={submit}>
      <div>
        <p className="eyebrow">SC2 Analyze</p>
        <h1>Study your replays with real time win prediction.</h1>
        <p className="lede">
          Upload a StarCraft II replay.
        </p>
      </div>
      <label className="file-drop">
        <input
          ref={inputRef}
          type="file"
          accept=".SC2Replay"
          onChange={selectFile}
          disabled={busy}
        />
        <span className="file-drop-icon" aria-hidden="true">
          ↑
        </span>
        <strong>{file ? file.name : "Choose a .SC2Replay file"}</strong>
        <small>{file ? "Ready to analyze" : "Up to 100 MB"}</small>
      </label>
      <button className="primary-button" type="submit" disabled={!file || busy}>
        {busy ? "Analyzing replay…" : "Analyze replay"}
      </button>
    </form>
  );
}
