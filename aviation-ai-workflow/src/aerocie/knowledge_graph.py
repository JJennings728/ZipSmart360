"""AeroCIE-009 | Offline, evidence-linked research knowledge graph.

Research-only: no legal determination, inferred regulatory applicability,
client release, external fetch, automatic LLM extraction or cloud deployment.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import urlsplit

from .reviewer_packet import snapshot

DEFAULT_DB = Path("build/aerocie/knowledge_graph.sqlite3")
DEFAULT_SOURCE_DB = Path("build/aerocie/federal_register.sqlite3")
IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{2,119}$")
NODE_TYPES = ("ORGANIZATION", "AIRCRAFT", "COMPONENT", "PUBLICATION", "EVENT",
              "REGULATION", "TOPIC", "FACILITY", "OTHER")
PREDICATES = ("MENTIONS", "REFERENCES", "ASSOCIATED_WITH", "RESEARCH_RELATED_TO")
MAX_TEXT_BYTES = 2_000_000


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def checked(value: str, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{label} must contain 1 to {limit} characters")
    if any(ord(c) < 32 and c not in "\t\n" for c in value):
        raise ValueError(f"{label} contains control characters")
    return value.strip()


def check_id(value: str) -> str:
    if not isinstance(value, str) or not IDENT.fullmatch(value):
        raise ValueError("IDs must be 3–120 safe characters: letters, numbers, . _ : -")
    return value


def source_url(value: str) -> str:
    value = checked(value, "Source URL", 1500)
    p = urlsplit(value)
    if p.scheme != "https" or not p.hostname or p.username or p.password or any(ord(c) < 33 for c in value):
        raise ValueError("Source must have a valid HTTPS URL without credentials")
    return value


def _guard_db(db: Path, source_db: Path = DEFAULT_SOURCE_DB) -> None:
    if db.resolve() == source_db.resolve() or (db.exists() and source_db.exists() and db.samefile(source_db)):
        raise ValueError("Graph and Federal Register collector must be distinct databases")
    if db.is_file():
        with closing(sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if existing.intersection({"document_snapshots", "change_events", "obligation_candidates", "candidate_events"}):
                raise ValueError("Refusing to write into existing collector or candidate-register database")


def connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def initialize(db: Path, source_db: Path = DEFAULT_SOURCE_DB) -> None:
    _guard_db(db, source_db)
    db.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(db)) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS kg_documents (
              id TEXT PRIMARY KEY, title TEXT NOT NULL,
              kind TEXT NOT NULL CHECK(kind IN ('LOCAL_TEXT','FR_METADATA')),
              source_url TEXT NOT NULL, source_doc_number TEXT,
              content TEXT NOT NULL, sha256 TEXT NOT NULL,
              recorded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS kg_nodes (
              id TEXT PRIMARY KEY, kind TEXT NOT NULL,
              label TEXT NOT NULL, recorded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS kg_edges (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              from_id TEXT NOT NULL REFERENCES kg_nodes(id),
              to_id TEXT NOT NULL REFERENCES kg_nodes(id),
              predicate TEXT NOT NULL, document_id TEXT NOT NULL REFERENCES kg_documents(id),
              document_sha256 TEXT NOT NULL,
              exact_excerpt TEXT NOT NULL, locator TEXT NOT NULL,
              actor TEXT NOT NULL, recorded_at TEXT NOT NULL,
              state TEXT NOT NULL DEFAULT 'PROPOSED_RESEARCH_ONLY'
                CHECK(state='PROPOSED_RESEARCH_ONLY'),
              UNIQUE(from_id,to_id,predicate,document_id,exact_excerpt,locator)
            );
            CREATE INDEX IF NOT EXISTS kg_edges_from ON kg_edges(from_id);
            CREATE INDEX IF NOT EXISTS kg_edges_to ON kg_edges(to_id);
            CREATE INDEX IF NOT EXISTS kg_edges_evidence ON kg_edges(document_id);
        """)
        conn.commit()


