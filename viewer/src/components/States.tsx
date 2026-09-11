export function LoadingState({ label = "Loading" }: { label?: string }) {
  return <div className="viewer-state">{label}…</div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="viewer-state viewer-state-error">
      <p>{message}</p>
      {onRetry ? <button onClick={onRetry}>Try again</button> : null}
    </div>
  );
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="viewer-state viewer-state-empty">
      <h2>{title}</h2>
      <p>{detail}</p>
    </div>
  );
}