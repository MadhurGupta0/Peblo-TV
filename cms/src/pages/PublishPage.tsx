import { useState } from "react";

import { apiUrl } from "../api/client";
import { isApiError } from "../api/artwork";
import { usePublish, usePublishRuns, useValidationReport } from "../api/publish";
import { useAuth } from "../auth/AuthContext";
import { Pagination } from "../components/Pagination";
import { EmptyState, ErrorState, LoadingState, PermissionDenied } from "../components/States";
import { useToast } from "../components/Toast";

export function PublishPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const { showToast } = useToast();

  const report = useValidationReport();
  const [historyPage, setHistoryPage] = useState(1);
  const history = usePublishRuns(historyPage);
  const publish = usePublish();

  const blockingCount = report.data?.total_blocking_issues ?? 0;
  const canPublish = isAdmin && blockingCount === 0 && !publish.isPending;
  const blockingReasons = collectBlockingReasons(report.data);
  const latestSuccessfulRun = history.data?.items.find((run) => run.status === "success" && run.catalogue_key);

  function handlePublish() {
    if (!window.confirm("Publish the catalogue now? This makes the current published content live.")) return;
    publish.mutate(undefined, {
      onSuccess: (run) => showToast("success", `Publish succeeded (run #${run.run_id}).`),
      onError: (err) => showToast("error", isApiError(err) ? err.message : "Publish failed."),
    });
  }

  return (
    <div>
      <div className="page-header">
        <h1>Publish</h1>
      </div>

      {!isAdmin && <PermissionDenied message="You need admin access to publish. You can still review what's blocking it below." />}

      <section className="publish-action">
        <button type="button" disabled={!canPublish} onClick={handlePublish}>
          {publish.isPending ? "Publishing…" : "Publish catalogue"}
        </button>
        {isAdmin && blockingCount > 0 && (
          <div className="publish-blockers" role="status" aria-live="polite">
            <p className="hint">
              Publish is disabled: {blockingCount} blocking issue{blockingCount === 1 ? "" : "s"} must be fixed first.
            </p>
            <ul className="issue-list">
              {blockingReasons.map((reason, index) => (
                <li key={`${reason}-${index}`}>{reason}</li>
              ))}
            </ul>
          </div>
        )}
        {latestSuccessfulRun?.catalogue_key && (
          <p className="hint">
            Latest published catalogue:{" "}
            <a href={apiUrl(`/catalog`)} target="_blank" rel="noreferrer">
              run #{latestSuccessfulRun.run_id}
            </a>
          </p>
        )}
      </section>

      <section>
        <h2>Validation report</h2>
        {report.isLoading && <LoadingState label="Loading validation report…" />}
        {report.isError && (
          <ErrorState
            message={isApiError(report.error) ? report.error.message : "Failed to load validation report."}
            onRetry={() => report.refetch()}
          />
        )}
        {report.data && report.data.shows.length === 0 && <EmptyState message="Nothing is blocking publish right now." />}
        {report.data?.shows.map((show) => (
          <div key={show.show_id} className="report-show">
            <h3>{show.title}</h3>
            {show.issues.length > 0 && (
              <ul className="issue-list">
                {show.issues.map((issue, i) => (
                  <li key={i}>{issue.message}</li>
                ))}
              </ul>
            )}
            {show.episodes.length > 0 && (
              <ul className="issue-list">
                {show.episodes.map((ep) => (
                  <li key={ep.episode_id}>
                    Season {ep.season_number}, Episode {ep.episode_number} ("{ep.title}"):{" "}
                    {ep.issues.map((issue) => issue.message).join(" ")}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </section>

      <section>
        <h2>Run history</h2>
        {history.isLoading && <LoadingState label="Loading run history…" />}
        {history.isError && (
          <ErrorState
            message={isApiError(history.error) ? history.error.message : "Failed to load run history."}
            onRetry={() => history.refetch()}
          />
        )}
        {history.data && history.data.items.length === 0 && <EmptyState message="No publishes yet." />}
        {history.data && history.data.items.length > 0 && (
          <>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Who</th>
                  <th>When</th>
                  <th>Outcome</th>
                  <th>Counts</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody>
                {history.data.items.map((run) => (
                  <tr key={run.run_id}>
                    <td>#{run.run_id}</td>
                    <td>{run.actor_email ?? <em>unknown</em>}</td>
                    <td>{new Date(run.started_at).toLocaleString()}</td>
                    <td>
                      <span className={`status-badge status-run-${run.status}`}>{run.status}</span>
                      {run.error && <div className="hint">{run.error}</div>}
                    </td>
                    <td>
                      {run.counts.shows ?? 0} shows / {run.counts.episodes ?? 0} episodes
                      {run.catalogue_key && (
                        <div>
                          <a href={apiUrl(`/catalog`)} target="_blank" rel="noreferrer">
                            Open latest catalogue
                          </a>
                        </div>
                      )}
                    </td>
                    <td>{run.duration_seconds !== null ? `${run.duration_seconds.toFixed(1)}s` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination
              page={history.data.page}
              pageSize={history.data.page_size}
              total={history.data.total}
              onPageChange={setHistoryPage}
            />
          </>
        )}
      </section>
    </div>
  );
}

function collectBlockingReasons(report: ReturnType<typeof useValidationReport>["data"]): string[] {
  if (!report) return [];

  return report.shows.flatMap((show) => {
    const showIssues = show.issues.map((issue) => `${show.title}: ${issue.message}`);
    const episodeIssues = show.episodes.flatMap((episode) =>
      episode.issues.map(
        (issue) =>
          `${show.title} — Season ${episode.season_number}, Episode ${episode.episode_number} ("${episode.title}"): ${issue.message}`,
      ),
    );
    return [...showIssues, ...episodeIssues];
  });
}
