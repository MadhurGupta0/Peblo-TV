from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import PublishStatus
from app.models.season import Season
from app.models.show import Show
from app.services.publish_rules import episode_issues, show_issues


def build_validation_report(db: Session) -> dict:
    """Everything currently blocking publish, grouped by show for a non-engineer to act on.

    Only status=published rows are considered: a draft is expected to be incomplete, so
    it isn't "blocking" anything. A published row failing these checks can only happen via
    direct DB writes that bypass the API (e.g. the seed importer) — the API itself refuses
    to set status=published unless the rule already holds, so this report is really a
    guard against imported/back-doored data, not against normal editorial use.
    """
    shows = (
        db.execute(
            select(Show)
            .where(Show.status == PublishStatus.published)
            .options(selectinload(Show.seasons).selectinload(Season.episodes))
            .order_by(Show.title, Show.id)
        )
        .scalars()
        .all()
    )

    report_shows = []
    total_issues = 0

    for show in shows:
        show_level_issues = show_issues(show)
        episode_entries = []
        for season in show.seasons:
            for episode in season.episodes:
                if episode.status != PublishStatus.published:
                    continue
                issues = episode_issues(db, episode)
                if issues:
                    episode_entries.append(
                        {
                            "episode_id": episode.id,
                            "season_number": season.season_number,
                            "episode_number": episode.episode_number,
                            "title": episode.title,
                            "issues": issues,
                        }
                    )

        if not show_level_issues and not episode_entries:
            continue

        total_issues += len(show_level_issues) + sum(len(e["issues"]) for e in episode_entries)
        report_shows.append(
            {
                "show_id": show.id,
                "title": show.title,
                "slug": show.slug,
                "issues": show_level_issues,
                "episodes": episode_entries,
            }
        )

    return {"shows": report_shows, "total_blocking_issues": total_issues}
