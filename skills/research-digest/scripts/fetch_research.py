#!/usr/bin/env python3
"""
fetch_research.py — Coletor multi-fonte de papers e publicacoes.

Cobre Org Design, Workforce Planning, IA & Forca de Trabalho.
Fontes: OpenAlex, arXiv, e RSS feeds de consultorias / thought leaders.
Saida: JSON unificado e deduplicado.

Uso:
    python fetch_research.py --weeks 12 --output ./research-raw.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

# Lead capture / telemetry — best-effort, never blocks the fetch.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    import eam_client
except ImportError:
    eam_client = None

SKILL_NAME = "research-digest"
SKILL_VERSION = "1.0.0"

USER_AGENT = "Comp-ResearchDigest/1.0 (mailto:research@comp.vc)"
TIMEOUT = 30

# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------


@dataclass
class Item:
    id: str
    source: str
    source_type: str  # academic / consultancy / thoughtleader / media
    title: str
    authors: list[str]
    published_date: str  # ISO YYYY-MM-DD
    url: str
    abstract: str
    doi: str | None
    topics: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    paywall: bool = False


# ---------------------------------------------------------------------------
# Util
# ---------------------------------------------------------------------------


def _http_get(url: str, accept: str = "application/json") -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def _normalize_title(title: str) -> str:
    t = re.sub(r"[^a-z0-9 ]+", " ", title.lower())
    t = re.sub(r"\s+", " ", t).strip()
    stopwords = {"a", "the", "an", "of", "in", "on", "and", "or", "for", "to", "is", "are"}
    t = " ".join(w for w in t.split() if w not in stopwords)
    return t


def _title_hash(title: str) -> str:
    return hashlib.sha1(_normalize_title(title).encode("utf-8")).hexdigest()


def _within_window(date_str: str, cutoff: datetime) -> bool:
    if not date_str:
        return False
    try:
        d = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        try:
            d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except ValueError:
            return False
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d >= cutoff


def _safe_text(elem) -> str:
    if elem is None:
        return ""
    return (elem.text or "").strip()


# ---------------------------------------------------------------------------
# OpenAlex
# ---------------------------------------------------------------------------

OPENALEX_QUERIES = {
    "Org Design": [
        "organizational design",
        "span of control",
        "organizational structure delayering",
        "agile organization design",
    ],
    "Workforce Planning": [
        "strategic workforce planning",
        "skills based organization",
        "internal mobility talent",
        "headcount planning",
    ],
    "IA & Forca de Trabalho": [
        "generative AI workforce",
        "large language model occupation tasks",
        "AI exposure labor market",
        "automation future of work",
    ],
}


def fetch_openalex(cutoff: datetime, per_query: int = 25) -> list[Item]:
    items: list[Item] = []
    from_date = cutoff.strftime("%Y-%m-%d")
    for topic, queries in OPENALEX_QUERIES.items():
        for q in queries:
            params = {
                "search": q,
                "filter": f"from_publication_date:{from_date},type:article|preprint|book-chapter",
                "per-page": str(per_query),
                "sort": "publication_date:desc",
            }
            url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
            try:
                raw = _http_get(url)
                data = json.loads(raw)
            except Exception as e:
                print(f"[openalex] fail '{q}': {e}", file=sys.stderr)
                continue
            for w in data.get("results", []):
                doi = w.get("doi")
                title = w.get("title") or ""
                if not title:
                    continue
                pub_date = w.get("publication_date") or ""
                if not _within_window(pub_date, cutoff):
                    continue
                # Abstract is inverted index
                abstract = ""
                idx = w.get("abstract_inverted_index")
                if idx:
                    positions: dict[int, str] = {}
                    for word, locs in idx.items():
                        for loc in locs:
                            positions[loc] = word
                    abstract = " ".join(positions[i] for i in sorted(positions))
                authors = [
                    a.get("author", {}).get("display_name", "")
                    for a in w.get("authorships", [])
                    if a.get("author")
                ][:6]
                landing = (
                    w.get("primary_location", {}).get("landing_page_url")
                    or (doi if doi else "")
                    or w.get("id", "")
                )
                concepts = [c.get("display_name", "") for c in w.get("concepts", [])][:5]
                item_id = f"openalex:{w.get('id', '').split('/')[-1]}"
                items.append(
                    Item(
                        id=item_id,
                        source="OpenAlex",
                        source_type="academic",
                        title=title,
                        authors=[a for a in authors if a],
                        published_date=pub_date,
                        url=landing,
                        abstract=abstract,
                        doi=doi,
                        topics=[topic],
                        keywords=concepts,
                    )
                )
            time.sleep(0.3)
    return items


# ---------------------------------------------------------------------------
# arXiv
# ---------------------------------------------------------------------------

ARXIV_QUERIES = {
    "Org Design": [
        'all:"organizational design"',
        'all:"team topologies"',
    ],
    "Workforce Planning": [
        'all:"workforce planning"',
        'all:"skills based organization"',
    ],
    "IA & Forca de Trabalho": [
        'all:"generative AI" AND all:"workforce"',
        'all:"large language model" AND all:"occupation"',
        'all:"AI exposure" AND all:"labor"',
    ],
}

ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def fetch_arxiv(cutoff: datetime, per_query: int = 50) -> list[Item]:
    items: list[Item] = []
    for topic, queries in ARXIV_QUERIES.items():
        for q in queries:
            params = {
                "search_query": q,
                "start": "0",
                "max_results": str(per_query),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
            try:
                raw = _http_get(url, accept="application/atom+xml")
                root = ET.fromstring(raw)
            except Exception as e:
                print(f"[arxiv] fail '{q}': {e}", file=sys.stderr)
                continue
            for entry in root.findall("atom:entry", ARXIV_NS):
                pub = _safe_text(entry.find("atom:published", ARXIV_NS))[:10]
                if not _within_window(pub, cutoff):
                    continue
                title = _safe_text(entry.find("atom:title", ARXIV_NS)).replace("\n", " ")
                abstract = _safe_text(entry.find("atom:summary", ARXIV_NS)).replace("\n", " ")
                link = ""
                for l in entry.findall("atom:link", ARXIV_NS):
                    if l.attrib.get("type") == "text/html":
                        link = l.attrib.get("href", "")
                        break
                if not link:
                    link = _safe_text(entry.find("atom:id", ARXIV_NS))
                authors = [
                    _safe_text(a.find("atom:name", ARXIV_NS))
                    for a in entry.findall("atom:author", ARXIV_NS)
                ][:6]
                arxiv_id = link.rstrip("/").split("/")[-1]
                items.append(
                    Item(
                        id=f"arxiv:{arxiv_id}",
                        source="arXiv",
                        source_type="academic",
                        title=title.strip(),
                        authors=[a for a in authors if a],
                        published_date=pub,
                        url=link,
                        abstract=abstract.strip(),
                        doi=None,
                        topics=[topic],
                        keywords=[],
                    )
                )
            time.sleep(0.5)
    return items


# ---------------------------------------------------------------------------
# RSS
# ---------------------------------------------------------------------------

RSS_FEEDS: list[dict] = [
    {"name": "McKinsey Insights", "type": "consultancy", "url": "https://www.mckinsey.com/insights/rss"},
    {"name": "Deloitte Insights", "type": "consultancy", "url": "https://www2.deloitte.com/insights/us/en/feed.xml"},
    {"name": "MIT Sloan Review", "type": "media", "url": "https://sloanreview.mit.edu/feed/"},
    {"name": "Harvard Business Review", "type": "media", "url": "https://hbr.org/feed"},
    {"name": "Josh Bersin", "type": "thoughtleader", "url": "https://joshbersin.com/feed/"},
    {"name": "World Economic Forum", "type": "thoughtleader", "url": "https://www.weforum.org/agenda/rss.xml"},
    {"name": "Gartner HR", "type": "consultancy", "url": "https://www.gartner.com/en/human-resources/insights/rss"},
    {"name": "BCG Publications", "type": "consultancy", "url": "https://www.bcg.com/about/about-bcg/rss"},
]

KEYWORD_FILTER = re.compile(
    r"\b(org(anization)?\s*design|span\s+of\s+control|workforce|talent|skills|"
    r"future\s+of\s+work|generative\s+ai|llm|large\s+language|automation|"
    r"productivity|job\s+architecture|career|hr|reskill|upskill|layoff|"
    r"headcount|leveling|compensation)\b",
    re.IGNORECASE,
)


def _parse_rss_date(s: str) -> str:
    if not s:
        return ""
    # Try RFC822
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
    ):
        try:
            d = datetime.strptime(s.strip(), fmt)
            return d.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Last resort: try first 10 chars
    return s[:10]


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_rss(cutoff: datetime) -> list[Item]:
    items: list[Item] = []
    for feed in RSS_FEEDS:
        try:
            raw = _http_get(feed["url"], accept="application/rss+xml, application/xml, text/xml")
            root = ET.fromstring(raw)
        except Exception as e:
            print(f"[rss] fail {feed['name']}: {e}", file=sys.stderr)
            continue

        # RSS 2.0 or Atom
        channel = root.find("channel")
        entries = []
        if channel is not None:
            entries = channel.findall("item")
            tag_title = "title"
            tag_link = "link"
            tag_date = "pubDate"
            tag_desc = "description"
            tag_creator = "{http://purl.org/dc/elements/1.1/}creator"
        else:
            atom_ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", atom_ns)
            tag_title = "{http://www.w3.org/2005/Atom}title"
            tag_link = "{http://www.w3.org/2005/Atom}link"
            tag_date = "{http://www.w3.org/2005/Atom}published"
            tag_desc = "{http://www.w3.org/2005/Atom}summary"
            tag_creator = "{http://www.w3.org/2005/Atom}author"

        for it in entries:
            title_el = it.find(tag_title)
            title = _safe_text(title_el)
            if not title:
                continue
            link_el = it.find(tag_link)
            link = _safe_text(link_el) or (link_el.attrib.get("href", "") if link_el is not None else "")
            date_raw = _safe_text(it.find(tag_date))
            pub = _parse_rss_date(date_raw)
            if not _within_window(pub, cutoff):
                continue
            desc = _strip_html(_safe_text(it.find(tag_desc)))
            # filter by keyword to keep it relevant
            blob = f"{title} {desc}"
            if not KEYWORD_FILTER.search(blob):
                continue
            creator_el = it.find(tag_creator)
            author = _safe_text(creator_el) if creator_el is not None else ""
            topic_guess = _classify_topic(blob)
            item_id = f"rss:{hashlib.sha1(link.encode()).hexdigest()[:12]}"
            items.append(
                Item(
                    id=item_id,
                    source=feed["name"],
                    source_type=feed["type"],
                    title=title,
                    authors=[author] if author else [],
                    published_date=pub,
                    url=link,
                    abstract=desc,
                    doi=None,
                    topics=[topic_guess] if topic_guess else [],
                    keywords=[],
                )
            )
        time.sleep(0.3)
    return items


def _classify_topic(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["ai", "artificial intelligence", "llm", "generative", "automation", "machine learning"]):
        return "IA & Forca de Trabalho"
    if any(k in t for k in ["org design", "organizational design", "span of control", "delayering", "structure"]):
        return "Org Design"
    if any(k in t for k in ["workforce planning", "skills", "talent", "headcount", "mobility"]):
        return "Workforce Planning"
    return "Workforce Planning"


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------


def dedupe(items: list[Item]) -> list[Item]:
    by_doi: dict[str, Item] = {}
    by_url: dict[str, Item] = {}
    by_title: dict[str, Item] = {}
    out: list[Item] = []
    for it in items:
        if it.doi:
            doi_key = it.doi.lower().replace("https://doi.org/", "").strip()
            if doi_key in by_doi:
                _merge(by_doi[doi_key], it)
                continue
            by_doi[doi_key] = it
        url_key = (it.url or "").lower().split("?")[0].rstrip("/")
        if url_key and url_key in by_url:
            _merge(by_url[url_key], it)
            continue
        title_key = _title_hash(it.title)
        if title_key in by_title:
            _merge(by_title[title_key], it)
            continue
        by_title[title_key] = it
        if url_key:
            by_url[url_key] = it
        out.append(it)
    return out


def _merge(keep: Item, drop: Item) -> None:
    # Combine topics and keywords
    for t in drop.topics:
        if t not in keep.topics:
            keep.topics.append(t)
    for k in drop.keywords:
        if k not in keep.keywords:
            keep.keywords.append(k)
    # Prefer non-empty abstract / authors
    if not keep.abstract and drop.abstract:
        keep.abstract = drop.abstract
    if not keep.authors and drop.authors:
        keep.authors = drop.authors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weeks", type=int, default=12, help="Janela em semanas (default 12)")
    parser.add_argument(
        "--output",
        default="./research-raw.json",
        help="Caminho de saida JSON (default: ./research-raw.json)",
    )
    parser.add_argument(
        "--sources",
        default="openalex,arxiv,rss",
        help="Fontes separadas por virgula (openalex,arxiv,rss)",
    )
    args = parser.parse_args()

    if eam_client is not None:
        try:
            eam_client.on_first_run(
                skill_name=SKILL_NAME,
                skill_version=SKILL_VERSION,
                source="github",
            )
        except Exception:
            pass

    cutoff = datetime.now(timezone.utc) - timedelta(weeks=args.weeks)
    print(f"Janela: desde {cutoff.strftime('%Y-%m-%d')} ate hoje ({args.weeks} semanas)")

    sources = {s.strip() for s in args.sources.split(",")}
    collected: list[Item] = []

    if "openalex" in sources:
        print("Fetching OpenAlex ...")
        collected.extend(fetch_openalex(cutoff))
        print(f"  parcial: {len(collected)} itens")
    if "arxiv" in sources:
        print("Fetching arXiv ...")
        collected.extend(fetch_arxiv(cutoff))
        print(f"  parcial: {len(collected)} itens")
    if "rss" in sources:
        print("Fetching RSS feeds ...")
        collected.extend(fetch_rss(cutoff))
        print(f"  parcial: {len(collected)} itens")

    print(f"Total bruto: {len(collected)} itens")
    deduped = dedupe(collected)
    print(f"Apos dedup: {len(deduped)} itens")

    # Sort by date desc
    deduped.sort(key=lambda i: i.published_date, reverse=True)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_weeks": args.weeks,
        "window_start": cutoff.strftime("%Y-%m-%d"),
        "window_end": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "total_items": len(deduped),
        "items": [asdict(i) for i in deduped],
    }

    import os

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Generated: {args.output}")
    print(f"Items: {len(deduped)}")
    by_topic: dict[str, int] = {}
    for it in deduped:
        for t in it.topics or ["(sem tema)"]:
            by_topic[t] = by_topic.get(t, 0) + 1
    for t, n in sorted(by_topic.items(), key=lambda x: -x[1]):
        print(f"  {t}: {n}")

    if eam_client is not None:
        try:
            eam_client.record_run(skill_name=SKILL_NAME, skill_version=SKILL_VERSION)
        except Exception:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
