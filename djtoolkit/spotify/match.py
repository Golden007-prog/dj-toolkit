"""Match local tracks to the Spotify catalog with a confidence score.

Ported from the TypeScript original (src/match.ts); tune normalize()/score() here.
"""

from __future__ import annotations

import re
from collections import Counter

from .client import BudgetExhaustedError, RateLimitError, SpotifyClient
from .types import LocalTrack, MatchResult, SpotifyTrack


def normalize(s: str) -> str:
    """Lowercase; strip feat., Beatport-style country codes and bare version labels;
    unparenthesize the rest so '(Alan Dixon Remix)' stays as 'alan dixon remix'."""
    s = s.lower()
    s = re.sub(r"\(feat\.?[^)]*\)|\bfeat\.?\b.*$|\bft\.?\b.*$", "", s)
    s = re.sub(r"\([a-z]{2,5}\)", "", s)
    s = re.sub(r"\((extended|original|radio)\s*(mix|version|edit)?\s*\)", "", s)
    s = re.sub(r"-\s*(extended|original|radio)\s*(mix|version|edit)?\s*$", "", s)
    s = re.sub(r"[()\[\]]", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return s.strip()


def query_title(title: str) -> str:
    """Title for Spotify queries: drop feat. and bare version suffixes, keep remix names."""
    c = re.sub(r"\s*\(feat\.?[^)]*\)", "", title, flags=re.I)
    c = re.sub(r"\bfeat\.?\s+\S[^(\[,]*", "", c, flags=re.I)
    c = re.sub(r"\s*\((extended|original|radio)\s*(mix|version|edit)?\s*\)", "", c, flags=re.I)
    c = re.sub(r"\s*-\s*(extended|original|radio)\s*(mix|version|edit)?\s*$", "", c, flags=re.I)
    c = c.strip()
    return c or title


def query_artist(artist: str) -> str:
    """First artist only, with Beatport-style (BR)/(Aus) suffixes stripped."""
    first = artist.split(",")[0].strip()
    return re.sub(r"\s+", " ", re.sub(r"\s*\([A-Za-z]{2,5}\)\s*", " ", first)).strip()


def dice(a: str, b: str) -> float:
    """Sørensen–Dice coefficient over character bigrams, on normalized strings."""
    na, nb = normalize(a), normalize(b)
    if na == nb:
        return 1.0
    if len(na) < 2 or len(nb) < 2:
        return 0.0
    ma = Counter(na[i : i + 2] for i in range(len(na) - 1))
    mb = Counter(nb[i : i + 2] for i in range(len(nb) - 1))
    overlap = sum(min(c, mb.get(g, 0)) for g, c in ma.items())
    return 2 * overlap / ((len(na) - 1) + (len(nb) - 1))


def score(local: LocalTrack, cand: SpotifyTrack) -> float:
    """60 % title + 40 % best pairwise artist match (comma-separated artists compared individually)."""
    title_score = dice(local.title, cand.name)
    if not local.artist:
        artist_score = 0.5
    else:
        artist_score = 0.0
        for la in (a.strip() for a in local.artist.split(",")):
            for sa in cand.artists:
                artist_score = max(artist_score, dice(la, sa))
    return 0.6 * title_score + 0.4 * artist_score


def match_track(client: SpotifyClient, local: LocalTrack, threshold: float) -> MatchResult:
    qt = query_title(local.title)
    qa = query_artist(local.artist) if local.artist else ""

    old_format = f"track:{local.title} artist:{local.artist}" if local.artist else f"track:{local.title}"
    cache_formats = [f"track:{qt} artist:{qa}", old_format, f"{qt} {qa}", qt] if qa else [f"track:{qt}", old_format, qt]

    # Phase 1: cache only, no budget used. Also checks the old query format so
    # caches from earlier versions keep working.
    candidates: list[SpotifyTrack] = []
    for q in cache_formats:
        hit = client.peek_cache(q)
        if hit:
            candidates = hit
            break

    # Phase 2: fresh API queries only if the cache had nothing usable.
    if not candidates:
        api_queries = [f"track:{qt} artist:{qa}", f"{qt} {qa}", qt] if qa else [f"track:{qt}", qt]
        for q in api_queries:
            try:
                candidates = client.search_track(q)
            except RateLimitError:
                raise
            except BudgetExhaustedError:
                return MatchResult("deferred", local)
            except Exception as e:  # noqa: BLE001 - report and move on
                return MatchResult("skipped", local, reason=f"search error: {e}")
            if candidates:
                break

    if not candidates:
        return MatchResult("skipped", local, reason="no search results")

    best = max(candidates, key=lambda c: score(local, c))
    best_score = score(local, best)
    if best_score >= threshold:
        return MatchResult("matched", local, best, round(best_score, 3))
    return MatchResult(
        "skipped",
        local,
        score=round(best_score, 3),
        reason=f"low confidence (best: {', '.join(best.artists)} - {best.name})",
    )
