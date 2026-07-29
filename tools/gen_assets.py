#!/usr/bin/env python3
"""
Animated SVG asset generator for GitHub profile / repo READMEs.

Design constraints (researched, see NOTES.md):
  * SVGs are consumed via <img> in GitHub Markdown -> "secure animated mode".
    - CSS @keyframes / SMIL animation: WORKS
    - <script>: blocked
    - external resources (images, webfonts): blocked  -> everything must be inline
  * `prefers-color-scheme` inside an <img>-embedded SVG is inconsistent across
    browsers and reflects the OS, not GitHub's theme toggle. So every asset
    paints its OWN opaque dark surface and reads identically in both themes.
  * Only generic font families are safe: monospace / sans-serif / system-ui.
"""
from __future__ import annotations
import math, random, html
from dataclasses import dataclass, field

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace"
SANS = "system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


@dataclass
class Theme:
    """One visual identity per GitHub account."""
    key: str
    a1: str                      # accent 1
    a2: str                      # accent 2
    a3: str                      # accent 3 (highlight)
    bg0: str = "#05070d"         # deep surface
    bg1: str = "#0b1020"         # raised surface
    ink: str = "#e8edf7"         # primary text
    dim: str = "#8b97b0"         # secondary text
    grid: str = "#1b2440"


THEMES = {
    # main account: AI / autonomous agents / Android systems -> cyan to violet
    "GamerX3560": Theme("neural", "#00e5ff", "#7c4dff", "#00ffa3"),
    # OS ecosystem: Arch blue to teal
    "GamerXECO-sys55": Theme("arch", "#1793d1", "#00e5c3", "#8be9fd", bg0="#04080e", bg1="#081826", grid="#123449"),
    # web / ML / college work: magenta to amber
    "GraphicsAndroid65": Theme("prism", "#ff3d81", "#ffb340", "#7c4dff", bg0="#0a0611", bg1="#160d22", grid="#2d1a3d"),
}


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


# --------------------------------------------------------------------------- #
# shared building blocks
# --------------------------------------------------------------------------- #
def _defs(t: Theme, w: int, h: int, uid: str) -> str:
    return f"""
  <defs>
    <linearGradient id="acc{uid}" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t.a1}"/>
      <stop offset="55%" stop-color="{t.a2}"/>
      <stop offset="100%" stop-color="{t.a3}"/>
    </linearGradient>
    <linearGradient id="surf{uid}" x1="0" y1="0" x2="0.35" y2="1">
      <stop offset="0%" stop-color="{t.bg1}"/>
      <stop offset="100%" stop-color="{t.bg0}"/>
    </linearGradient>
    <radialGradient id="blob{uid}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{t.a1}" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="{t.a1}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="blob2{uid}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{t.a2}" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="{t.a2}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="blob3{uid}" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{t.a3}" stop-opacity="0.40"/>
      <stop offset="100%" stop-color="{t.a3}" stop-opacity="0"/>
    </radialGradient>
    <pattern id="grid{uid}" width="34" height="34" patternUnits="userSpaceOnUse">
      <path d="M34 0H0V34" fill="none" stroke="{t.grid}" stroke-width="1" stroke-opacity="0.55"/>
    </pattern>
    <filter id="soft{uid}" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="18"/>
    </filter>
    <filter id="glow{uid}" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="3.2" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="frame{uid}"><rect width="{w}" height="{h}" rx="16"/></clipPath>
  </defs>"""


def _aurora(t: Theme, w: int, h: int, uid: str) -> str:
    """Slow drifting colour blobs behind everything."""
    return f"""
  <g filter="url(#soft{uid})" opacity="0.95">
    <circle class="b1" cx="{int(w*0.18)}" cy="{int(h*0.30)}" r="{int(h*0.62)}" fill="url(#blob{uid})"/>
    <circle class="b2" cx="{int(w*0.74)}" cy="{int(h*0.68)}" r="{int(h*0.66)}" fill="url(#blob2{uid})"/>
    <circle class="b3" cx="{int(w*0.48)}" cy="{int(h*0.12)}" r="{int(h*0.50)}" fill="url(#blob3{uid})"/>
  </g>"""