def import_text(db: Path, *, doc_id: str, title: str, url: str,
                text: str, kind: str = "LOCAL_TEXT", doc_number: str | None = None,
                source_db: Path = DEFAULT_SOURCE_DB) -> dict:
    check_id(doc_id)
    checked(title, "Title", 300)
    source_url(url)
    if kind not in ("LOCAL_TEXT", "FR_METADATA"):
        raise ValueError("Unsupported document kind")
    if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > MAX_TEXT_BYTES:
        raise ValueError("Source text must be nonempty and at most 2 MB")
    if kind == "FR_METADATA":
        snap = snapshot(source_db, doc_number or "")
        if snap["fingerprint"] != digest(text) or snap["record"].get("html_url") != url:
            raise ValueError("Pinned Federal Register metadata does not match collector snapshot")
    fingerprint = digest(text)
    initialize(db, source_db)
    with closing(connect(db)) as conn:
        with conn:
            prior = conn.execute("SELECT sha256,title,source_url,kind,source_doc_number FROM kg_documents WHERE id=?", (doc_id,)).fetchone()
            if prior:
                if (prior[0],prior[1],prior[2],prior[3],prior[4]) != (fingerprint,title.strip(),url,kind,doc_number):
                    raise ValueError("Document ID already pinned to different content or provenance; use a versioned ID")
                return {"id": doc_id, "sha256": fingerprint, "event": "existing_same_bytes"}
            conn.execute("""INSERT INTO kg_documents
                (id,title,kind,source_url,source_doc_number,content,sha256,recorded_at)
                VALUES (?,?,?,?,?,?,?,?)""",
                (doc_id, title.strip(), kind, url, doc_number, text, fingerprint, now()))
    return {"id": doc_id, "sha256": fingerprint, "event": "imported"}


def import_federal_register(db: Path, source_db: Path, document_number: str) -> dict:
    """Import existing *published metadata*, not governing full legal text."""
    s = snapshot(source_db, document_number)
    rec = s["record"]
    url = rec.get("html_url")
    if not isinstance(url, str) or not url.startswith("https://www.federalregister.gov/"):
        raise ValueError("Federal Register publication must have official HTTPS URL")
    # This exact canonical format matches the collector's original payload contract.
    content = json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if digest(content) != s["fingerprint"]:
        raise ValueError("Canonical metadata does not match original fingerprint")
    return import_text(db, doc_id=f"fr:{document_number}:{s['fingerprint'][:12]}",
                       title=str(rec.get("title") or document_number)[:300], url=url,
                       text=content, kind="FR_METADATA", doc_number=document_number,
                       source_db=source_db)


def add_node(db: Path, *, node_id: str, kind: str, label: str,
             source_db: Path = DEFAULT_SOURCE_DB) -> dict:
    check_id(node_id)
    if kind not in NODE_TYPES:
        raise ValueError("Unsupported node kind")
    label = checked(label, "Node label", 240)
    initialize(db, source_db)
    with closing(connect(db)) as conn:
        with conn:
            prior = conn.execute("SELECT kind,label FROM kg_nodes WHERE id=?", (node_id,)).fetchone()
            if prior:
                if (prior[0], prior[1]) != (kind, label):
                    raise ValueError("Existing node ID cannot be silently redefined")
                return {"id": node_id, "event": "existing_same_values"}
            conn.execute("INSERT INTO kg_nodes VALUES (?,?,?,?)", (node_id, kind, label, now()))
    return {"id": node_id, "event": "created"}


