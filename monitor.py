"""Daily digest of new roles from SimplifyJobs listing repos. Runs on GitHub Actions cron."""
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------------------------------------------------------- config
SOURCES = {
    "Internships": "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json",
    "New Grad": "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json",
}

TITLE_ALLOW = [
    "software engineer", "swe", "machine learning", "ml engineer", "ai engineer",
    "data engineer", "quant", "research engineer", "platform", "infra",
    "backend", "back end", "back-end", "full stack", "full-stack", "fullstack",
]
TITLE_DENY = [
    "hardware", "mechanical", "electrical", "product manager", "product management",
    "product design", "ux design", "ui design", "designer", "civil",
]

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
    "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC", "PR",
}
US_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho", "illinois",
    "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine", "maryland",
    "massachusetts", "michigan", "minnesota", "mississippi", "missouri", "montana",
    "nebraska", "nevada", "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon", "pennsylvania",
    "rhode island", "south carolina", "south dakota", "tennessee", "texas", "utah",
    "vermont", "virginia", "washington", "west virginia", "wisconsin", "wyoming",
}
US_ALIASES = {"nyc", "sf", "la", "bay area", "united states", "usa", "u.s."}
NON_US = [
    "canada", "united kingdom", "uk", "germany", "france", "india", "mexico",
    "brazil", "japan", "china", "singapore", "australia", "netherlands", "poland",
    "ireland", "israel", "spain", "italy", "sweden", "switzerland", "korea",
    "taiwan", "europe", "emea", "apac",
]

SPONSOR_TAGS = {
    "Does Not Offer Sponsorship": " ⛔ no sponsorship",
    "U.S. Citizenship is Required": " ⛔ citizenship required",
    "Offers Sponsorship": " ✅ sponsors",
}

STATE_FILE = Path(__file__).resolve().parent / "state" / "seen.json"


# ---------------------------------------------------------------- helpers
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "job-digest-bot"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def title_ok(title):
    t = title.lower()
    if any(d in t for d in TITLE_DENY):
        return False
    return any(a in t for a in TITLE_ALLOW)


def is_us_location(loc):
    lo = loc.lower()
    if any(re.search(rf"\b{re.escape(c)}\b", lo) for c in NON_US):
        return False
    if "remote" in lo or "united states" in lo or lo in US_ALIASES or lo in US_STATE_NAMES:
        return True
    m = re.search(r", ([A-Z]{2})\b", loc)
    return bool(m and m.group(1) in US_STATES)


def location_ok(locations):
    return not locations or any(is_us_location(l) for l in locations)


def load_seen():
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    return set()


def save_seen(seen):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(json.dumps(sorted(seen), indent=0) + "\n", encoding="utf-8")


def post_issue(title, body):
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
    if not token or not repo:
        print(f"\n=== {title} ===\n{body}")
        return
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues",
        data=json.dumps({"title": title, "body": body}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "job-digest-bot",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        print(f"Issue created: {json.load(resp)['html_url']}")


def format_role(listing):
    locs = ", ".join(listing.get("locations") or []) or "location n/a"
    tag = SPONSOR_TAGS.get(listing.get("sponsorship"), "")
    return (
        f"- **{listing['company_name']}** — [{listing['title']}]({listing['url']})"
        f" — {locs}{tag}"
    )


# ---------------------------------------------------------------- main
def main():
    live = []
    for source, url in SOURCES.items():
        listings = fetch(url)
        live += [(source, l) for l in listings if l.get("active") and l.get("is_visible")]
        print(f"{source}: {len(listings)} listings fetched")

    seen = load_seen()
    if not seen:
        save_seen({l["id"] for _, l in live})
        post_issue("Job monitor seeded", f"Seeded {len(live)} active listings. Digests start tomorrow.")
        return

    new = [(s, l) for s, l in live if l["id"] not in seen]
    save_seen(seen | {l["id"] for _, l in new})

    matched = [(s, l) for s, l in new if title_ok(l["title"]) and location_ok(l.get("locations"))]
    print(f"{len(new)} new listings, {len(matched)} match filters")
    if not matched:
        return

    from datetime import date
    sections = []
    for source in SOURCES:
        roles = [format_role(l) for s, l in matched if s == source]
        if roles:
            sections.append(f"## {source} ({len(roles)})\n" + "\n".join(roles))
    post_issue(f"Job digest {date.today()} — {len(matched)} new roles", "\n\n".join(sections))


if __name__ == "__main__":
    sys.exit(main())
