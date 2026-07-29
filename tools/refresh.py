#!/usr/bin/env python3
"""
Regenerate the animated stats / language / activity SVGs for this profile.

Runs inside GitHub Actions with GITHUB_TOKEN, or locally with GH_TOKEN set.
Everything it produces is committed back into assets/, so the README never
depends on a third-party image service that can rate-limit or disappear.

    python3 tools/refresh.py <github-username>
"""
from __future__ import annotations
import collections, datetime, json, os, pathlib, sys, urllib.error, urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import gen_assets as G  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""

GQL = """query($login:String!){
  user(login:$login){
    followers{totalCount}
    contributionsCollection{
      totalCommitContributions
      totalRepositoryContributions
      contributionCalendar{
        totalContributions
        weeks{contributionDays{date contributionCount}}
      }
    }
  }
}"""


def api(path: str, method: str = "GET", body: dict | None = None):
    url = path if path.startswith("http") else "https://api.github.com" + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "profile-asset-refresher")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception:
        return 0, {}


def main() -> int:
    user = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PROFILE_USER", "")
    if not user:
        print("usage: refresh.py <github-username>", file=sys.stderr)
        return 2
    if user not in G.THEMES:
        print(f"no theme registered for {user!r}; known: {list(G.THEMES)}", file=sys.stderr)
        return 2

    # ---- public repositories -------------------------------------------------
    repos, page = [], 1
    while True:
        s, d = api(f"/users/{user}/repos?per_page=100&page={page}&type=owner")
        if s != 200 or not d:
            break
        repos += [r for r in d if not r.get("fork")]
        if len(d) < 100:
            break
        page += 1

    # ---- language bytes ------------------------------------------------------
    tally: collections.Counter = collections.Counter()
    for r in repos:
        s, d = api(f"/repos/{user}/{r['name']}/languages")
        if s == 200 and isinstance(d, dict):
            tally.update(d)
    total = sum(tally.values()) or 1
    langs = [(k, v * 100.0 / total) for k, v in tally.most_common(6)]

    # ---- contributions -------------------------------------------------------
    s, d = api("https://api.github.com/graphql", "POST",
               {"query": GQL, "variables": {"login": user}})
    u = (d.get("data") or {}).get("user") or {}
    cc = u.get("contributionsCollection", {}) or {}
    cal = cc.get("contributionCalendar", {}) or {}
    weeks_raw = cal.get("weeks", []) or []
    weeks = [[day["contributionCount"] for day in wk["contributionDays"]] for wk in weeks_raw]

    per_month: collections.Counter = collections.Counter()
    for wk in weeks_raw:
        for day in wk["contributionDays"]:
            per_month[day["date"][:7]] += day["contributionCount"]
    monthly = [per_month[m] for m in sorted(per_month)[-12:]]

    stats = dict(
        repos=len(repos),
        stars=sum(r.get("stargazers_count", 0) for r in repos),
        forks=sum(r.get("forks_count", 0) for r in repos),
        commits=cc.get("totalCommitContributions", 0),
        new_repos=cc.get("totalRepositoryContributions", 0),
        contributions=cal.get("totalContributions", 0),
        followers=(u.get("followers") or {}).get("totalCount", 0),
        updated=datetime.date.today().isoformat(),
    )

    if not repos:
        print("refusing to write assets: repository listing came back empty", file=sys.stderr)
        return 1

    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "stats.svg").write_text(G.stats_card(user, stats, monthly))
    if langs:
        (ASSETS / "langs.svg").write_text(G.lang_card(user, langs))
    if weeks:
        (ASSETS / "activity.svg").write_text(
            G.activity_card(user, weeks, stats["contributions"], stats["updated"]))
    (ASSETS / "stats.json").write_text(
        json.dumps({"stats": stats, "langs": langs}, indent=2) + "\n")

    print(f"{user}: repos={stats['repos']} stars={stats['stars']} "
          f"contributions={stats['contributions']} weeks={len(weeks)} "
          f"langs={[l[0] for l in langs]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
