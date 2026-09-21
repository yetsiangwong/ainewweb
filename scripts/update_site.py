import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "news.json"

FEEDS = [
    ("Google News: global AI", "https://news.google.com/rss/search?q=artificial%20intelligence%20OR%20AI%20when%3A1d&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: frontier labs", "https://news.google.com/rss/search?q=OpenAI%20OR%20Anthropic%20OR%20Google%20DeepMind%20OR%20Meta%20AI%20OR%20xAI%20when%3A1d&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: AI policy", "https://news.google.com/rss/search?q=AI%20regulation%20OR%20AI%20policy%20OR%20AI%20copyright%20when%3A1d&hl=en-US&gl=US&ceid=US:en"),
    ("Google News: AI funding", "https://news.google.com/rss/search?q=AI%20startup%20funding%20OR%20AI%20data%20center%20OR%20AI%20chips%20when%3A1d&hl=en-US&gl=US&ceid=US:en"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ("arXiv cs.AI", "https://export.arxiv.org/rss/cs.AI"),
    ("arXiv cs.CL", "https://export.arxiv.org/rss/cs.CL"),
]

CATEGORY_RULES = [
    ("Policy & Regulation", ["regulation", "policy", "government", "senate", "white house", "law", "copyright", "court", "lawsuit", "eu ai act"]),
    ("Models & Products", ["model", "gpt", "claude", "gemini", "llama", "grok", "release", "launch", "agent", "chatbot"]),
    ("Research & Open Source", ["research", "paper", "arxiv", "open source", "benchmark", "dataset", "github"]),
    ("Industry & Funding", ["funding", "startup", "raise", "investment", "data center", "chip", "nvidia", "cloud", "revenue"]),
    ("Risk, Safety & Copyright", ["safety", "risk", "misuse", "deepfake", "privacy", "security", "copyright", "harm"]),
]

WHY_BY_CATEGORY = {
    "Policy & Regulation": "Policy choices can quickly change compliance duties, product release plans and cross-border AI deployment.",
    "Models & Products": "Model and product releases shape the competitive baseline for developers, enterprises and everyday AI users.",
    "Research & Open Source": "Research and open-source work often signals where the next product wave or safety debate will move.",
    "Industry & Funding": "Funding and infrastructure moves reveal where companies expect real AI demand and return on investment.",
    "Risk, Safety & Copyright": "Safety, privacy and copyright issues define what AI systems can responsibly do at scale.",
    "AI Companies": "Company strategy affects the products, pricing and platform choices available to the market.",
}

TRUSTED_HINTS = [
    "reuters",
    "associated press",
    "ap news",
    "wall street journal",
    "wsj",
    "financial times",
    "ft.com",
    "bloomberg",
    "the guardian",
    "axios",
    "techcrunch",
    "the verge",
    "mit technology review",
    "venturebeat",
    "anthropic",
    "openai",
    "google",
    "microsoft",
    "meta",
    "nvidia",
    "arxiv",
]

LOW_TRUST_HINTS = [
    "newsbytes",
    "eastern herald",
    "et now",
    "wowt",
    "news mobile",
    "et enterprise ai",
]


def fetch(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ai-signal-daily-site/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read()


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    value = value.replace("\ufffd", "")
    return re.sub(r"\s+", " ", value).strip()


def child_text(node: ET.Element, names: list[str]) -> str:
    for child in list(node):
        short = child.tag.split("}")[-1]
        if short in names and child.text:
            return child.text.strip()
    found = node.find(names[0])
    return found.text.strip() if found is not None and found.text else ""


def item_link(node: ET.Element) -> str:
    direct = child_text(node, ["link"])
    if direct:
        return direct
    for child in list(node):
        short = child.tag.split("}")[-1]
        if short == "link" and child.attrib.get("href"):
            return child.attrib["href"]
    return ""


def parse_date(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except (TypeError, ValueError):
        pass
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    except ValueError:
        return None


def parse_feed(source: str, url: str) -> list[dict]:
    try:
        root = ET.fromstring(fetch(url))
    except Exception as exc:
        print(f"warn: could not read {source}: {exc}", file=sys.stderr)
        return []

    nodes = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    entries = []
    for node in nodes:
        title = clean_text(child_text(node, ["title"]))
        link = item_link(node)
        summary = clean_text(child_text(node, ["description", "summary", "content"]))
        published = parse_date(child_text(node, ["pubDate", "published", "updated"]))
        if title and link:
            entries.append({"sourceName": source, "title": title, "source": link, "summary": summary, "published": published})
    return entries


def normalize(value: str) -> str:
    value = re.sub(r"\s+-\s+[^-]+$", "", value)
    value = re.sub(r"[^a-z0-9 ]+", "", value.lower())
    return re.sub(r"\s+", " ", value).strip()


def category_for(item: dict) -> str:
    text = f"{item['title']} {item['summary']} {item['sourceName']}".lower()
    for category, keywords in CATEGORY_RULES:
        if any(keyword in text for keyword in keywords):
            return category
    return "AI Companies"


def score(item: dict) -> int:
    text = f"{item['title']} {item['summary']}".lower()
    important = ["openai", "anthropic", "google", "deepmind", "meta", "microsoft", "nvidia", "policy", "regulation", "copyright", "safety", "model", "funding"]
    value = sum(3 for keyword in important if keyword in text)
    if item["published"]:
        age = (dt.datetime.now(dt.timezone.utc) - item["published"]).total_seconds() / 3600
        if age <= 24:
            value += 10
        elif age <= 48:
            value += 4
    if item["sourceName"].startswith("Google News"):
        value += 1
    if any(hint in text for hint in TRUSTED_HINTS):
        value += 12
    if any(hint in text for hint in LOW_TRUST_HINTS):
        value -= 16
    return value


def collect_news() -> list[dict]:
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=48)
    seen = set()
    items = []
    for source, url in FEEDS:
        for item in parse_feed(source, url):
            key = normalize(item["title"]) or item["source"]
            if key in seen:
                continue
            seen.add(key)
            if item["published"] and item["published"] < cutoff:
                continue
            item["category"] = category_for(item)
            item["score"] = score(item)
            items.append(item)
    ranked = sorted(items, key=lambda row: (row["score"], row["published"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc)), reverse=True)
    diverse = []
    seen_roots = set()
    for item in ranked:
        root = normalize(re.sub(r"\s+-\s+[^-]+$", "", item["title"]))[:70]
        if root in seen_roots:
            continue
        seen_roots.add(root)
        diverse.append(item)
    return diverse


def summarize_sentence(item: dict) -> str:
    summary = item.get("summary") or ""
    if summary:
        summary = re.split(r"(?<=[.!?])\s+", summary)[0]
    if not summary or len(summary) < 45:
        summary = f"{item['sourceName']} reported this AI-related development within the latest monitoring window."
    return summary[:420]


def build_issue(items: list[dict]) -> dict:
    now_myt = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    chosen = items[:8]
    if not chosen:
        raise RuntimeError("No AI news items found from configured feeds.")

    stories = []
    for item in chosen:
        category = item["category"]
        stories.append(
            {
                "category": category,
                "title": item["title"],
                "summary": summarize_sentence(item),
                "whyItMatters": WHY_BY_CATEGORY.get(category, WHY_BY_CATEGORY["AI Companies"]),
                "source": item["source"],
            }
        )

    highlights = []
    for story in stories[:5]:
        highlights.append(f"{story['category']}: {story['title']}")

    return {
        "date": now_myt.strftime("%Y-%m-%d"),
        "label": "Today",
        "status": "Auto-updated from RSS and news feeds. Recheck primary sources before using any item as a formal citation.",
        "highlights": highlights,
        "stories": stories,
        "discordShort": [story["title"] for story in stories[:10]],
    }


def load_data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_data(data: dict) -> None:
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    data = load_data()
    issue = build_issue(collect_news())
    issues = [row for row in data.get("issues", []) if row.get("date") != issue["date"]]
    for row in issues:
        row["label"] = "Archive"
    data["issues"] = [issue] + issues[:30]
    data.setdefault("site", {})
    data["site"]["lastUpdated"] = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(timespec="seconds")
    save_data(data)
    print(f"Updated {DATA_PATH} with {len(issue['stories'])} stories for {issue['date']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
