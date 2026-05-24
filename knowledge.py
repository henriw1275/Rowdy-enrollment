"""Lightweight catalog retrieval for "Rowdy, Your Crowder Guide".

The 2026-27 Crowder catalog is ~206 pages / ~135k tokens — far too big to
attach to every Claude call. Instead we keep it as plain text in
data/catalog.txt, split it into per-page chunks at load time, and pull only
the handful of pages most relevant to each student question.

This is deliberately simple: pure-Python keyword scoring, no embeddings, no
vector DB, no extra services to run on Railway. It won't match a real
semantic search, but for "find the Nursing pages" / "find the Welding
requirements" it does the job and costs nothing to operate.

If you later want better recall, the upgrade path is to swap `retrieve()`'s
scoring for an embedding similarity search — the rest of the app doesn't
need to change.
"""
from __future__ import annotations

import re
from pathlib import Path

CATALOG_PATH = Path(__file__).parent / "data" / "catalog.txt"

# Very small stopword list — just the words common enough to add noise to
# keyword overlap scoring without helping pick the right page.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "of", "to", "in", "on", "for",
    "with", "at", "by", "from", "about", "as", "is", "are", "was", "were", "be",
    "been", "do", "does", "did", "can", "could", "would", "should", "i", "you",
    "me", "my", "we", "our", "it", "this", "that", "these", "those", "what",
    "how", "when", "where", "which", "who", "want", "need", "get", "got",
    "tell", "help", "know", "like", "into", "out", "up", "so", "some", "any",
}

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS and len(w) > 2]


class CatalogIndex:
    """Holds the catalog split into pages and scores them against a query."""

    def __init__(self, path: Path = CATALOG_PATH):
        self.pages: list[str] = []
        self._page_tokens: list[set[str]] = []
        self._load(path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            # App still runs without the catalog; retrieval just returns nothing.
            return
        raw = path.read_text(encoding="utf-8", errors="ignore")
        # pdftotext separates pages with form feeds (\f).
        pages = [p.strip() for p in raw.split("\f")]
        self.pages = [p for p in pages if len(p) > 40]  # drop near-empty pages
        self._page_tokens = [set(_tokenize(p)) for p in self.pages]

    def retrieve(self, query: str, k: int = 4, max_chars: int = 9000) -> str:
        """Return the top-k most relevant catalog pages as one text block.

        Scoring: number of distinct query terms that appear on the page, with
        a small bonus for how often they appear. Returns "" when nothing
        meaningfully matches, so the caller can simply skip injection.
        """
        if not self.pages:
            return ""

        q_terms = set(_tokenize(query))
        if not q_terms:
            return ""

        scored: list[tuple[float, int]] = []
        for idx, page_tokens in enumerate(self._page_tokens):
            overlap = q_terms & page_tokens
            if not overlap:
                continue
            page_lower = self.pages[idx].lower()
            # distinct-term overlap is the main signal; frequency is a tiebreaker
            freq = sum(page_lower.count(term) for term in overlap)
            score = len(overlap) * 10 + min(freq, 20)
            scored.append((score, idx))

        if not scored:
            return ""

        scored.sort(reverse=True)
        chosen: list[str] = []
        total = 0
        for _score, idx in scored[:k]:
            page = self.pages[idx]
            if total + len(page) > max_chars and chosen:
                break
            chosen.append(page)
            total += len(page)

        return "\n\n--- (catalog page break) ---\n\n".join(chosen)


# Build the index once at import time.
catalog = CatalogIndex()


def retrieve_catalog(query: str, k: int = 4) -> str:
    """Module-level convenience wrapper used by claude_service."""
    return catalog.retrieve(query, k=k)
