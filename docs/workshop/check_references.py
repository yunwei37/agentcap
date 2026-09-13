#!/usr/bin/env python3
"""Check every active workshop citation against live primary metadata (stdlib).

Run: python3 check_references.py
Outputs JSON lines with all checked fields and evidence URLs; exits nonzero on
missing/duplicate keys, metadata mismatches, or inaccessible sources. Conference
web records below are transcribed from the linked official pages and checked
against their live text. They are not inferred from the bibliography under test.
"""
import concurrent.futures
from datetime import datetime, timezone
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

BASE = Path(__file__).resolve().parent


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "IntentCap-citation-audit/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read().decode("utf-8"), response.url
        except urllib.error.HTTPError as error:
            if error.code not in {429, 502, 503, 504} or attempt == 2:
                raise
            time.sleep(min(30, int(error.headers.get("Retry-After", 3 * (attempt + 1)))))


def normal(value):
    value = html.unescape(value).replace(r"\tau", "tau").replace("τ", "tau")
    value = re.sub(r"\\(?:url|texttt|textsc)\s*", "", value)
    value = re.sub(r"\\[\"'`^~ckuvHr=.]+", "", value)
    value = unicodedata.normalize("NFKD", value)
    return re.sub(r"[^a-z0-9]", "", value.lower())


def author_normal(name):
    # BibTeX's Last, First notation is equivalent to First Last; list order is
    # preserved. Full given names are compared, not merely initials.
    if "," in name:
        last, first = name.split(",", 1)
        name = first + " " + last
    return normal(name)


def parse_bib(text):
    entries = {}
    for match in re.finditer(r"@\w+\s*\{\s*([^,]+),", text):
        key = match[1].strip()
        if key in entries:
            raise ValueError("duplicate key: " + key)
        start, depth, end = match.end(), 1, match.end()
        while depth:
            if text[end] == "{" and text[end - 1] != "\\":
                depth += 1
            elif text[end] == "}" and text[end - 1] != "\\":
                depth -= 1
            end += 1
        body = text[start:end - 1]
        fields = {}
        pos = 0
        while match_field := re.search(r"(\w+)\s*=\s*\{", body[pos:]):
            field = match_field[1].lower()
            left = pos + match_field.end()
            right, depth = left, 1
            while depth:
                if body[right] == "{" and body[right - 1] != "\\":
                    depth += 1
                elif body[right] == "}" and body[right - 1] != "\\":
                    depth -= 1
                right += 1
            fields[field] = body[left:right - 1]
            pos = right
        entries[key] = fields
    return entries


