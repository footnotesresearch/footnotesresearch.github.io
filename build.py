#!/usr/bin/env python3
"""Builds the site into the _site folder.

    python build.py                 # public build: published files only
    python build.py --drafts        # preview build: includes drafts, marked as such
    python build.py --serve         # preview build, then serve at http://localhost:8000

You normally never run this yourself: the GitHub workflow runs it on every
change you push and publishes the result.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
OUT = ROOT / "_site"

problems: list[str] = []
notices: list[str] = []


def problem(msg: str) -> None:
    problems.append(msg)


def notice(msg: str) -> None:
    notices.append(msg)


# ---------------------------------------------------------------- reading

FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.S)


def read_doc(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = FRONT.match(text)
    if not m:
        problem(f"{rel(path)}: missing the --- settings block at the top")
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        problem(f"{rel(path)}: the settings block has a formatting error: {e}")
        meta = {}
    return meta, m.group(2).strip()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def md_to_html(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "attr_list", "sane_lists", "toc"],
        extension_configs={"toc": {"permalink": False}},
        output_format="html5",
    )


def as_date(value, path: Path, field: str) -> dt.date | None:
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if value in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        problem(f"{rel(path)}: {field} must be a date like 2026-10-21, got {value!r}")
        return None


PLACEHOLDER = re.compile(r"\[[^\]]*\]")


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _strings(v)


def has_placeholder(*values) -> bool:
    """True if any text still contains a [bracketed placeholder].
    Footnote refs like [1] and Markdown links [text](url) don't count."""
    for s in _strings(values):
        s = re.sub(r"\[[^\]]*\]\(", "(", s)  # Markdown links
        if any(not re.fullmatch(r"\[\d+(, ?\d+)*\]", m) for m in PLACEHOLDER.findall(s)):
            return True
    return False


# ---------------------------------------------------------------- model

