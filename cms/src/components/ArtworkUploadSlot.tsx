import { useId, useRef, useState } from "react";

import { isApiError, useUploadArtwork } from "../api/artwork";
import { useToast } from "./Toast";

interface ArtworkUploadSlotProps {
  kind: "poster" | "banner" | "thumbnail";
  ownerType: "show" | "episode";
  ownerId: number;
  label: string;
  requiredDims: string;
  maxKb: number;
  currentUrl?: string | null;
}

export function ArtworkUploadSlot({ kind, ownerType, ownerId, label, requiredDims, maxKb, currentUrl }: ArtworkUploadSlotProps) {
  const inputId = useId();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const upload = useUploadArtwork();
  const { showToast } = useToast();

  const displayUrl = preview ?? currentUrl ?? null;

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setErrorMessage(null);
    setPreview(URL.createObjectURL(file)); // client-side preview only — the server is the authority

    // Courtesy pre-check so an editor doesn't wait for a round trip on an obviously oversized file.
    if (file.size > maxKb * 1024) {
      setErrorMessage(`This file is ${Math.round(file.size / 1024)} KB, over the ${maxKb} KB limit. Pick a smaller file.`);
      return;
    }

    upload.mutate(
      { file, kind, ownerType, ownerId },
      {
        onSuccess: () => {
          showToast("success", `${label} uploaded.`);
        },
        onError: (err) => {
          const message = isApiError(err) ? err.message : "Upload failed. Please try again.";
          setErrorMessage(message);
          setPreview(null);
        },
      },
    );
  }

  return (
    <div className="artwork-slot">
      <label htmlFor={inputId} className="artwork-slot-label">
        {label} — {requiredDims}, max {maxKb} KB
      </label>
      <div className="artwork-slot-body">
        {displayUrl ? (
          <img src={displayUrl} alt={`${label} preview`} className={`artwork-preview artwork-preview-${kind}`} />
        ) : (
          <div className={`artwork-preview artwork-preview-${kind} artwork-preview-empty`}>No {label.toLowerCase()} yet</div>
        )}
        <input
          id={inputId}
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png"
          onChange={handleFileChange}
          disabled={upload.isPending}
        />
        {upload.isPending && <span className="artwork-slot-status">Uploading…</span>}
        {errorMessage && (
          <p className="field-error" role="alert">
            {errorMessage}
          </p>
        )}
      </div>
    </div>
  );
}
