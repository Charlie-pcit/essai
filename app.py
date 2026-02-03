#!/usr/bin/env python3
import datetime as dt
import json
import math
import re
import textwrap
from collections import Counter
from pathlib import Path
from typing import Iterable, List, Dict

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

CONFIG_PATH = Path("config.json")
OUTPUT_DIR = Path(".")

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
WORD_RE = re.compile(r"[\w\-]+", re.UNICODE)


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def is_weekday(date: dt.date) -> bool:
    return date.weekday() < 5


def parse_published(entry) -> dt.datetime | None:
    if getattr(entry, "published", None):
        return date_parser.parse(entry.published)
    if getattr(entry, "updated", None):
        return date_parser.parse(entry.updated)
    return None


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def extract_article_text(url: str, timeout: int = 10) -> str:
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    paragraphs = [clean_text(p.get_text(" ")) for p in soup.find_all("p")]
    return " ".join(p for p in paragraphs if p)


def score_text(text: str, keywords: Iterable[str]) -> int:
    text_lower = text.lower()
    score = 0
    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower in text_lower:
            score += 3
    return score


def summarize(text: str, keywords: Iterable[str], max_sentences: int = 3) -> str:
    sentences = [s.strip() for s in SENTENCE_SPLIT.split(text) if s.strip()]
    if not sentences:
        return "Résumé indisponible."

    keyword_counts = Counter()
    for keyword in keywords:
        keyword_counts[keyword.lower()] += 1

    scored = []
    for sentence in sentences:
        words = WORD_RE.findall(sentence.lower())
        if not words:
            continue
        keyword_score = sum(1 for word in words for key in keyword_counts if key in word)
        length_penalty = 1 / math.sqrt(len(words))
        scored.append((keyword_score * length_penalty, sentence))

    scored.sort(reverse=True, key=lambda item: item[0])
    top_sentences = [sentence for _, sentence in scored[:max_sentences]]

    if not top_sentences:
        return sentences[0]
    return " ".join(top_sentences)


def gather_entries(config: dict) -> List[Dict]:
    now = dt.datetime.now(dt.timezone.utc)
    lookback = now - dt.timedelta(hours=config["lookback_hours"])
    keywords = config["keywords"]
    entries: List[Dict] = []

    for feed in config["feeds"]:
        parsed = feedparser.parse(feed["url"])
        for entry in parsed.entries:
            published = parse_published(entry)
            if not published:
                continue
            published = published.astimezone(dt.timezone.utc)
            if published < lookback:
                continue

            content = ""
            if getattr(entry, "summary", None):
                content = entry.summary
            elif getattr(entry, "content", None):
                content = entry.content[0].value

            content = clean_text(content)
            if not content:
                content = extract_article_text(entry.link)

            score = score_text(f"{entry.title} {content}", keywords)
            entries.append(
                {
                    "title": entry.title,
                    "link": entry.link,
                    "published": published,
                    "summary": summarize(content, keywords),
                    "score": score,
                    "source": feed["name"],
                }
            )

    entries.sort(key=lambda item: (item["score"], item["published"]), reverse=True)
    return entries


def format_report(entries: List[Dict], config: dict) -> str:
    today = dt.date.today()
    header = f"# Veille IA & Automatisation - {today.isoformat()}\n"
    lines = [header, "\n"]

    max_items = config["max_items"]
    min_items = config["min_items"]
    selected = entries[:max_items]
    if len(selected) < min_items:
        selected = entries

    if not selected:
        return header + "\nAucun article pertinent trouvé.\n"

    for idx, entry in enumerate(selected, start=1):
        lines.append(f"## {idx}. {entry['title']}\n")
        lines.append(f"- Source: {entry['source']}\n")
        lines.append(f"- Date: {entry['published'].date().isoformat()}\n")
        lines.append(f"- Lien: {entry['link']}\n")
        wrapped = "\n".join(textwrap.wrap(entry["summary"], width=88))
        lines.append(f"- Résumé: {wrapped}\n\n")

    return "".join(lines)


def main() -> None:
    config = load_config(CONFIG_PATH)
    today = dt.date.today()
    if not is_weekday(today):
        print("Ce script est prévu pour une exécution en semaine (lundi-vendredi).")
        return

    entries = gather_entries(config)
    report = format_report(entries, config)
    output_path = OUTPUT_DIR / f"veille-{today.isoformat()}.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"Rapport généré: {output_path}")


if __name__ == "__main__":
    main()