AURORA_CSS = """
    .b1{animation:d1 19s ease-in-out infinite}
    .b2{animation:d2 23s ease-in-out infinite}
    .b3{animation:d3 27s ease-in-out infinite}
    @keyframes d1{0%,100%{transform:translate(0,0)}50%{transform:translate(70px,26px)}}
    @keyframes d2{0%,100%{transform:translate(0,0)}50%{transform:translate(-80px,-30px)}}
    @keyframes d3{0%,100%{transform:translate(0,0)}50%{transform:translate(40px,34px)}}
"""


def _particles(t: Theme, w: int, h: int, n: int, seed: int) -> str:
    rng = random.Random(seed)
    out = []
    for i in range(n):
        x = rng.uniform(0, w)
        y = rng.uniform(0, h)
        r = rng.choice([0.9, 1.2, 1.6, 2.1])
        dur = rng.uniform(6, 15)
        delay = rng.uniform(0, 10)
        col = rng.choice([t.a1, t.a2, t.a3, t.ink])
        rise = rng.uniform(18, 46)
        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{col}" opacity="0">'
            f'<animate attributeName="opacity" values="0;0.85;0" dur="{dur:.1f}s"'
            f' begin="-{delay:.1f}s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate"'
            f' values="0 0;0 -{rise:.0f}" dur="{dur:.1f}s" begin="-{delay:.1f}s"'
            f' repeatCount="indefinite"/></circle>'
        )
    return '<g class="dust">' + "".join(out) + "</g>"