def add_edge(db: Path, *, from_id: str, to_id: str, predicate: str, doc_id: str,
             excerpt: str, locator: str, actor: str,
             source_db: Path = DEFAULT_SOURCE_DB) -> dict:
    if from_id == to_id or predicate not in PREDICATES:
        raise ValueError("Self-relationships and unsupported predicates are not allowed")
    for key in (from_id, to_id, doc_id):
        check_id(key)
    excerpt = checked(excerpt, "Exact supporting excerpt", 1500)
    locator = checked(locator, "Human-entered locator", 220)
    actor = checked(actor, "Researcher", 120)
    initialize(db, source_db)
    with closing(connect(db)) as conn:
        row = conn.execute("SELECT content,sha256 FROM kg_documents WHERE id=?", (doc_id,)).fetchone()
        if row is None:
            raise ValueError("Evidence document not found")
        if digest(row["content"]) != row["sha256"]:
            raise ValueError("Evidence integrity failure; refusing relation")
        if excerpt not in row["content"]:
            raise ValueError("Evidence quote must appear exactly in pinned source content")
        with conn:
            cur = conn.execute("""INSERT INTO kg_edges
              (from_id,to_id,predicate,document_id,document_sha256,
               exact_excerpt,locator,actor,recorded_at)
              VALUES (?,?,?,?,?,?,?,?,?)""",
              (from_id, to_id, predicate, doc_id, row["sha256"],
               excerpt, locator, actor, now()))
    return {"id": cur.lastrowid, "state": "PROPOSED_RESEARCH_ONLY"}


def _evidence_status(row: dict, source_db: Path) -> str:
    if digest(row["content"]) != row["sha256"] or row["document_sha256"] != row["sha256"]:
        return "PINNED_EVIDENCE_INTEGRITY_FAILURE"
    if row["exact_excerpt"] not in row["content"]:
        return "EXCERPT_MISSING_FROM_PINNED_EVIDENCE"
    if row["kind"] == "FR_METADATA":
        try:
            snapshot(source_db, row["source_doc_number"], fingerprint=row["sha256"])
        except (ValueError, OSError, sqlite3.Error, TypeError):
            return "PINNED_FEDERAL_REGISTER_METADATA_UNAVAILABLE_OR_INVALID"
        try:
            latest = snapshot(source_db, row["source_doc_number"])
            if latest["fingerprint"] != row["sha256"]:
                return "NEWER_LOCAL_METADATA_REQUIRES_REVIEW"
        except (ValueError, OSError, sqlite3.Error, TypeError):
            return "LATEST_LOCAL_METADATA_UNAVAILABLE"
        return "LOCAL_METADATA_PIN_MATCH_ONLY_NOT_CURRENT_AUTHORITY"
    return "PINNED_LOCAL_TEXT_MATCH_ONLY_NOT_LIVE_VERIFIED"


def evidence_edges(db: Path, source_db: Path = DEFAULT_SOURCE_DB,
                   node_id: str | None = None) -> list[dict]:
    if not db.is_file():
        return []
    clause = "WHERE e.from_id=? OR e.to_id=?" if node_id else ""
    args = (node_id, node_id) if node_id else ()
    with closing(connect(db)) as conn:
        rows = [dict(r) for r in conn.execute(f"""SELECT e.*,d.title,d.kind,d.source_url,
                d.source_doc_number,d.content,d.sha256,
                n1.label AS from_label,n2.label AS to_label
                FROM kg_edges e JOIN kg_documents d ON d.id=e.document_id
                JOIN kg_nodes n1 ON n1.id=e.from_id
                JOIN kg_nodes n2 ON n2.id=e.to_id
                {clause} ORDER BY e.id""", args)]
    for r in rows:
        r["evidence_status"] = _evidence_status(r, source_db)
        del r["content"]
        r["compliance_status"] = "NOT_DETERMINED"
        r["external_release_authorized"] = False
    return rows


def export_graph(db: Path, source_db: Path = DEFAULT_SOURCE_DB,
                 node_id: str | None = None) -> dict:
    if node_id is not None:
        check_id(node_id)
    if not db.is_file():
        return {"nodes": [], "edges": [], "documents": [],
                "compliance_status": "NOT_DETERMINED", "external_release_authorized": False}
    with closing(connect(db)) as conn:
        if node_id is not None and not conn.execute("SELECT 1 FROM kg_nodes WHERE id=?", (node_id,)).fetchone():
            raise ValueError("Node ID not found")
        nodes = [dict(r) for r in conn.execute("SELECT * FROM kg_nodes ORDER BY id")]
        docs = [dict(r) for r in conn.execute("SELECT id,title,kind,source_url,sha256 FROM kg_documents ORDER BY id")]
    edges = evidence_edges(db, source_db, node_id)
    if node_id is not None:
        ids = {x for e in edges for x in (e["from_id"], e["to_id"])} | {node_id}
        nodes = [n for n in nodes if n["id"] in ids]
        doc_ids = {e["document_id"] for e in edges}
        docs = [d for d in docs if d["id"] in doc_ids]
    return {"nodes": nodes, "edges": edges, "documents": docs,
            "compliance_status": "NOT_DETERMINED", "external_release_authorized": False,
            "limits": "Research candidates only; source citations are not legal applicability findings."}


