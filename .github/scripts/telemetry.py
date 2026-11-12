"""Builds assets/telemetry.svg from the GitHub GraphQL API. Run by .github/workflows/telemetry.yml."""
import datetime as dt
import json
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "tanush69lucifer")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT", "assets/telemetry.svg")

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 8, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}
"""

INK, PANEL, LINE, TX, MU = "#07040f", "#130c24", "#33284f", "#f2edfc", "#a79fc2"
SPEC = ["#FFC83D", "#FF6A1F", "#FF3FA4", "#9D6BFF", "#2EC8FF", "#8CFF3A"]
LEVELS = ["#1a1230", "#3b2a7a", "#9D6BFF", "#FF3FA4", "#FFC83D"]
MONO = "'JetBrains Mono','SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body,
                                 headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]


def streaks(days):
    counts = [d["contributionCount"] for d in days]
    if counts and counts[-1] == 0:  # today not done yet: don't break the streak
        counts = counts[:-1]
    cur = 0
    for c in reversed(counts):
        if c == 0:
            break
        cur += 1
    best = run = 0
    for c in counts:
        run = run + 1 if c else 0
        best = max(best, run)
    return cur, best


def build(u):
    cal = u["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"][-53:]
    days = [d for w in weeks for d in w["contributionDays"]]
    cur, best = streaks(days)
    repos = u["repositories"]["nodes"]
    stars = sum(r["stargazerCount"] for r in repos)
    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    total_l = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]

    tiles = [
        ("CONTRIBUTIONS", f"{cal['totalContributions']:,}", "last 12 months", SPEC[0]),
        ("CURRENT STREAK", f"{cur}d", "keep it alive", SPEC[1]),
        ("LONGEST STREAK", f"{best}d", "personal best", SPEC[2]),
        ("COMMITS", f"{u['contributionsCollection']['totalCommitContributions']:,}", "this year", SPEC[3]),
        ("PUBLIC REPOS", str(u["repositories"]["totalCount"]), f"{stars} stars", SPEC[4]),
        ("FOLLOWERS", str(u["followers"]["totalCount"]), "crew watching", SPEC[5]),
    ]
    o = []
    for i, (k, v, s, c) in enumerate(tiles):
        x = 25 + i * 160
        o.append(f'<g class="tile" style="animation-delay:{i*.12:.2f}s">'
                 f'<rect x="{x}" y="64" width="150" height="96" rx="12" fill="{PANEL}" stroke="{LINE}" stroke-width="1.5"/>'
                 f'<rect x="{x}" y="64" width="150" height="4" rx="2" fill="{c}"/>'
                 f'<text x="{x+14}" y="90" class="k" fill="{c}">{k}</text>'
                 f'<text x="{x+14}" y="128" class="v">{v}</text>'
                 f'<text x="{x+14}" y="148" class="s">{s}</text></g>')

    # heatmap
    mx = max([d["contributionCount"] for d in days] + [1])
    cell, gap = 11, 3
    hx = (1000 - len(weeks) * (cell + gap) + gap) // 2
    hy = 206
    last_month = None
    for wi, w in enumerate(weeks):
        x = hx + wi * (cell + gap)
        first = w["contributionDays"][0]["date"]
        m = dt.date.fromisoformat(first).strftime("%b").upper()
        if m != last_month and wi < len(weeks) - 2:
            o.append(f'<text x="{x}" y="{hy-8}" class="s">{m}</text>')
            last_month = m
        for d in w["contributionDays"]:
            wd = (dt.date.fromisoformat(d["date"]).weekday() + 1) % 7
            c = d["contributionCount"]
            lvl = 0 if c == 0 else min(4, 1 + int(3 * c / mx + .0001))
            cls = ' class="now"' if wi == len(weeks) - 1 else ""
            o.append(f'<rect{cls} x="{x}" y="{hy + wd*(cell+gap)}" width="{cell}" height="{cell}" rx="2.5" fill="{LEVELS[lvl]}"><title>{d["date"]}: {c}</title></rect>')
    hw = len(weeks) * (cell + gap)
    o.append(f'<clipPath id="hm"><rect x="{hx}" y="{hy}" width="{hw}" height="{7*(cell+gap)}"/></clipPath>'
             f'<g clip-path="url(#hm)"><rect class="beam" x="{hx-80}" y="{hy}" width="80" height="{7*(cell+gap)}" fill="url(#beam)"/></g>')
    lx = hx + hw - 5 * 15 - 70
    o.append(f'<text x="{lx}" y="{hy+7*(cell+gap)+18}" class="s">less</text>')
    for i, c in enumerate(LEVELS):
        o.append(f'<rect x="{lx+34+i*15}" y="{hy+7*(cell+gap)+8}" width="11" height="11" rx="2.5" fill="{c}"/>')
    o.append(f'<text x="{lx+34+5*15+4}" y="{hy+7*(cell+gap)+18}" class="s">more</text>')

    # languages bar
    by = 352
    o.append(f'<text x="25" y="{by-10}" class="k" fill="{MU}">LANGUAGE MIX</text>')
    x = 25.0
    for i, (n, s) in enumerate(top):
        w = 950 * s / total_l
        o.append(f'<rect class="lb" style="animation-delay:{.2+i*.1:.1f}s" x="{x:.1f}" y="{by}" width="{max(w-2,2):.1f}" height="10" rx="3" fill="{SPEC[i]}"/>')
        x += w
    lgx = 25
    for i, (n, s) in enumerate(top):
        label = f"{n} {100*s/total_l:.0f}%"
        o.append(f'<rect x="{lgx}" y="{by+22}" width="9" height="9" fill="{SPEC[i]}"/><text x="{lgx+15}" y="{by+31}" class="s" fill="{TX}">{label}</text>')
        lgx += 30 + len(label) * 7.6

    stamp = dt.datetime.now(dt.timezone.utc).strftime("%d %b %Y %H:%M UTC").upper()
    css = f"""