# --------------------------------------------------------------------------- #
# 1. HERO BANNER
# --------------------------------------------------------------------------- #
def hero(user: str, title: str, kicker: str, lines: list[str],
         w: int = 1200, h: int = 320) -> str:
    """Animated header: aurora + grid + scanline + gradient title + typing rotator."""
    t = THEMES[user]
    uid = "h"
    ch = 15.0                                    # px advance for the 25px mono font
    n = len(lines)
    seg = 100.0 / n                              # % of timeline per line
    hold_in, hold_out = seg * 0.16, seg * 0.10   # reveal / hide portions

    rot, css = [], []
    for i, ln in enumerate(lines):
        tw = len(ln) * ch
        s = i * seg
        # opacity: visible only inside this line's slot
        css.append(
            f".ln{i}{{opacity:0;animation:o{i} {n*4.2:.1f}s linear infinite}}"
            f"@keyframes o{i}{{0%,{max(s-0.4,0):.2f}%{{opacity:0}}"
            f"{s+0.01:.2f}%,{s+seg-0.4:.2f}%{{opacity:1}}"
            f"{s+seg:.2f}%,100%{{opacity:0}}}}"
        )
        # width of the reveal mask, in px, animated: 0 -> full -> hold -> 0
        css.append(
            f".rv{i}{{animation:r{i} {n*4.2:.1f}s linear infinite}}"
            f"@keyframes r{i}{{0%,{s:.2f}%{{width:0px}}"
            f"{s+hold_in:.2f}%,{s+seg-hold_out:.2f}%{{width:{tw:.0f}px}}"
            f"{s+seg-hold_out*0.2:.2f}%,100%{{width:0px}}}}"
        )
        rot.append(f"""
      <g class="ln{i}">
        <clipPath id="c{i}"><rect class="rv{i}" x="0" y="-22" width="0" height="34"/></clipPath>
        <text class="mono" clip-path="url(#c{i})" x="0" y="0">{esc(ln)}</text>
        <rect class="caret" x="-2" y="-20" width="2.5" height="26" fill="{t.a3}"/>
      </g>""")

    tx = w // 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)} — {esc(kicker)}">
  <title>{esc(title)} — {esc(kicker)}</title>
{_defs(t, w, h, uid)}
  <style>
    text{{dominant-baseline:middle}}
    .mono{{font-family:{MONO};font-size:25px;font-weight:600;fill:{t.a3};letter-spacing:0.5px}}
    .caret{{animation:blink 1.05s steps(1) infinite}}
    @keyframes blink{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}
    .title{{font-family:{SANS};font-size:78px;font-weight:800;letter-spacing:-2px;fill:url(#acc{uid})}}
    .kick{{font-family:{MONO};font-size:15px;font-weight:600;fill:{t.dim};letter-spacing:5px;text-transform:uppercase}}
    .halo{{animation:pulse 5.5s ease-in-out infinite}}
    @keyframes pulse{{0%,100%{{opacity:.35}}50%{{opacity:.85}}}}
    .scan{{animation:scan 7s linear infinite}}
    @keyframes scan{{0%{{transform:translateY(-40px)}}100%{{transform:translateY({h+40}px)}}}}
    .sweep{{animation:sweep 4.5s ease-in-out infinite}}
    @keyframes sweep{{0%,100%{{transform:translateX(-{w*0.35:.0f}px);opacity:0}}45%{{opacity:.5}}50%{{transform:translateX({w*0.35:.0f}px);opacity:0}}}}
    .rail{{animation:rail 3.6s ease-in-out infinite}}
    @keyframes rail{{0%,100%{{transform:scaleX(.25);opacity:.5}}50%{{transform:scaleX(1);opacity:1}}}}
    .fadein{{animation:fi 1.4s ease-out}}
    @keyframes fi{{from{{opacity:.25;transform:translateY(8px) scale(.985)}}to{{opacity:1;transform:none}}}}
{AURORA_CSS}
    @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.rv0{{width:{len(lines[0])*ch:.0f}px}}}}
  </style>
  <g clip-path="url(#frame{uid})">
    <rect width="{w}" height="{h}" fill="url(#surf{uid})"/>
{_aurora(t, w, h, uid)}
    <rect width="{w}" height="{h}" fill="url(#grid{uid})" opacity="0.38"/>
    <rect class="scan" width="{w}" height="2" y="0" fill="{t.a1}" opacity="0.22"/>
{_particles(t, w, h, 46, 7)}
    <g class="halo"><ellipse cx="{tx}" cy="{int(h*0.42)}" rx="{int(w*0.34)}" ry="46" fill="url(#blob{uid})"/></g>
    <g class="fadein">
      <text class="kick" x="{tx}" y="{int(h*0.19)}" text-anchor="middle">{esc(kicker)}</text>
      <text class="title" x="{tx}" y="{int(h*0.44)}" text-anchor="middle" filter="url(#glow{uid})">{esc(title)}</text>
    </g>
    <g transform="translate({int(w*0.5)},{int(h*0.70)})" text-anchor="start">
      <g transform="translate(-{int(max(len(l) for l in lines)*ch/2)},0)">{''.join(rot)}</g>
    </g>
    <g transform="translate({tx},{int(h*0.86)})">
      <rect class="rail" x="-160" y="-1" width="320" height="2.5" rx="1.25" fill="url(#acc{uid})"/>
    </g>
    <rect class="sweep" x="{int(w*0.5)-90}" y="0" width="180" height="{h}" fill="url(#acc{uid})" opacity="0"/>
    <rect width="{w}" height="{h}" rx="16" fill="none" stroke="{t.a1}" stroke-opacity="0.28" stroke-width="1.5"/>
  </g>
</svg>
"""


# --------------------------------------------------------------------------- #
# 2. DIVIDER
# --------------------------------------------------------------------------- #
def divider(user: str, w: int = 1200, h: int = 8) -> str:
    t = THEMES[user]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="section divider">
  <defs>
    <linearGradient id="dg" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{t.a1}" stop-opacity="0"/>
      <stop offset="20%" stop-color="{t.a1}"/>
      <stop offset="50%" stop-color="{t.a2}"/>
      <stop offset="80%" stop-color="{t.a3}"/>
      <stop offset="100%" stop-color="{t.a3}" stop-opacity="0"/>
    </linearGradient>
    <linearGradient id="dh" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#fff" stop-opacity="0"/>
      <stop offset="50%" stop-color="#fff" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <style>
    .run{{animation:run 3.8s ease-in-out infinite}}
    @keyframes run{{0%{{transform:translateX(-{w*0.5:.0f}px)}}100%{{transform:translateX({w*0.5:.0f}px)}}}}
    .br{{animation:br 3.8s ease-in-out infinite}}
    @keyframes br{{0%,100%{{opacity:.45}}50%{{opacity:1}}}}
    @media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
  </style>
  <rect class="br" y="{h/2-1.25:.1f}" width="{w}" height="2.5" rx="1.25" fill="url(#dg)"/>
  <rect class="run" x="{w*0.5-110:.0f}" y="{h/2-1.75:.1f}" width="220" height="3.5" rx="1.75" fill="url(#dh)" opacity="0.85"/>
</svg>
"""


# --------------------------------------------------------------------------- #
# 3. TECH STACK STRIP
# --------------------------------------------------------------------------- #
def stack(user: str, chips: list[str], heading: str = "Tech Arsenal",
          per_row: int = 6, w: int = 1200) -> str:
    """
    Chips that cascade in and then breathe, on real card chrome.

    The chrome matters: entrance animations rest at opacity 0, so an asset with
    no background rasterises to an empty PNG in any non-animating renderer
    (GitHub's Markdown API, link unfurlers, image crawlers). The surface, border
    and heading are deliberately un-animated so frame zero is never blank.
    """
    t = THEMES[user]
    uid = "k"
    ch, pad, gap, rh = 8.4, 18, 12, 44
    rows: list[list[str]] = [chips[i:i + per_row] for i in range(0, len(chips), per_row)]
    top = 62
    h = top + len(rows) * (rh + gap) + 12
    body, css = [], []
    idx = 0
    for r, row in enumerate(rows):
        widths = [len(c) * ch + pad * 2 for c in row]
        total = sum(widths) + gap * (len(row) - 1)
        x = (w - total) / 2
        y = top + r * (rh + gap)
        for c, cw in zip(row, widths):
            d = 0.12 + idx * 0.06
            css.append(f".ch{idx}{{opacity:0;animation:pop .6s cubic-bezier(.2,.9,.2,1) {d:.2f}s both,"
                       f"breathe 4.6s ease-in-out {d + 0.9:.2f}s infinite}}")
            body.append(f"""
    <g class="ch{idx}">
      <rect x="{x:.1f}" y="{y}" width="{cw:.1f}" height="{rh}" rx="10" fill="{t.bg1}"
            stroke="url(#cg{uid})" stroke-width="1.4"/>
      <rect x="{x:.1f}" y="{y}" width="{cw:.1f}" height="{rh}" rx="10" fill="url(#acc{uid})" opacity="0.10"/>
      <text x="{x + cw/2:.1f}" y="{y + rh/2 + 1}" text-anchor="middle" class="cl">{esc(c)}</text>
    </g>""")
            x += cw + gap
            idx += 1
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(heading)}: {esc(', '.join(chips))}">
  <title>{esc(heading)}</title>
{_defs(t, w, h, uid)}
  <defs>
    <linearGradient id="cg{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{t.a1}" stop-opacity="0.85"/>
      <stop offset="100%" stop-color="{t.a2}" stop-opacity="0.85"/>
    </linearGradient>
  </defs>
  <style>
    .cl{{font-family:{MONO};font-size:13.5px;font-weight:600;fill:{t.ink};dominant-baseline:middle}}
    .hd{{font-family:{SANS};font-size:17px;font-weight:700;fill:url(#acc{uid})}}
    .sub{{font-family:{MONO};font-size:9.5px;fill:{t.dim};letter-spacing:1.6px}}
    @keyframes pop{{from{{opacity:0;transform:translateY(12px) scale(.94)}}to{{opacity:1;transform:none}}}}
    @keyframes breathe{{0%,100%{{opacity:1}}50%{{opacity:.74}}}}
    {''.join(css)}
{AURORA_CSS}
    @media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important;transform:none!important}}}}
  </style>
  <g clip-path="url(#frame{uid})">
    <rect width="{w}" height="{h}" fill="url(#surf{uid})"/>
{_aurora(t, w, h, uid)}
    <rect width="{w}" height="{h}" fill="url(#grid{uid})" opacity="0.26"/>
    <text class="hd" x="46" y="32">{esc(heading)}</text>
    <text class="sub" x="46" y="50">LANGUAGES · RUNTIMES · TOOLING</text>
    <line x1="46" y1="{top-14}" x2="{w-46}" y2="{top-14}" stroke="{t.grid}" stroke-width="1"/>
{''.join(body)}
    <rect width="{w}" height="{h}" rx="16" fill="none" stroke="{t.a1}" stroke-opacity="0.26" stroke-width="1.5"/>
  </g>
