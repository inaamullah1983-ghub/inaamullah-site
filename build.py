#!/usr/bin/env python3
"""Reward Heaven site builder. Runs on Netlify at every commit (see netlify.toml).

Inputs, all in this repository:
  index.html, og.png, robots.txt   the home page as designed, and its assets
  data/bulletins/YYYY-MM-DD.json   one small file per published daily bulletin
  data/library.json                published long-form videos (may be an empty list)
Output: the complete site in ./public. No dependencies beyond Python 3.
"""
import glob, html, json, os, re, shutil
from datetime import date

BASE = "https://inaamullah.netlify.app"
TAGLINE = "AI, code, chess and statecraft, made clear."
# Plausible analytics. data-domain must match the site registered in Plausible,
# so it is derived from BASE to stay in step with it. The outbound-links variant
# is used because every call to action here leaves the site (YouTube, Facebook,
# Instagram, TikTok), and the plain script would record none of those clicks.
PLAUSIBLE = ('<script defer data-domain="%s" '
             'src="https://plausible.io/js/script.outbound-links.js"></script>'
             % BASE.split("//", 1)[1])
VAR = {"ai": "ai", "code": "code", "chess": "chess", "statecraft": "state", "crypto": "crypto",
       "data": "data", "security": "sec", "travel": "travel"}
# Pill text sits on a 14% tint of its own colour, so the two darkest palette
# entries fall below WCAG 1.4.3 (4.5:1) at the pill's 15px/700: sec 3.06,
# data 3.80. Lowering the tint cannot fix it (same hue both sides: red tops out
# at 3.27 even at 6%), so the text is lightened one step instead. Scoped to the
# pill because --sec and --data are also used elsewhere on the home page.
PILL_INK = {"sec": "#FF6B6B", "data": "#B197FC"}  # -> 4.52, 4.96
SKIP = '<a class="skip" href="#main">Skip to content</a>'
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
OUT = "public"
e = html.escape


def nice(d):
    y, m, dd = map(int, d.split("-"))
    return "%d %s %d" % (dd, MONTHS[m - 1], y)


home = open("index.html", encoding="utf-8").read()
css = re.search(r"<style>(.*?)</style>", home, re.S).group(1)
EXTRA = """
/* site additions */
.nav{position:relative;z-index:4;max-width:760px;margin:0 auto;padding:14px 20px 0;display:flex;flex-wrap:wrap;gap:8px}
.nav a{font:600 16px var(--body);color:var(--text);text-decoration:none;padding:7px 14px;border-radius:999px;border:1px solid var(--edge);background:var(--glass)}
.nav a:hover,.nav a[aria-current=page]{background:var(--glass-hi);border-color:rgba(255,255,255,.35)}
.page{padding:28px 24px}
.page h1{font-size:clamp(40px,10vw,64px);line-height:.95}
.kicker{margin:0 0 10px;color:var(--muted);font:600 15px var(--body);letter-spacing:.08em;text-transform:uppercase}
.lead{margin:14px 0 0;font-size:20px;color:#D7DCE2}
.pill{--c:#fff;display:inline-block;font-family:var(--display);font-weight:700;font-size:15px;letter-spacing:.06em;text-transform:uppercase;color:var(--c);padding:2px 10px 1px;border-radius:999px;border:1.5px solid var(--c);background:color-mix(in srgb,var(--c) 14%,transparent)}
.items{margin:0;padding:0;list-style:none;display:grid;gap:12px}
.items li{padding:16px 18px}
.items p{margin:8px 0 0}
.items b{font-weight:700}
.watch{display:flex;flex-wrap:wrap;gap:10px;margin:0;padding:0;list-style:none}
.watch a{display:inline-block;font:600 17px var(--body);color:var(--text);text-decoration:none;padding:10px 18px;border-radius:999px;border:1px solid var(--edge);background:var(--glass-hi)}
.watch a:hover{background:rgba(255,255,255,.16)}
/* --red (#E03131) behind --text is 4.13:1, under WCAG 1.4.3 for this 17px/600
   label; one step darker clears it at 4.99:1 without changing the brand hue */
.watch .primary{background:#C92A2A;border-color:#C92A2A}
.note{color:var(--muted);font-size:16px}
.note p{margin:0 0 6px}
.list{margin:0;padding:0;list-style:none;display:grid;gap:12px}
.list a{display:block;padding:16px 20px;color:var(--text);text-decoration:none}
.list a:hover{background:var(--glass-hi)}
.list .d{font-family:var(--display);font-weight:700;font-size:24px;letter-spacing:.03em;text-transform:uppercase}
.list .s{display:block;color:var(--muted);font-size:16px;margin-top:2px}
.pager{display:flex;justify-content:space-between;gap:12px;margin-top:28px}
.pager a{color:var(--text);font-weight:600}
/* the hand-written CSS gives .links a and summary an explicit 3px ring; these
   generated controls had none and fell back to the browser default, which is
   weak against the glass backgrounds. Same convention, applied consistently. */
.nav a:focus-visible,.watch a:focus-visible,.list a:focus-visible,
.pager a:focus-visible,.skip:focus-visible{outline:3px solid #fff;outline-offset:2px}
/* WCAG 2.4.1: every page puts a banner and five nav links before the main
   landmark. Off-screen until focused, then visible for keyboard users. */
.skip{position:absolute;left:-9999px;top:0;z-index:10}
.skip:focus{left:8px;top:8px;padding:10px 16px;border-radius:999px;background:var(--bg);
color:var(--text);border:1px solid var(--edge);font:600 16px var(--body);text-decoration:none}
"""
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(os.path.join(OUT, "assets"))
open(os.path.join(OUT, "assets", "site.css"), "w", encoding="utf-8").write(css + EXTRA)
for f in ("og.png", "robots.txt"):
    if os.path.exists(f):
        shutil.copy(f, os.path.join(OUT, f))