def load(include_drafts: bool):
    site = yaml.safe_load((ROOT / "site.yml").read_text(encoding="utf-8"))
    sectors = yaml.safe_load((ROOT / "sectors.yml").read_text(encoding="utf-8"))
    sector_by_slug = {s["slug"]: s for s in sectors}
    for s in sectors:
        s["companies"] = []

    def wanted(meta: dict, path: Path) -> bool:
        status = meta.get("status", "draft")
        if status not in ("draft", "published"):
            problem(f"{rel(path)}: status must be draft or published, got {status!r}")
            return False
        if status == "draft" and not include_drafts:
            notice(f"skipped draft: {rel(path)}")
            return False
        return True

    companies = {}
    for path in sorted((CONTENT / "companies").glob("*.md")):
        meta, body = read_doc(path)
        if not meta or not wanted(meta, path):
            continue
        slug = path.stem
        for field in ("name", "sector", "author_position"):
            if not meta.get(field):
                problem(f"{rel(path)}: missing {field}")
        if meta.get("sector") not in sector_by_slug:
            problem(f"{rel(path)}: sector {meta.get('sector')!r} is not in sectors.yml")
            continue
        sources = {s["id"]: s for s in meta.get("sources") or []}
        takeaways = meta.get("takeaways") or []
        for i, t in enumerate(takeaways, 1):
            for sid in t.get("sources") or []:
                if sid not in sources:
                    problem(f"{rel(path)}: takeaway {i} cites source {sid}, which isn't in the sources list")
            if not t.get("sources"):
                problem(f"{rel(path)}: takeaway {i} has no source. Every takeaway needs one.")
        if len(takeaways) > 12:
            notice(f"{rel(path)}: {len(takeaways)} takeaways. Consider trimming to the ten that matter most.")
        draft = meta.get("status") == "draft"
        if not draft and has_placeholder(meta, body):
            problem(f"{rel(path)}: still has [bracketed] placeholders but is marked published")
        data_files = []
        raw_files = meta.get("data_files") or []
        if not isinstance(raw_files, list) or not all(isinstance(d, dict) and d.get("file") for d in raw_files):
            problem(f"{rel(path)}: data_files must be a list of '- file: name.csv' entries (or [] for none)")
            raw_files = []
        for d in raw_files:
            src = CONTENT / "data" / slug / d["file"]
            if not src.exists():
                problem(f"{rel(path)}: data file {d['file']} not found in content/data/{slug}/")
                continue
            data_files.append({**d, "src": src, "url": f"/data/{slug}/{d['file']}"})
        c = {
            **meta,
            "slug": slug,
            "draft": draft,
            "path": path,
            "tier_key": str(meta.get("cap_tier") or "").strip().lower(),
            "url": f"/companies/{slug}/",
            "md_url": f"/companies/{slug}.md",
            "body_md": body,
            "body_html": md_to_html(body),
            "sector_info": sector_by_slug[meta["sector"]],
            "takeaways": takeaways,
            "sources": sorted(sources.values(), key=lambda s: s["id"]),
            "takeaways_as_of": as_date(meta.get("takeaways_as_of"), path, "takeaways_as_of"),
            "data_files": data_files,
            "reports": [],
        }
        companies[slug] = c
        sector_by_slug[meta["sector"]]["companies"].append(c)

    reports = []
    for path in sorted((CONTENT / "reports").glob("*.md")):
        meta, body = read_doc(path)
        if not meta or not wanted(meta, path):
            continue
        for field in ("title", "company", "date", "summary"):
            if not meta.get(field):
                problem(f"{rel(path)}: missing {field}")
        company = companies.get(meta.get("company"))
        if not company:
            problem(f"{rel(path)}: company {meta.get('company')!r} has no published page in content/companies/")
            continue
        date = as_date(meta.get("date"), path, "date")
        if date and date > dt.date.today():
            problem(f"{rel(path)}: date {date} is in the future")
        slug = path.stem
        draft = meta.get("status") == "draft"
        if not draft and has_placeholder(meta, body):
            problem(f"{rel(path)}: still has [bracketed] placeholders but is marked published")
        r = {
            **meta,
            "slug": slug,
            "draft": draft,
            "path": path,
            "date": date,
            "updated": as_date(meta.get("updated"), path, "updated"),
            "url": f"/reports/{slug}/",
            "md_url": f"/reports/{slug}.md",
            "history_url": f"{site['repo_url'].rstrip('/')}/commits/{site.get('repo_branch', 'main')}/{rel(path)}",
            "company_info": company,
            "sources": sorted(meta.get("sources") or [], key=lambda s: s["id"]),
            "body_md": body,
            "body_html": md_to_html(body),
        }
        reports.append(r)
        company["reports"].append(r)

    reports.sort(key=lambda r: (r["date"] or dt.date.min, r["slug"]), reverse=True)
    for c in companies.values():
        c["reports"].sort(key=lambda r: r["date"] or dt.date.min, reverse=True)
        dates = [d for d in [c["takeaways_as_of"]] + [r["updated"] or r["date"] for r in c["reports"]] if d]
        c["last_updated"] = max(dates) if dates else None
    for s in sectors:
        s["companies"].sort(key=lambda c: c["name"])

    pages = []
    for path in sorted((CONTENT / "pages").glob("*.md")):
        meta, body = read_doc(path)
        slug = meta.get("slug", path.stem)
        pages.append({**meta, "slug": slug, "url": f"/{slug}/", "md_url": f"/{slug}.md",
                      "body_md": body, "body_html": md_to_html(body)})

    return site, sectors, companies, reports, pages


# ---------------------------------------------------------------- plain text

def tier_label(c: dict) -> str:
    t = str(c.get("cap_tier") or "").strip().lower()
    return {"small": "Small cap", "mid": "Mid cap", "large": "Large cap"}.get(t, c.get("cap_tier") or "Not classified")