</svg>
"""


# --------------------------------------------------------------------------- #
# 4. STATS CARD  (self-hosted replacement for github-readme-stats)
# --------------------------------------------------------------------------- #
def stats_card(user: str, stats: dict, monthly: list[int] | None = None,
               w: int = 560, h: int = 240) -> str:
    """
    Metric column + animated 12-month contribution sparkline.
    stats keys: repos, stars, forks, commits, contributions, followers, created, updated
    """
    t = THEMES[user]
    uid = "s"
    items = [
        ("Public repositories", stats.get("repos", 0)),
        ("Total stars earned", stats.get("stars", 0)),
        ("Contributions (12 mo)", stats.get("contributions", 0)),
        ("Commits (12 mo)", stats.get("commits", 0)),
        ("Repos created (12 mo)", stats.get("new_repos", 0)),
        ("Followers", stats.get("followers", 0)),
    ]
    rows = []
    for i, (label, val) in enumerate(items):
        y = 86 + i * 24
        rows.append(f"""
    <g class="rw" style="animation-delay:{0.15 + i*0.085:.2f}s">
      <circle cx="30" cy="{y-4}" r="2.6" fill="{t.a1}"/>
      <text class="lb" x="44" y="{y}">{esc(label)}</text>
      <text class="vl" x="{w-30}" y="{y}" text-anchor="end">{val:,}</text>
    </g>""")

    # --- sparkline of the last 12 months of contributions ---
    monthly = (monthly or [0] * 12)[-12:]
    peak = max(monthly) or 1
    bw, bg = 26, 8
    base_y, max_h = h - 26, 46
    sx = (w - (len(monthly) * bw + (len(monthly) - 1) * bg)) / 2
    bars = []
    for i, v in enumerate(monthly):
        bh = max(v / peak * max_h, 2.0)
        x = sx + i * (bw + bg)
        bars.append(
            f'<rect class="bar" style="animation-delay:{0.75+i*0.055:.2f}s;'
            f'transform-origin:{x+bw/2:.1f}px {base_y}px"'
            f' x="{x:.1f}" y="{base_y-bh:.1f}" width="{bw}" height="{bh:.1f}" rx="3.5"'
            f' fill="url(#acc{uid})" opacity="{0.45 + 0.55*v/peak:.2f}"/>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="GitHub statistics for {esc(user)}">
  <title>{esc(user)} — GitHub statistics</title>
{_defs(t, w, h, uid)}
  <style>
    .hd{{font-family:{SANS};font-size:16px;font-weight:700;fill:url(#acc{uid})}}
    .sub{{font-family:{MONO};font-size:9px;fill:{t.dim};letter-spacing:1.5px}}
    .lb{{font-family:{SANS};font-size:12px;fill:{t.dim};dominant-baseline:middle}}
    .vl{{font-family:{MONO};font-size:13px;font-weight:700;fill:{t.ink};dominant-baseline:middle}}
    .rw{{opacity:0;animation:sl .55s cubic-bezier(.2,.9,.2,1) both}}
    @keyframes sl{{from{{opacity:0;transform:translateX(-10px)}}to{{opacity:1;transform:none}}}}
    .bar{{transform:scaleY(0);animation:gy .7s cubic-bezier(.2,.9,.2,1) both}}
    @keyframes gy{{to{{transform:scaleY(1)}}}}
{AURORA_CSS}
    @media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important;transform:none!important}}}}
  </style>
  <g clip-path="url(#frame{uid})">
    <rect width="{w}" height="{h}" fill="url(#surf{uid})"/>
{_aurora(t, w, h, uid)}
    <rect width="{w}" height="{h}" fill="url(#grid{uid})" opacity="0.28"/>
    <text class="hd" x="30" y="36">GitHub Statistics</text>
    <text class="sub" x="30" y="54">SELF-HOSTED · REGENERATED {esc(stats.get('updated','')).upper()}</text>
    <line x1="30" y1="64" x2="{w-30}" y2="64" stroke="{t.grid}" stroke-width="1"/>
{''.join(rows)}
    <line x1="30" y1="{base_y+7}" x2="{w-30}" y2="{base_y+7}" stroke="{t.grid}" stroke-width="1"/>
{''.join(bars)}
    <rect width="{w}" height="{h}" rx="16" fill="none" stroke="{t.a1}" stroke-opacity="0.26" stroke-width="1.5"/>
  </g>
</svg>
"""