class Meta(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.values = {}
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and "name" in attrs and "content" in attrs:
            self.values.setdefault(attrs["name"], []).append(attrs["content"])


# Manually transcribed official records for sources lacking stable full-field
# machine-readable metadata. Source pages and field witnesses are re-fetched.
WEB = {
    "capsicum": {
        "url": "https://www.usenix.org/conference/usenixsecurity10/capsicum-practical-capabilities-unix",
        "title": "Capsicum: Practical Capabilities for UNIX",
        "authors": ["Robert N. M. Watson", "Jonathan Anderson", "Ben Laurie", "Kris Kennaway"],
        "venue": "19th USENIX Security Symposium (USENIX Security 10)", "year": "2010"},
    "eim-bpftime": {
        "url": "https://www.usenix.org/conference/osdi25/presentation/zheng-yusheng",
        "title": "Extending Applications Safely and Efficiently",
        "authors": ["Yusheng Zheng", "Tong Yu", "Yiwei Yang", "Yanpeng Hu", "Xiaozheng Lai", "Dan Williams", "Andi Quinn"],
        "venue": "19th USENIX Symposium on Operating Systems Design and Implementation (OSDI 25)", "year": "2025"},
    "dualllm": {
        "url": "https://simonwillison.net/2023/Apr/25/dual-llm-pattern/",
        "title": "The Dual LLM pattern for building AI assistants that can resist prompt injection",
        "authors": ["Simon Willison"], "venue": "Simon Willison's Weblog", "year": "2023"},
    "openai-skills": {
        "url": "https://learn.chatgpt.com/docs/build-skills",
        "title": "Build skills", "authors": ["OpenAI"],
        "venue": "ChatGPT Learn", "year": "2026", "date_kind": "access year (living documentation)"},
    "mcp-spec": {
        "url": "https://modelcontextprotocol.io/specification/2025-06-18",
        "title": "Specification", "authors": ["Model Context Protocol"],
        "venue": "Model Context Protocol specification, version 2025-06-18", "year": "2025"},
}


def primary(key, bib):
    doi = bib.get("doi", "")
    if doi.lower().startswith("10.48550/arxiv."):
        aid = doi[len("10.48550/arXiv."):]
        url = "https://arxiv.org/abs/" + aid
        page, resolved = fetch(url)
        meta = Meta(page).values
        # First submission year is the bibliographic year, not revision year.
        date = meta.get("citation_date", [""])[0]
        return {"title": meta["citation_title"][0], "authors": meta["citation_author"],
                "venue": "arXiv preprint arXiv:" + aid, "year": date[:4],
                "doi": doi, "source": url, "resolved_url": resolved,
                "method": "live arXiv citation meta tags"}
    if key in WEB:
        record = dict(WEB[key])
        page, resolved = fetch(record["url"])
        plain = normal(re.sub("<[^>]+>", " ", page))
        witnesses = [record["title"]] + record["authors"]
        if key in {"capsicum", "eim-bpftime"}:
            witnesses += [record["venue"], record["year"]]
        absent = [s for s in witnesses if normal(s) not in plain]
        if absent:
            raise ValueError("primary page lacks expected field witnesses: " + repr(absent))
        record.update(source=record.pop("url"), resolved_url=resolved,
                      method="official-page transcription, live title and full author witnesses")
        return record
    url = "https://api.crossref.org/works/" + doi
    raw, resolved = fetch(url)
    msg = json.loads(raw)["message"]
    authors = [(a.get("given", "") + " " + a["family"]).strip() for a in msg["author"]]
    record = {"title": msg["title"][0], "authors": authors,
              "venue": msg["container-title"][0], "year": str(msg["published"]["date-parts"][0][0]),
              "doi": msg["DOI"], "source": url, "primary_url": "https://doi.org/" + doi,
              "method": "live publisher-deposited Crossref metadata"}
    if key == "isolategpt":
        # Crossref omits 'Agentic'; authoritative NDSS final PDF and page agree.
        official = "https://www.ndss-symposium.org/ndss-paper/isolategpt-an-execution-isolation-architecture-for-llm-based-agentic-systems/"
        page, _ = fetch(official)
        title = "IsolateGPT: An Execution Isolation Architecture for LLM-Based Agentic Systems"
        assert normal(title) in normal(re.sub("<[^>]+>", " ", page))
        record.update(title=title, title_source=official,
                      title_pdf="https://www.ndss-symposium.org/wp-content/uploads/2025-1131-paper.pdf")
    if key == "saltzer-schroeder":
        # IEEE's deposit abbreviates given names. The authors' MIT-hosted paper
        # explicitly gives their full names; verify these rather than accepting
        # arbitrary names with matching initials.
        official = "https://web.mit.edu/Saltzer/www/publications/protection/"
        page, _ = fetch(official)
        authors = ["Jerome H. Saltzer", "Michael D. Schroeder"]
        assert all(normal(a) in normal(re.sub("<[^>]+>", " ", page)) for a in authors)
        record.update(authors=authors, author_source=official)
    return record


def check(item):
    key, bib = item
    try:
        record = primary(key, bib)
        authors = re.split(r"\s+and\s+", bib["author"])
        venue = bib.get("journal", bib.get("booktitle", bib.get("howpublished", "")))
        if key in WEB and key not in {"capsicum", "eim-bpftime"}:
            # Web pages are not conference/journal publications: their official
            # URL identifies the publishing site, not an invented booktitle.
            venue_ok = WEB[key]["url"] in venue
        else:
            venue_ok = normal(venue) == normal(record["venue"])
        fields = {
            "title": normal(bib["title"]) == normal(record["title"]),
            "authors_full_and_order": [author_normal(a) for a in authors] == [author_normal(a) for a in record["authors"]],
            "venue": venue_ok, "year": bib["year"] == record["year"],
            "primary_identifier": normal(bib.get("doi", "")) == normal(record.get("doi", "")) if "doi" in record else record["source"] in (bib.get("url", "") + venue),
        }
        return {"key": key, "status": "PASS" if all(fields.values()) else "FAIL",
                "fields": fields, "primary_record": record,
                "bib_record": {"title": bib["title"], "authors": authors, "venue": venue, "year": bib["year"]}}
    except Exception as error:
        return {"key": key, "status": "FAIL", "error": str(error)}


def main():
    tex = re.sub(r"(?m)(?<!\\)%.*$", "", (BASE / "main.tex").read_text(encoding="utf-8"))
    cites = sorted({key.strip() for group in re.findall(r"\\cite\w*\{([^}]+)\}", tex) for key in group.split(",")})
    bib = parse_bib((BASE / "references.bib").read_text(encoding="utf-8"))
    labels = re.findall(r"\\label\{([^}]+)\}", tex)
    refs = re.findall(r"\\(?:ref|eqref|autoref)\{([^}]+)\}", tex)
    structural = {"cited": len(cites), "bib_entries": len(bib), "missing_keys": sorted(set(cites) - bib.keys()),
                  "unused_keys": sorted(bib.keys() - set(cites)), "undefined_crossrefs": sorted(set(refs) - set(labels)),
                  "duplicate_labels": sorted({label for label in labels if labels.count(label) > 1})}
    print(json.dumps({"checked_at": datetime.now(timezone.utc).isoformat(), "structure": structural}))
    if structural["missing_keys"]:
        return 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(check, [(key, bib[key]) for key in cites]))
    for result in results:
        print(json.dumps(result))
    failures = sum(r["status"] != "PASS" for r in results)
    print(json.dumps({"summary": {"pass": len(results) - failures, "fail": failures}}))
    return int(bool(failures or structural["undefined_crossrefs"] or structural["duplicate_labels"]))


if __name__ == "__main__":
    sys.exit(main())
