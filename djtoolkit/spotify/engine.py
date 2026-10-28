"""Orchestrates scan -> match -> plan -> apply. UI-agnostic: reports via callbacks."""

from __future__ import annotations

import csv
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from ..settings import Settings, app_dir
from . import auth
from .client import RateLimitError, SpotifyClient
from .match import match_track
from .scan import scan_library
from .types import MatchResult, SyncPlan


class Cancelled(Exception):
    pass


@dataclass
class SyncSummary:
    tracks: int = 0
    matched: int = 0
    skipped: int = 0
    deferred: int = 0
    plans: list[SyncPlan] = field(default_factory=list)
    report_path: Path | None = None
    applied: bool = False
    incomplete: bool = False
    rate_limited_hours: float | None = None


def write_report(results: list[MatchResult]) -> Path | None:
    bad = [r for r in results if r.kind == "skipped"]
    if not bad:
        return None
    d = app_dir() / "reports"
    d.mkdir(exist_ok=True)
    path = d / f"unmatched-{time.strftime('%Y-%m-%d_%H-%M-%S')}.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["genre", "artist", "title", "score", "reason", "path"])
        for r in bad:
            w.writerow([r.local.genre, r.local.artist, r.local.title, r.score, r.reason, r.local.path])
    return path


def plan_genre(
    client: SpotifyClient, settings: Settings, genre: str, desired: list[str], playlists: list[dict]
) -> tuple[SyncPlan, str | None]:
    """Diff so the playlist exactly equals `desired` (mirror semantics)."""
    name = settings.playlist_name(genre)
    existing = next((p for p in playlists if p["name"] == name), None)
    want = list(dict.fromkeys(desired))
    if not existing:
        return SyncPlan(genre, name, to_add=want, is_new=True), None
    current = client.playlist_track_uris(existing["id"])
    cur_set, want_set = set(current), set(want)
    return SyncPlan(
        genre,
        name,
        to_add=[u for u in want if u not in cur_set],
        to_remove=[u for u in dict.fromkeys(current) if u not in want_set],
        keep=sum(1 for u in want if u in cur_set),
    ), existing["id"]


def apply_plan(client: SpotifyClient, plan: SyncPlan, playlist_id: str | None) -> None:
    pid = playlist_id
    if not pid:
        if not plan.to_add:
            return
        pid = client.create_playlist(plan.playlist_name)
    if plan.to_remove:
        client.remove_tracks(pid, plan.to_remove)
    if plan.to_add:
        client.add_tracks(pid, plan.to_add)


def run_sync(
    settings: Settings,
    dry_run: bool,
    log: Callable[[str], None] = print,
    progress: Callable[[int, int], None] = lambda d, t: None,
    cancelled: Callable[[], bool] = lambda: False,
    concurrency: int = 3,
) -> SyncSummary:
    summary = SyncSummary()

    def check() -> None:
        if cancelled():
            raise Cancelled()

    log("Scanning library…")
    tracks = scan_library(settings.music_root, settings.ignore_set)
    genres = list(dict.fromkeys(t.genre for t in tracks))
    summary.tracks = len(tracks)
    log(f"Found {len(tracks)} tracks across {len(genres)} genres.")
    if not tracks:
        return summary
    check()

    token = auth.get_access_token(settings, log, cancelled)
    client = SpotifyClient(token, settings.request_interval_ms, notify=log)
    limit = settings.search_limit
    client.set_search_budget(limit if limit > 0 else float("inf"))
    me = client.me()
    if limit > 0:
        log(f"Search budget: {limit} fresh lookups this run (cached tracks are free).")
    log(f"Matching against the Spotify catalog… ({client.cache_size} searches cached)")

    done = 0
    results: list[MatchResult | None] = [None] * len(tracks)

    def work(i: int) -> None:
        nonlocal done
        check()
        results[i] = match_track(client, tracks[i], settings.match_threshold)
        done += 1
        if done % 20 == 0 or done == len(tracks):
            progress(done, len(tracks))
            client.save_cache()  # checkpoint so progress survives a cancel

    try:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            for fut in [pool.submit(work, i) for i in range(len(tracks))]:
                fut.result()
    except RateLimitError as e:
        client.save_cache()
        summary.rate_limited_hours = round(e.retry_after_s / 3600, 1)
        return summary
    finally:
        client.save_cache()

    done_results = [r for r in results if r is not None]
    matched = [r for r in done_results if r.kind == "matched"]
    summary.matched = len(matched)
    summary.deferred = sum(r.kind == "deferred" for r in done_results)
    summary.skipped = len(done_results) - summary.matched - summary.deferred
    log(f"Matched {summary.matched}, skipped {summary.skipped}, deferred {summary.deferred}.")
    summary.report_path = write_report(done_results)
    if summary.report_path:
        log(f"Unmatched report: {summary.report_path}")

    # SAFETY: with deferred tracks, mirror mode would treat not-yet-matched tracks as removed.
    if summary.deferred:
        summary.incomplete = True
        log(
            f"Matching is incomplete: {summary.deferred} track(s) not yet looked up (daily quota). "
            "Progress is cached. Re-run later; sync is skipped until matching finishes."
        )
        return summary

    by_genre: dict[str, list[str]] = {}
    for m in matched:
        by_genre.setdefault(m.local.genre, []).append(m.track.uri)  # type: ignore[union-attr]

    check()
    playlists = client.list_my_playlists(me["id"])
    for genre in genres:
        check()
        plan, pid = plan_genre(client, settings, genre, by_genre.get(genre, []), playlists)
        summary.plans.append(plan)
        tag = " (new)" if plan.is_new else ""
        log(f"{plan.playlist_name}{tag}: +{len(plan.to_add)} -{len(plan.to_remove)} ={plan.keep}")
        if not dry_run:
            apply_plan(client, plan, pid)
    summary.applied = not dry_run
    log("Dry run complete. No changes made." if dry_run else "Sync complete.")
    return summary


def import_legacy_cache(src: Path) -> int:
    """Copy the old spotify-genre-sync search cache so existing lookups aren't repeated."""
    import json

    dest = app_dir() / "search-cache.json"
    new = json.loads(src.read_text("utf8"))
    try:
        merged = json.loads(dest.read_text("utf8"))
    except (OSError, ValueError):
        merged = {}
    before = len(merged)
    merged.update({k: v for k, v in new.items() if k not in merged})
    dest.write_text(json.dumps(merged), "utf8")
    return len(merged) - before
