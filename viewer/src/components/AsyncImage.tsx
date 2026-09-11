import { useState } from "react";

type AsyncImageProps = {
  src?: string | null;
  alt: string;
  ratio: "banner" | "poster" | "thumb";
  className?: string;
};

export function AsyncImage({ src, alt, ratio, className }: AsyncImageProps) {
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");

  return (
    <div className={`media-shell media-${ratio} ${className ?? ""} ${status === "ready" ? "is-ready" : ""}`.trim()}>
      {src ? (
        <img
          src={src}
          alt={alt}
          loading="lazy"
          decoding="async"
          onLoad={() => setStatus("ready")}
          onError={() => setStatus("error")}
        />
      ) : null}
      {status !== "ready" ? (
        <div className="media-fallback" aria-hidden={status !== "error"}>
          <span>{status === "error" ? "Artwork unavailable" : "Loading artwork"}</span>
        </div>
      ) : null}
    </div>
  );
}