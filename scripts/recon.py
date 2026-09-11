"""Throwaway recon script: profile _given/seed_shows.json against _given/reference.json.

Run: python scripts/recon.py
Prints a report; findings are copied into docs/DATA_FINDINGS.md by hand.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GIVEN = ROOT / "_given"


def load():
    reference = json.loads((GIVEN / "reference.json").read_text(encoding="utf-8"))
    episodes = json.loads((GIVEN / "seed_shows.json").read_text(encoding="utf-8"))
    return reference, episodes


def section(title: str) -> None:
    print(f"\n{'=' * 8} {title} {'=' * 8}")


def main() -> None:
    reference, episodes = load()
    allowed_sections = set(reference["sections"])
    allowed_categories = set(reference["categories"])
    allowed_languages = set(reference["languages"])

    section("Basic counts")
    shows = {e["slug"]: e["show_title"] for e in episodes}
    print(f"episode rows: {len(episodes)}")
    print(f"distinct shows: {len(shows)}")
    seasons = {(e["slug"], e["season_number"]) for e in episodes}
    print(f"distinct (show, season) pairs: {len(seasons)}")
    per_show = Counter(e["slug"] for e in episodes)
    for slug, n in per_show.most_common():
        print(f"  {slug}: {n} rows")

    section("Enum values not in reference.json")
    bad_sections = {e["episode_id"]: e["section"] for e in episodes if e["section"] not in allowed_sections and e["section"] is not None}
    null_sections = [e["episode_id"] for e in episodes if e["section"] is None]
    print(f"invalid section values: {bad_sections}")
    print(f"null sections: {null_sections}")

    bad_categories = defaultdict(list)
    for e in episodes:
        for c in e["categories"]:
            if c not in allowed_categories:
                bad_categories[c].append(e["episode_id"])
    print(f"invalid categories: {dict(bad_categories)}")

    bad_languages = {e["episode_id"]: e["language"] for e in episodes if e["language"] not in allowed_languages}
    print(f"invalid languages: {bad_languages}")

    section("Missing / null / zero duration")
    bad_duration = [e["episode_id"] for e in episodes if not e.get("duration_seconds")]
    print(f"missing/zero duration: {bad_duration}")

    section("Missing synopsis / title / artwork")
    no_synopsis = [e["episode_id"] for e in episodes if not e.get("synopsis")]
    no_title = [e["episode_id"] for e in episodes if not e.get("episode_title")]
    no_artwork = [e["episode_id"] for e in episodes if not e.get("artwork_available")]
    print(f"no synopsis: {no_synopsis}")
    print(f"no episode_title: {no_title}")
    print(f"no artwork_available (empty list) — published episodes among these are a publish blocker:")
    for eid in no_artwork:
        e = next(x for x in episodes if x["episode_id"] == eid)
        print(f"  {eid}  status={e['status']}  show={e['show_title']}  S{e['season_number']}E{e['episode_number']}")

    section("Duplicate (content_group, language) pairs — UNIQUE constraint trap")
    pair_counter = Counter((e["content_group"], e["language"]) for e in episodes)
    dupes = {k: v for k, v in pair_counter.items() if v > 1}
    for (cg, lang), count in dupes.items():
        ids = [e["episode_id"] for e in episodes if e["content_group"] == cg and e["language"] == lang]
        print(f"  content_group={cg!r} language={lang!r} appears {count}x -> {ids}")

    section("content_group variants where published state differs")
    by_cg = defaultdict(list)
    for e in episodes:
        by_cg[e["content_group"]].append(e)
    for cg, rows in by_cg.items():
        statuses = {r["status"] for r in rows}
        if len(statuses) > 1:
            print(f"  {cg}: statuses={statuses} -> {[(r['episode_id'], r['language'], r['status']) for r in rows]}")

    section("content_group spanning different shows/seasons (should be impossible)")
    for cg, rows in by_cg.items():
        shows_ = {r["slug"] for r in rows}
        seasons_ = {r["season_number"] for r in rows}
        if len(shows_) > 1 or len(seasons_) > 1:
            print(f"  {cg}: shows={shows_} seasons={seasons_}")

    section("Season 0 rows (trailers convention)")
    s0 = [e for e in episodes if e["season_number"] == 0]
    for e in s0:
        print(f"  {e['episode_id']}  show={e['show_title']}  title={e['episode_title']!r}  artwork={e['artwork_available']}")
    shows_with_s0 = {e["slug"] for e in s0}
    shows_without_real_season = {slug for slug in shows_with_s0 if not any(e["slug"] == slug and e["season_number"] > 0 for e in episodes)}
    print(f"shows with Season 0 but no real season: {shows_without_real_season}")

    section("Episode numbering gaps / duplicates within (show, season, language)")
    by_show_season_lang = defaultdict(list)
    for e in episodes:
        by_show_season_lang[(e["slug"], e["season_number"], e["language"])].append(e["episode_number"])
    for (slug, season_num, lang), nums in by_show_season_lang.items():
        counts = Counter(nums)
        dup_nums = {n: c for n, c in counts.items() if c > 1}
        if dup_nums:
            print(f"  {slug} S{season_num} [{lang}]: duplicate episode_number(s) {dup_nums}")
        expected = set(range(1, max(nums) + 1)) if season_num > 0 and nums else set()
        missing = expected - set(nums)
        if missing:
            print(f"  {slug} S{season_num} [{lang}]: missing episode_number(s) {sorted(missing)}")

    section("Shows/episodes marked published with no section")
    pub_no_section = [e["episode_id"] for e in episodes if e["status"] == "published" and e["section"] is None]
    print(f"published episodes with null section: {pub_no_section}")

    section("Whitespace / casing inconsistencies in titles")
    seen = defaultdict(set)
    for e in episodes:
        seen[e["episode_title"].strip().lower()].add(e["episode_title"])
    for norm, variants in seen.items():
        if len(variants) > 1:
            print(f"  {norm!r} has casing/spacing variants: {variants}")

    section("Shows and their computed status (derived from episode statuses)")
    by_show = defaultdict(list)
    for e in episodes:
        by_show[e["slug"]].append(e)
    for slug, rows in by_show.items():
        statuses = Counter(r["status"] for r in rows)
        print(f"  {slug}: {dict(statuses)}  section={rows[0]['section']!r}")


if __name__ == "__main__":
    main()