text{{font-family:{MONO}}}
.k{{font-size:11px;font-weight:700;letter-spacing:1.2px}}
.v{{font-size:30px;font-weight:800;fill:{TX}}}
.s{{font-size:11px;fill:{MU}}}
.tile{{animation:tin .8s cubic-bezier(.2,1.2,.3,1) both}}
@keyframes tin{{from{{opacity:0;transform:translateY(12px)}}}}
.beam{{animation:beam 4.5s linear infinite}}@keyframes beam{{to{{transform:translateX({hw+80}px)}}}}
.now{{animation:now 1.6s ease-in-out infinite}}@keyframes now{{50%{{opacity:.45}}}}
.lb{{transform-box:fill-box;transform-origin:left;animation:lb 1.2s cubic-bezier(.2,.9,.2,1) both}}@keyframes lb{{from{{transform:scaleX(0)}}}}
.dot{{animation:now 1.2s steps(1) infinite}}
"""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 400" width="1000" height="400" role="img">
<title>Live GitHub telemetry for {USER}</title><style>{css}</style>
<defs><pattern id="ht" width="8" height="8" patternUnits="userSpaceOnUse"><circle cx="4" cy="4" r="1" fill="#fff" opacity=".05"/></pattern>
<linearGradient id="beam"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".18"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>
<rect width="1000" height="400" rx="18" fill="{INK}"/><rect width="1000" height="400" rx="18" fill="url(#ht)"/>
<circle class="dot" cx="34" cy="34" r="5" fill="#ff4d6d"/>
<text x="48" y="38" class="k" fill="{TX}">LIVE FEED  //  @{USER}</text>
<text x="975" y="38" class="s" text-anchor="end">synced {stamp}</text>
{"".join(o)}
</svg>'''


if __name__ == "__main__":
    if os.environ.get("SAMPLE"):
        import random
        random.seed(4)
        start = dt.date.today() - dt.timedelta(days=370)
        start -= dt.timedelta(days=(start.weekday() + 1) % 7)
        wk = [{"contributionDays": [{"date": str(start + dt.timedelta(days=w*7+d)), "contributionCount": random.choice([0, 0, 1, 2, 3, 5, 8])} for d in range(7)]} for w in range(53)]
        u = {"followers": {"totalCount": 42}, "repositories": {"totalCount": 18, "nodes": [{"stargazerCount": 3, "languages": {"edges": [{"size": 900, "node": {"name": "Python"}}, {"size": 600, "node": {"name": "JavaScript"}}, {"size": 300, "node": {"name": "HTML"}}, {"size": 200, "node": {"name": "Java"}}, {"size": 100, "node": {"name": "CSS"}}]}}]},
             "contributionsCollection": {"totalCommitContributions": 612, "totalPullRequestContributions": 20, "contributionCalendar": {"totalContributions": 803, "weeks": wk}}}
    else:
        u = fetch()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(build(u))
    print("wrote", OUT)