head_keep = re.search(r'(<link rel="icon".*?rel="stylesheet">)', home, re.S).group(1)
NAV = [("/", "Home"), ("/bulletins/", "Bulletins"), ("/library/", "Library"),
       ("/products/", "Products"), ("/about/", "About")]
CUR = ' aria-current="page"'


def nav(cur):
    return '<nav class="nav" aria-label="Site">' + "".join(
        '<a href="%s"%s>%s</a>' % (h, CUR if h == cur else "", t) for h, t in NAV) + "</nav>"


FOOT = ("<footer><p>Inaam Ullah · Reward Heaven</p><p>" + e(TAGLINE) + "</p>"
        "<p>Narration in the videos is AI-generated · every figure checked against two independent sources</p></footer>")
urls = []


def page(path, title, desc, body, cur, extra_head=""):
    url = BASE + path
    urls.append(url)
    doc = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>%s</title>
<meta name="description" content="%s">
<meta name="author" content="Inaam Ullah">
<meta name="theme-color" content="#15181C">
<link rel="canonical" href="%s">
<meta property="og:type" content="article">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
<meta property="og:url" content="%s">
<meta property="og:image" content="%s/og.png">
<meta name="twitter:card" content="summary_large_image">
%s
<link rel="stylesheet" href="/assets/site.css">
%s
%s
</head>
<body>
%s
<div class="field" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
<header class="band"><p>Inaam Ullah · Reward Heaven</p></header>
%s
<main id="main">
%s
%s
</main>
</body>
</html>
""" % (e(title), e(desc), url, e(title), e(desc), url, BASE, head_keep, PLAUSIBLE, extra_head,
       SKIP, nav(cur), body, FOOT)
    d = os.path.join(OUT, path.strip("/"))
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(doc)


def pill(p):
    k = p.lower()
    if k not in VAR:
        return ""
    v = VAR[k]
    return '<span class="pill" style="--c:%s">%s</span>' % (PILL_INK.get(v, "var(--%s)" % v), e(p))


# ---------------------------------------------------------------- bulletins
days = [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob("data/bulletins/*.json"))]
built = []
for i, d in enumerate(days):
    dt, lead, text = d["date"], d["lead"], d["text"]
    body = ['<article class="page glass rise"><p class="kicker">Reward Heaven Bulletin · %s</p><h1>%s</h1>' % (nice(dt), e(lead)),
            '<p class="lead">%d developments, one line each. Every figure checked against two independent sources.</p></article>' % len(text)]
    links = d.get("links", {})
    if links:
        order = ["YouTube", "Facebook", "Instagram", "TikTok"]
        body.append('<section aria-labelledby="w-h"><h2 id="w-h">Watch the Video Bulletin</h2><ul class="watch">' + "".join(
            '<li><a class="%s" href="%s" rel="noopener" target="_blank">%s</a></li>' % ("primary" if n == "YouTube" else "", e(links[n]), n)
            for n in order if n in links) + "</ul>")
        if d.get("video"):
            body.append('<p class="note">In the video: ' + " · ".join(e(v) for v in d["video"]) + ".</p>")
        body.append("</section>")
    body.append('<section aria-labelledby="t-h"><h2 id="t-h">The Text Bulletin</h2><ul class="items">')
    for pl, subj, txt in text:
        body.append('<li class="glass">%s<p>%s%s</p></li>' % (pill(pl), ("<b>%s:</b> " % e(subj)) if subj else "", e(txt)))
    body.append("</ul></section>")
    body.append('<section class="note" aria-label="Sources and transparency"><h2>Sources</h2>'
                + ("<p>%s</p>" % e(d["sources"]) if d.get("sources") else "")
                + "".join("<p>%s</p>" % e(n) for n in d.get("notes", []))
                + "<p>Corrections are posted in the comments of the video.</p></section>")
    prev_ = days[i - 1]["date"] if i > 0 else None
    next_ = days[i + 1]["date"] if i + 1 < len(days) else None
    body.append('<nav class="pager" aria-label="Other bulletins">'
                + ('<a href="/bulletins/%s/">← %s</a>' % (prev_, nice(prev_)) if prev_ else "<span></span>")
                + ('<a href="/bulletins/%s/">%s →</a>' % (next_, nice(next_)) if next_ else "<span></span>") + "</nav>")
    ld = {"@context": "https://schema.org", "@type": "Article",
          "headline": "Reward Heaven Bulletin · %s: %s" % (nice(dt), lead), "datePublished": dt,
          "author": {"@type": "Person", "name": "Inaam Ullah", "url": BASE + "/"},
          "mainEntityOfPage": "%s/bulletins/%s/" % (BASE, dt)}
    page("/bulletins/%s/" % dt, "Reward Heaven Bulletin · %s: %s" % (nice(dt), lead),
         "%d developments in AI, code, chess and statecraft for %s, one line each, with sources." % (len(text), nice(dt)),
         "\n".join(body), "/bulletins/",
         '<script type="application/ld+json">%s</script>' % json.dumps(ld, ensure_ascii=False))
    built.append((dt, lead, len(text)))

built.sort(reverse=True)
page("/bulletins/", "Reward Heaven Bulletins · daily archive",
     "Every Reward Heaven daily bulletin: AI, code, chess and statecraft, made clear, with sources.",
     '<article class="page glass rise"><p class="kicker">Archive</p><h1>Daily bulletins</h1>'
     '<p class="lead">One video and one text brief a day. Newest first.</p></article>'
     '<section aria-label="All bulletins"><h2>All bulletins</h2><ul class="list">' + "".join(
         '<li><a class="glass" href="/bulletins/%s/"><span class="d">%s</span><span class="s">%s · %d developments</span></a></li>'
         % (dt, nice(dt), e(lead), n) for dt, lead, n in built) + "</ul></section>", "/bulletins/")

# ---------------------------------------------------------------- library, products, about
pub = json.load(open("data/library.json", encoding="utf-8")) if os.path.exists("data/library.json") else []
lib = ('<article class="page glass rise"><p class="kicker">Library</p><h1>Long-form explainers</h1>'
       '<p class="lead">Concepts explained in connected series, one clear step at a time.</p></article>')
if pub:
    lib += '<section><h2>Published</h2><ul class="list">' + "".join(
        '<li><a class="glass" href="%s" rel="noopener" target="_blank"><span class="d">%s</span><span class="s">%s</span></a></li>'
        % (e(r["url"]), e(r["title"]), e(r.get("pillar", ""))) for r in pub) + "</ul></section>"
else:
    lib += ('<section class="note"><h2>Coming soon</h2><p>The first long videos are in review. Each will appear here '
            'with its written version and sources.</p><p>Subscribe on YouTube to see them first.</p></section>')
lib += ('<ul class="watch"><li><a class="primary" href="https://www.youtube.com/@reward_heaven" rel="noopener" '
        'target="_blank">Subscribe on YouTube</a></li></ul>')
page("/library/", "Reward Heaven Library · long-form explainers",
     "Long-form explainers on AI, code, chess and statecraft, in connected series.", lib, "/library/")
page("/products/", "Reward Heaven Products", "Guides and templates from Reward Heaven.",
     '<article class="page glass rise"><p class="kicker">Products</p><h1>Guides and templates</h1>'
     '<p class="lead">Practical material built from the series, for people who want to apply it.</p></article>'
     '<section class="note"><h2>In preparation</h2><p>Nothing is on sale yet. The first product will be announced '
     'here and in the daily bulletin.</p></section>', "/products/")
page("/about/", "About Reward Heaven · Inaam Ullah",
     "What Reward Heaven publishes, how every figure is checked, and how corrections are handled.",
     '<article class="page glass rise"><p class="kicker">About</p><h1>How this is made</h1><p class="lead">' + e(TAGLINE) + "</p></article>"
     '<section class="note"><h2>The daily bulletin</h2><p>Every day: a one-minute video and a short text brief covering '
     "the day's most useful developments across eight topics.</p>"
     "<h2>Verification</h2><p>Every figure is checked against two independent sources before it is published. "
     "Sources are listed with each bulletin.</p>"
     "<h2>Transparency</h2><p>Narration in the videos is AI-generated. Corrections are posted in the comments of the "
     "video concerned.</p><p>Explainers on crypto and finance are educational, not financial advice.</p>"
     "<h2>Who publishes it</h2><p>Inaam Ullah, Vice President, Chess Federation of Pakistan.</p></section>", "/about/")

# ---------------------------------------------------------------- home: kept as designed, three insertions
# the main landmark is given its id BEFORE the stylesheet is injected: EXTRA is
# inserted into <style> in the head, so any "<main>" inside it would otherwise be
# the first match in document order and absorb this replacement instead
h = home.replace("<main>", '<main id="main">', 1)
h = h.replace("</style>", EXTRA + "</style>", 1)
band = '<header class="band"><p>Inaam Ullah · Reward Heaven</p></header>'
# the home source may carry its own hand-written menu (SEO pass); the generated one is canonical
h = re.sub(r"(?:<!--[^>]*-->\s*)?<nav class=\"nav\".*?</nav>\s*", "", h, flags=re.S)
h = h.replace(band, band + "\n" + nav("/"), 1)
# the home page keeps its hand-written head, so analytics is inserted into it directly
h = h.replace("</head>", PLAUSIBLE + "\n</head>", 1)
h = h.replace("<body>", "<body>\n" + SKIP, 1)
if built:
    dt, lead, n = built[0]
    latest = ('  <section aria-labelledby="lt-h">\n    <h2 id="lt-h">Latest bulletin</h2>\n    <ul class="list"><li>'
              '<a class="glass" href="/bulletins/%s/"><span class="d">%s</span><span class="s">%s · %d developments</span></a></li></ul>\n'
              '    <p class="note" style="margin-top:12px"><a href="/bulletins/" style="color:inherit">All bulletins →</a></p>\n  </section>\n\n'
              % (dt, nice(dt), e(lead), n))
    h = h.replace('  <section aria-labelledby="ch-h">', latest + '  <section aria-labelledby="ch-h">', 1)
assert h.count('class="nav"') == 1, "home page: menu bar not inserted"
assert h.count("Latest bulletin") == (1 if built else 0), "home page: latest block not inserted"
assert h.count("plausible.io/js/script") == 1, "home page: analytics not inserted"
# checked against the body alone: the same strings occur in the stylesheet
# comments in the head, which would otherwise satisfy these silently
_body = h.split("</head>", 1)[1]
assert _body.count('class="skip"') == 1, "home page: skip link not inserted"
assert _body.count('<main id="main">') == 1, "home page: main landmark not given an id"
assert _body.index('class="skip"') < _body.index('<main id="main">'), \
    "home page: skip link must precede the main landmark it targets"
open(os.path.join(OUT, "index.html"), "w", encoding="utf-8").write(h)
urls.insert(0, BASE + "/")

today = date.today().isoformat()
open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write(
    '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    + "".join("  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n" % (u, today) for u in urls) + "</urlset>\n")
print("pages built: %d | bulletin days: %s" % (len(urls), [b[0] for b in built]))