def company_markdown(site, c, abs_url) -> str:
    lines = [f"# {c['name']}", ""]
    lines += [
        f"- Sector (NSE): {c['sector_info']['name']}",
        f"- Market-cap tier (AMFI): {tier_label(c)}" + (f" ({c['cap_tier_source']})" if c.get("cap_tier_source") else ""),
    ]
    if c.get("nse_symbol"):
        lines.append(f"- NSE symbol: {c['nse_symbol']}")
    if c.get("bse_code"):
        lines.append(f"- BSE code: {c['bse_code']}")
    lines.append(f"- Author's position: {c['author_position']}")
    if c["last_updated"]:
        lines.append(f"- Last updated: {c['last_updated'].isoformat()}")
    lines.append(f"- Web page: {abs_url(c['url'])}")
    lines.append("")
    if c["takeaways"]:
        as_of = f" (as of {c['takeaways_as_of'].isoformat()})" if c["takeaways_as_of"] else ""
        lines += [f"## Key takeaways{as_of}", ""]
        for t in c["takeaways"]:
            refs = "".join(f"[{s}]" for s in t.get("sources") or [])
            topic = f"{t['topic']}: " if t.get("topic") else ""
            lines.append(f"- {topic}{t['text']} {refs}".rstrip())
        lines.append("")
    if c["body_md"]:
        lines += ["## About the business", "", c["body_md"], ""]
    if c["reports"]:
        lines += ["## Reports", ""]
        for r in c["reports"]:
            lines.append(f"- {r['date'].isoformat()}: [{r['title']}]({abs_url(r['md_url'])}). {r['summary'].strip()}")
        lines.append("")
    if c["sources"]:
        lines += ["## Sources", ""]
        for s in c["sources"]:
            lines.append(f"[{s['id']}] {s['label']}: {s.get('url', '')}")
        lines.append("")
    lines += ["---", site["disclaimer"].strip(), ""]
    return "\n".join(lines)