# --------------------------------------------------------------------------- #
# 4b. CONTRIBUTION HEATMAP  (self-hosted, replaces snake/activity-graph actions)
# --------------------------------------------------------------------------- #
def activity_card(user: str, weeks: list[list[int]], total: int, updated: str,
                  w: int = 1200) -> str:
    """
    weeks: list of weeks, each a list of 7 daily contribution counts (Sun..Sat).
    A diagonal wave sweeps across the grid; active cells pulse on the beat.
    """
    t = THEMES[user]
    cell, gap = 15, 4
    left, top = 46, 74
    cols = len(weeks)
    grid_w = cols * (cell + gap)
    h = top + 7 * (cell + gap) + 40
    peak = max((max(wk) if wk else 0) for wk in weeks) or 1

    def tone(v: int) -> tuple[str, float]:
        if v == 0:
            return t.grid, 0.55
        r = v / peak
        if r <= 0.25: return t.a1, 0.40
        if r <= 0.50: return t.a1, 0.65
        if r <= 0.75: return t.a2, 0.85
        return t.a3, 1.0

    cells, dow = [], ["", "Mon", "", "Wed", "", "Fri", ""]
    for ci, wk in enumerate(weeks):
        for di in range(7):
            v = wk[di] if di < len(wk) else 0
            col, op = tone(v)
            x = left + ci * (cell + gap)
            y = top + di * (cell + gap)
            delay = (ci * 0.024) + (di * 0.045)
            cls = "cl act" if v else "cl"
            cells.append(
                f'<rect class="{cls}" style="animation-delay:{delay:.2f}s,{delay+1.4:.2f}s"'
                f' x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3.5"'
                f' fill="{col}" opacity="{op}"/>'
            )
    labels = "".join(
        f'<text class="dw" x="{left-10}" y="{top + i*(cell+gap) + cell/2}" text-anchor="end">{d}</text>'
        for i, d in enumerate(dow) if d
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{total} contributions in the last year by {esc(user)}">
  <title>{esc(user)} — {total} contributions in the last year</title>
{_defs(t, w, h, 'a')}
  <style>
    .hd{{font-family:{SANS};font-size:17px;font-weight:700;fill:url(#acca)}}
    .sub{{font-family:{MONO};font-size:9.5px;fill:{t.dim};letter-spacing:1.6px}}
    .dw{{font-family:{MONO};font-size:9.5px;fill:{t.dim};dominant-baseline:middle}}
    .lg{{font-family:{MONO};font-size:9.5px;fill:{t.dim};dominant-baseline:middle}}
    .cl{{transform:scale(0);transform-box:fill-box;transform-origin:center;
        animation:bloom .55s cubic-bezier(.2,.9,.3,1.4) both}}
    .act{{animation:bloom .55s cubic-bezier(.2,.9,.3,1.4) both,
                    twinkle 3.6s ease-in-out infinite}}
    @keyframes bloom{{to{{transform:scale(1)}}}}
    @keyframes twinkle{{0%,100%{{filter:none}}50%{{filter:brightness(1.65)}}}}
    .beam{{animation:beam 6.5s ease-in-out infinite}}
    @keyframes beam{{0%{{transform:translateX(-160px);opacity:0}}
                     18%{{opacity:.30}}82%{{opacity:.30}}
                     100%{{transform:translateX({grid_w+40}px);opacity:0}}}}
{AURORA_CSS}
    @media (prefers-reduced-motion:reduce){{*{{animation:none!important;transform:none!important}}}}
  </style>
  <g clip-path="url(#framea)">
    <rect width="{w}" height="{h}" fill="url(#surfa)"/>
{_aurora(t, w, h, 'a')}
    <rect width="{w}" height="{h}" fill="url(#grida)" opacity="0.22"/>
    <text class="hd" x="{left}" y="36">{total:,} contributions in the last year</text>
    <text class="sub" x="{left}" y="55">CONTRIBUTION GRAPH · SELF-HOSTED · {esc(updated).upper()}</text>
    {labels}
    <g>{''.join(cells)}</g>
    <rect class="beam" x="{left}" y="{top-4}" width="120" height="{7*(cell+gap)}"
          fill="url(#acca)" opacity="0"/>
    <g transform="translate({left},{h-22})">
      <text class="lg" x="0" y="0">less</text>
      <rect x="34" y="-6" width="12" height="12" rx="3" fill="{t.grid}" opacity="0.55"/>
      <rect x="50" y="-6" width="12" height="12" rx="3" fill="{t.a1}" opacity="0.40"/>
      <rect x="66" y="-6" width="12" height="12" rx="3" fill="{t.a1}" opacity="0.65"/>
      <rect x="82" y="-6" width="12" height="12" rx="3" fill="{t.a2}" opacity="0.85"/>
      <rect x="98" y="-6" width="12" height="12" rx="3" fill="{t.a3}"/>
      <text class="lg" x="120" y="0">more</text>
    </g>
    <rect width="{w}" height="{h}" rx="16" fill="none" stroke="{t.a1}" stroke-opacity="0.26" stroke-width="1.5"/>
  </g>
</svg>
"""


# --------------------------------------------------------------------------- #
# 5. LANGUAGE CARD
# --------------------------------------------------------------------------- #
def lang_card(user: str, langs: list[tuple[str, float]], w: int = 560, h: int = 240) -> str:
    """langs: [(name, percent)] already sorted desc, max ~6 entries."""
    t = THEMES[user]
    uid = "l"
    palette = [t.a1, t.a2, t.a3, "#ffb340", "#ff5c8a", "#5ee7a0", "#9aa7c2"]
    langs = langs[:6]
    # stacked meter
    bar_y, bar_w, bar_h, x = 74, w - 60, 13, 30.0
    seg, rows = [], []
    for i, (name, p) in enumerate(langs):
        sw = bar_w * p / 100.0
        col = palette[i % len(palette)]
        seg.append(f'<rect class="sg" style="animation-delay:{0.25+i*0.11:.2f}s;transform-origin:{x:.1f}px 0"'
                   f' x="{x:.1f}" y="{bar_y}" width="{max(sw,1.5):.1f}" height="{bar_h}" fill="{col}"/>')
        x += sw
        ry = 118 + i * 21
        cx = 34 if i < 3 else w / 2 + 10
        ty = 118 + (i % 3) * 21
        rows.append(f"""
    <g class="rw" style="animation-delay:{0.5+i*0.09:.2f}s">
      <rect x="{cx}" y="{ty-7}" width="11" height="11" rx="3" fill="{col}"/>
      <text class="lb" x="{cx+19}" y="{ty}">{esc(name)}</text>
      <text class="vl" x="{cx+225}" y="{ty}" text-anchor="end">{p:.1f}%</text>
    </g>""")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Most used languages for {esc(user)}">
  <title>{esc(user)} — language distribution</title>
{_defs(t, w, h, uid)}
  <style>
    .hd{{font-family:{SANS};font-size:17px;font-weight:700;fill:url(#acc{uid})}}
    .sub{{font-family:{MONO};font-size:9.5px;fill:{t.dim};letter-spacing:1.6px}}
    .lb{{font-family:{SANS};font-size:12.5px;fill:{t.dim};dominant-baseline:middle}}
    .vl{{font-family:{MONO};font-size:12.5px;font-weight:700;fill:{t.ink};dominant-baseline:middle}}
    .sg{{transform:scaleX(0);animation:gx .95s cubic-bezier(.2,.9,.2,1) both}}
    @keyframes gx{{to{{transform:scaleX(1)}}}}
    .rw{{opacity:0;animation:sl .55s ease-out both}}
    @keyframes sl{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:none}}}}
    .shine{{animation:sh 3.4s ease-in-out 1.3s infinite}}
    @keyframes sh{{0%{{transform:translateX(0);opacity:0}}25%{{opacity:.75}}100%{{transform:translateX({w-60}px);opacity:0}}}}
{AURORA_CSS}
    @media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important;transform:none!important}}}}
  </style>
  <g clip-path="url(#frame{uid})">
    <rect width="{w}" height="{h}" fill="url(#surf{uid})"/>
{_aurora(t, w, h, uid)}
    <rect width="{w}" height="{h}" fill="url(#grid{uid})" opacity="0.30"/>
    <text class="hd" x="30" y="38">Language Distribution</text>
    <text class="sub" x="30" y="56">BY BYTES ACROSS ALL PUBLIC REPOSITORIES</text>
    <g clip-path="url(#frame{uid})">
      <rect x="30" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="6.5" fill="{t.bg0}"/>
      <g clip-path="url(#meter)">{''.join(seg)}</g>
      <clipPath id="meter"><rect x="30" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="6.5"/></clipPath>
      <rect class="shine" x="30" y="{bar_y}" width="60" height="{bar_h}" fill="#fff" opacity="0"/>
    </g>
{''.join(rows)}
    <rect width="{w}" height="{h}" rx="16" fill="none" stroke="{t.a1}" stroke-opacity="0.26" stroke-width="1.5"/>
  </g>
</svg>
"""


# --------------------------------------------------------------------------- #
# 6. PROJECT CARD  (repo README headers)
# --------------------------------------------------------------------------- #
def repo_hero(user: str, name: str, tagline: str, badges: list[str],
              w: int = 1200, h: int = 260) -> str:
    t = THEMES[user]
    uid = "r"
    ch, pad, gap = 7.6, 14, 10
    widths = [len(b) * ch + pad * 2 for b in badges]
    total = sum(widths) + gap * (len(badges) - 1)
    bx = (w - total) / 2
    chips = []
    for i, (b, bw) in enumerate(zip(badges, widths)):
        chips.append(f"""
      <g class="bc" style="animation-delay:{0.55+i*0.08:.2f}s">
        <rect x="{bx:.1f}" y="0" width="{bw:.1f}" height="30" rx="15" fill="{t.bg1}"
              stroke="url(#acc{uid})" stroke-width="1.2" stroke-opacity="0.75"/>
        <text x="{bx+bw/2:.1f}" y="16" text-anchor="middle" class="bt">{esc(b)}</text>
      </g>""")
        bx += bw + gap
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(name)} — {esc(tagline)}">
  <title>{esc(name)} — {esc(tagline)}</title>
{_defs(t, w, h, uid)}
  <style>
    text{{dominant-baseline:middle}}
    .nm{{font-family:{SANS};font-size:62px;font-weight:800;letter-spacing:-1.6px;fill:url(#acc{uid})}}
    .tg{{font-family:{SANS};font-size:19px;font-weight:500;fill:{t.dim}}}
    .bt{{font-family:{MONO};font-size:12px;font-weight:600;fill:{t.ink}}}
    .up{{opacity:0;animation:up .9s cubic-bezier(.2,.9,.2,1) both}}
    @keyframes up{{from{{opacity:0;transform:translateY(18px)}}to{{opacity:1;transform:none}}}}
    .bc{{opacity:0;animation:up .6s cubic-bezier(.2,.9,.2,1) both}}
    .scan{{animation:scan 8s linear infinite}}
    @keyframes scan{{0%{{transform:translateY(-30px)}}100%{{transform:translateY({h+30}px)}}}}
    .halo{{animation:pulse 6s ease-in-out infinite}}
    @keyframes pulse{{0%,100%{{opacity:.30}}50%{{opacity:.8}}}}
{AURORA_CSS}
    @media (prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important}}}}
  </style>
  <g clip-path="url(#frame{uid})">
    <rect width="{w}" height="{h}" fill="url(#surf{uid})"/>
{_aurora(t, w, h, uid)}
    <rect width="{w}" height="{h}" fill="url(#grid{uid})" opacity="0.34"/>
    <rect class="scan" width="{w}" height="2" fill="{t.a1}" opacity="0.20"/>
{_particles(t, w, h, 34, 21)}
    <g class="halo"><ellipse cx="{w//2}" cy="{int(h*0.40)}" rx="{int(w*0.30)}" ry="42" fill="url(#blob{uid})"/></g>
    <g class="up">
      <text class="nm" x="{w//2}" y="{int(h*0.38)}" text-anchor="middle" filter="url(#glow{uid})">{esc(name)}</text>
      <text class="tg" x="{w//2}" y="{int(h*0.60)}" text-anchor="middle" fill="{t.dim}">{esc(tagline)}</text>
    </g>
    <g transform="translate(0,{int(h*0.76)})">{''.join(chips)}</g>
    <rect width="{w}" height="{h}" rx="16" fill="none" stroke="{t.a1}" stroke-opacity="0.28" stroke-width="1.5"/>
  </g>
</svg>
"""