def render_html(data: dict) -> str:
    """Offline interactive SVG topology with evidence panel; no CDN, fonts, scripts or API calls."""
    safe_payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    template = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SRP | AeroCIE-009 Research Graph</title>
<style>body{background:#0b1728;color:#e4ebf5;font:15px/1.5 system-ui;margin:0}header{background:#11253f;padding:22px 28px;border-bottom:2px solid #c2a46a}h1{margin:0;font-size:25px}small,.muted{color:#acbed0}main{display:grid;grid-template-columns:minmax(400px,1fr) 360px;gap:18px;padding:20px}.pane{border:1px solid #314963;border-radius:12px;background:#10213a;padding:14px}svg{width:100%;height:560px}line{stroke:#6e87aa;stroke-opacity:.65}circle{fill:#d8b775;stroke:#152b44;stroke-width:2;cursor:pointer}text{fill:#eaf3ff;font-size:11px}.edge{cursor:pointer}button{background:#c2a46a;border:none;border-radius:5px;padding:6px 9px;margin:3px;cursor:pointer}a{color:#94ccff;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere}p{overflow-wrap:anywhere}@media(max-width:900px){main{grid-template-columns:1fr}}</style>
<header><small>STRATEGICRISK PARTNERS | RESEARCH INFRASTRUCTURE</small><h1>AeroCIE-009 | Source-Linked Knowledge Graph</h1><small>INTERNAL RESEARCH ONLY | NOT_DETERMINED | CLIENT RELEASE NOT AUTHORIZED</small></header>
<main><section class="pane"><p id="counts"></p><svg id="view" role="img" aria-label="Graph of research entities connected by source-linked relationships" viewBox="0 0 900 560"></svg></section><aside class="pane"><h2>Evidence inspector</h2><p class="muted">Select a relationship to inspect its source excerpt, fingerprint and current local evidence status.</p><div id="detail"></div></aside></main>
<script>const g=__DATA__;const svg=document.getElementById('view'),details=document.getElementById('detail');const N='http://www.w3.org/2000/svg';function elem(t,a){let e=document.createElementNS(N,t);Object.entries(a||{}).forEach(([k,v])=>e.setAttribute(k,v));return e}function show(e){details.replaceChildren();const add=(t,v)=>{let x=document.createElement(t);x.textContent=v;details.append(x)};add('h3',e.from_label+' '+e.predicate.replaceAll('_',' ')+' '+e.to_label);add('p','PROPOSED_RESEARCH_ONLY | '+e.evidence_status);add('p','Document: '+e.title+' | '+e.kind);add('p','Locator (researcher supplied): '+e.locator);add('pre',e.exact_excerpt);add('p','Pinned SHA-256: '+e.document_sha256);let a=document.createElement('a');a.href=e.source_url;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Open cited source (external)';details.append(a)}document.getElementById('counts').textContent=g.nodes.length+' nodes | '+g.edges.length+' research links | '+g.documents.length+' sources';const n=g.nodes.length,pos=new Map();g.nodes.forEach((x,i)=>{const angle=2*Math.PI*i/Math.max(n,1),ring= Math.min(220,110+8*n);pos.set(x.id,[450+ring*Math.cos(angle),280+ring*Math.sin(angle)])});g.edges.forEach(e=>{const a=pos.get(e.from_id),b=pos.get(e.to_id);let l=elem('line',{x1:a[0],y1:a[1],x2:b[0],y2:b[1],class:'edge','stroke-width':3});l.addEventListener('click',()=>show(e));let ti=elem('title');ti.textContent=e.predicate+' | '+e.title;l.append(ti);svg.append(l)});g.nodes.forEach(x=>{let p=pos.get(x.id);let c=elem('circle',{cx:p[0],cy:p[1],r:9});let ti=elem('title');ti.textContent=x.label+' | '+x.kind;c.append(ti);svg.append(c);let t=elem('text',{x:p[0]+12,y:p[1]-10});t.textContent=x.label.slice(0,28);svg.append(t)});if(g.edges[0])show(g.edges[0]);</script></html>"""
    return template.replace("__DATA__", safe_payload)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AeroCIE-009 offline source-linked research graph")
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    p.add_argument("--source-db", type=Path, default=DEFAULT_SOURCE_DB)
    subs = p.add_subparsers(dest="command", required=True)
    subs.add_parser("init")
    f = subs.add_parser("import-file")
    f.add_argument("--id", required=True); f.add_argument("--title", required=True)
    f.add_argument("--url", required=True); f.add_argument("--file", type=Path, required=True)
    fr = subs.add_parser("import-fr"); fr.add_argument("--document-number", required=True)
    no = subs.add_parser("add-node"); no.add_argument("--id", required=True)
    no.add_argument("--type", required=True, choices=NODE_TYPES); no.add_argument("--label", required=True)
    li = subs.add_parser("add-link")
    for name in ("from-id", "to-id", "doc-id", "quote", "locator", "actor"):
        li.add_argument("--"+name, required=True)
    li.add_argument("--predicate", required=True, choices=PREDICATES)
    sub = subs.add_parser("neighbors"); sub.add_argument("--node", required=True)
    subs.add_parser("export"); subs.add_parser("stats")
    vi = subs.add_parser("render-html"); vi.add_argument("--output", type=Path, default=Path("build/aerocie/reports/knowledge-graph.html"))
    args = p.parse_args(argv)
    try:
        _guard_db(args.db, args.source_db)
        if args.command == "init":
            initialize(args.db, args.source_db); result = {"database": str(args.db)}
        elif args.command == "import-file":
            if args.file.stat().st_size > MAX_TEXT_BYTES:
                raise ValueError("Source text file exceeds 2 MB")
            text = args.file.read_bytes().decode("utf-8")
            result = import_text(args.db, doc_id=args.id, title=args.title, url=args.url,
                                 text=text, source_db=args.source_db)
        elif args.command == "import-fr":
            result = import_federal_register(args.db, args.source_db, args.document_number)
        elif args.command == "add-node":
            result = add_node(args.db, node_id=args.id, kind=args.type, label=args.label, source_db=args.source_db)
        elif args.command == "add-link":
            result = add_edge(args.db, from_id=args.from_id, to_id=args.to_id,
                              predicate=args.predicate, doc_id=args.doc_id, excerpt=args.quote,
                              locator=args.locator, actor=args.actor, source_db=args.source_db)
        elif args.command == "neighbors":
            result = export_graph(args.db, args.source_db, node_id=args.node)
        elif args.command == "render-html":
            graph = export_graph(args.db, args.source_db)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(render_html(graph), encoding="utf-8")
            result = {"path": str(args.output), "nodes": len(graph["nodes"]), "edges": len(graph["edges"])}
        else:
            graph = export_graph(args.db, args.source_db)
            result = ({"nodes": len(graph["nodes"]), "edges": len(graph["edges"]),
                       "sources": len(graph["documents"]),
                       "flagged_evidence": sum(e["evidence_status"].endswith(("FAILURE", "REVIEW", "UNAVAILABLE", "INVALID", "EVIDENCE")) for e in graph["edges"])}
                      if args.command == "stats" else graph)
        print(json.dumps({"compliance_status": "NOT_DETERMINED",
                          "external_release_authorized": False, "result": result}, indent=2, ensure_ascii=False))
        return 0
    except (ValueError, OSError, sqlite3.Error, UnicodeError) as exc:
        print(f"AeroCIE-009 error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())