def report_markdown(site, r, abs_url) -> str:
    c = r["company_info"]
    lines = [f"# {r['title']}", ""]
    lines += [
        f"- Company: {c['name']} ({c['sector_info']['name']}, {tier_label(c)})",
        f"- Published: {r['date'].isoformat()}",
    ]
    if r["updated"]:
        lines.append(f"- Updated: {r['updated'].isoformat()}")
    lines += [
        f"- Author: {site['author']}",
        f"- Author's position in this company: {c['author_position']}",
        f"- Web page: {abs_url(r['url'])}",
        f"- Change history: {r['history_url']}",
        "",
        "## Summary", "", r["summary"].strip(), "",
        r["body_md"], "",
    ]
    if r["sources"]:
        lines += ["## Sources", ""]
        for s in r["sources"]:
            lines.append(f"[{s['id']}] {s['label']}: {s.get('url', '')}")
        lines.append("")
    lines += ["---", site["disclaimer"].strip(), ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- build

def build(include_drafts: bool, site_url: str) -> int:
    site, sectors, companies, reports, pages = load(include_drafts)
    site_url = (site_url or site.get("site_url") or "").rstrip("/")
    base = urlparse(site_url).path.rstrip("/") if site_url else ""

    def url(path: str) -> str:
        return base + path

    def abs_url(path: str) -> str:
        return (site_url + path) if site_url else path

    def fix_links(body: str) -> str:
        return re.sub(r'(href|src)="/(?!/)', lambda m: f'{m.group(1)}="{base}/', body)

    for c in companies.values():
        c["body_html"] = fix_links(c["body_html"])
    for r in reports:
        r["body_html"] = fix_links(r["body_html"])
    for p in pages:
        p["body_html"] = fix_links(p["body_html"])

    if problems:
        print("\nThe site was NOT built. Fix these first:\n")
        for p in problems:
            print("  •", p)
        print()
        return 1

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "static", OUT / "static")

    env = Environment(loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html"]),
                      trim_blocks=True, lstrip_blocks=True)
    env.filters["nicedate"] = lambda d: f"{d.day} {d:%b %Y}" if d else ""
    env.filters["iso"] = lambda d: d.isoformat() if d else ""
    env.filters["tier"] = tier_label
    env.filters["jsonld"] = lambda obj: json.dumps(obj, ensure_ascii=False, indent=2).replace("</", "<\\/")
    env.globals.update(site=site, url=url, abs_url=abs_url, sectors=sectors, preview=include_drafts,
                       build_date=dt.date.today())

    def render(template: str, out_path: str, **ctx) -> None:
        dest = OUT / out_path.lstrip("/")
        if out_path.endswith("/"):
            dest = dest / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(env.get_template(template).render(**ctx), encoding="utf-8")

    def write(out_path: str, text: str) -> None:
        dest = OUT / out_path.lstrip("/")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")

    org = {"@context": "https://schema.org", "@type": "Organization", "name": site["name"],
           "description": site["description"].strip(), "url": abs_url("/")}

    render("home.html", "/", reports=reports[:12], companies=companies, jsonld=org, page_path="/")
    render("sectors.html", "/sectors/", page_path="/sectors/")
    for s in sectors:
        render("sector.html", f"/sectors/{s['slug']}/", sector=s, page_path=f"/sectors/{s['slug']}/")
    render("archive.html", "/archive/", reports=reports, page_path="/archive/")

    for c in companies.values():
        md = company_markdown(site, c, abs_url)
        c["md_text"] = md
        jsonld = {
            "@context": "https://schema.org", "@type": "WebPage", "name": c["name"],
            "url": abs_url(c["url"]), "inLanguage": site.get("language", "en"),
            "dateModified": c["last_updated"].isoformat() if c["last_updated"] else None,
            "author": {"@type": "Person", "name": site["author"]},
            "about": {"@type": "Corporation", "name": c["name"],
                      "tickerSymbol": f"NSE:{c['nse_symbol']}" if c.get("nse_symbol") else None,
                      "industry": c["sector_info"]["name"]},
        }
        render("company.html", c["url"], c=c, jsonld=jsonld, page_path=c["url"])
        write(c["md_url"], md)
        for d in c["data_files"]:
            dest = OUT / d["url"].lstrip("/")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(d["src"], dest)

    for r in reports:
        md = report_markdown(site, r, abs_url)
        r["md_text"] = md
        c = r["company_info"]
        jsonld = {
            "@context": "https://schema.org", "@type": "Report", "headline": r["title"],
            "description": r["summary"].strip(), "url": abs_url(r["url"]),
            "datePublished": r["date"].isoformat(),
            "dateModified": (r["updated"] or r["date"]).isoformat(),
            "inLanguage": site.get("language", "en"),
            "author": {"@type": "Person", "name": site["author"]},
            "publisher": {"@type": "Organization", "name": site["name"]},
            "about": {"@type": "Corporation", "name": c["name"],
                      "tickerSymbol": f"NSE:{c['nse_symbol']}" if c.get("nse_symbol") else None,
                      "industry": c["sector_info"]["name"]},
            "citation": [s.get("url") for s in r["sources"] if s.get("url")],
        }
        render("report.html", r["url"], r=r, c=c, jsonld=jsonld, page_path=r["url"])
        write(r["md_url"], md)

    for p in pages:
        render("page.html", p["url"], p=p, page_path=p["url"])
        write(p["md_url"], f"# {p['title']}\n\n{p['body_md']}\n")

    # ---- machine-readable files
    llms = [f"# {site['name']}", "", f"> {site['description'].strip()}", "",
            "Each page below has a plain-text Markdown version. Dates are publication dates; "
            f"the public change history is at {site['repo_url']}. When citing, give the page and its date.", ""]
    for s in sectors:
        if not s["companies"]:
            continue
        llms += [f"## {s['name']}", ""]
        for c in s["companies"]:
            llms.append(f"- [{c['name']}]({abs_url(c['md_url'])}): {tier_label(c)}. {c.get('summary', '').strip()}")
        llms.append("")
    if reports:
        llms += ["## Reports, newest first", ""]
        for r in reports:
            llms.append(f"- [{r['title']}]({abs_url(r['md_url'])}): published {r['date'].isoformat()}. {r['summary'].strip()}")
        llms.append("")
    llms += ["## Optional", "", f"- [Full archive in one file]({abs_url('/llms-full.txt')})",
             f"- [Structured index (JSON)]({abs_url('/reports.json')})",
             f"- [About and disclaimer]({abs_url('/about.md')})", ""]
    write("/llms.txt", "\n".join(llms))

    full = [f"# {site['name']}: full archive", "", site["description"].strip(), ""]
    for c in sorted(companies.values(), key=lambda c: c["name"]):
        full += ["", "=" * 72, "", c["md_text"]]
    for r in reports:
        full += ["", "=" * 72, "", r["md_text"]]
    write("/llms-full.txt", "\n".join(full))

    index = {
        "name": site["name"], "description": site["description"].strip(), "generated": dt.date.today().isoformat(),
        "history": site["repo_url"], "disclaimer": site["disclaimer"].strip(),
        "companies": [{
            "name": c["name"], "slug": c["slug"], "nse_symbol": c.get("nse_symbol"), "bse_code": c.get("bse_code"),
            "sector": c["sector_info"]["name"], "cap_tier": tier_label(c), "author_position": c["author_position"],
            "url": abs_url(c["url"]), "text_url": abs_url(c["md_url"]),
            "last_updated": c["last_updated"].isoformat() if c["last_updated"] else None,
            "takeaways": [{"topic": t.get("topic"), "text": t["text"],
                           "sources": [next((s for s in c["sources"] if s["id"] == sid), {"id": sid}) for sid in t.get("sources") or []]}
                          for t in c["takeaways"]],
            "data_files": [abs_url(d["url"]) for d in c["data_files"]],
        } for c in companies.values()],
        "reports": [{
            "title": r["title"], "company": r["company"], "published": r["date"].isoformat(),
            "updated": r["updated"].isoformat() if r["updated"] else None, "summary": r["summary"].strip(),
            "url": abs_url(r["url"]), "text_url": abs_url(r["md_url"]), "history": r["history_url"],
            "sources": r["sources"],
        } for r in reports],
    }
    write("/reports.json", json.dumps(index, ensure_ascii=False, indent=2, default=str))

    robots = ["# Search engines and AI tools are welcome to read this site.", "User-agent: *", "Allow: /", ""]
    for bot in ("GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "Claude-User", "Claude-SearchBot",
                "PerplexityBot", "Google-Extended", "Applebot-Extended", "CCBot"):
        robots += [f"User-agent: {bot}", "Allow: /", ""]
    if site_url:
        robots.append(f"Sitemap: {abs_url('/sitemap.xml')}")
    write("/robots.txt", "\n".join(robots) + "\n")

    urls = [("/", None), ("/sectors/", None), ("/archive/", None)]
    urls += [(f"/sectors/{s['slug']}/", None) for s in sectors]
    urls += [(c["url"], c["last_updated"]) for c in companies.values()]
    urls += [(r["url"], r["updated"] or r["date"]) for r in reports]
    urls += [(p["url"], None) for p in pages]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u, d in urls:
        sm.append(f"  <url><loc>{xml_escape(abs_url(u))}</loc>" + (f"<lastmod>{d.isoformat()}</lastmod>" if d else "") + "</url>")
    sm.append("</urlset>")
    write("/sitemap.xml", "\n".join(sm) + "\n")

    feed_updated = reports[0]["date"].isoformat() if reports else dt.date.today().isoformat()
    feed = ['<?xml version="1.0" encoding="utf-8"?>', '<feed xmlns="http://www.w3.org/2005/Atom">',
            f"  <title>{xml_escape(site['name'])}</title>", f"  <subtitle>{xml_escape(site['tagline'])}</subtitle>",
            f'  <link href="{xml_escape(abs_url("/"))}"/>', f"  <id>{xml_escape(abs_url('/'))}</id>",
            f"  <updated>{feed_updated}T00:00:00Z</updated>",
            f"  <author><name>{xml_escape(site['author'])}</name></author>"]
    for r in reports:
        feed += ["  <entry>", f"    <title>{xml_escape(r['title'])}</title>",
                 f'    <link href="{xml_escape(abs_url(r["url"]))}"/>', f"    <id>{xml_escape(abs_url(r['url']))}</id>",
                 f"    <published>{r['date'].isoformat()}T00:00:00Z</published>",
                 f"    <updated>{(r['updated'] or r['date']).isoformat()}T00:00:00Z</updated>",
                 f"    <summary>{xml_escape(r['summary'].strip())}</summary>", "  </entry>"]
    feed.append("</feed>")
    write("/feed.xml", "\n".join(feed) + "\n")

    render("404.html", "/404.html", page_path="/404.html")
    (OUT / ".nojekyll").write_text("")

    for n in notices:
        print("  note:", n)
    mode = "preview (drafts included)" if include_drafts else "public"
    print(f"Built {mode} site: {len(companies)} companies, {len(reports)} reports → {OUT}")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drafts", action="store_true", help="include drafts (for previewing only)")
    ap.add_argument("--serve", action="store_true", help="build with drafts and serve on localhost:8000")
    ap.add_argument("--site-url", default="", help="full public address, e.g. https://name.github.io/footnote")
    args = ap.parse_args()
    code = build(args.drafts or args.serve, args.site_url)
    if code or not args.serve:
        sys.exit(code)
    import functools
    import http.server
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
    print("Preview at http://localhost:8000  (Ctrl+C to stop)")
    http.server.ThreadingHTTPServer(("127.0.0.1", 8000), handler).serve_forever()


if __name__ == "__main__":
    main()
