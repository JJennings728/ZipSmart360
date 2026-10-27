#!/usr/bin/env python3
"""SRP static-site assembly. Public demo only; never imports local private research data."""
from pathlib import Path
from urllib.request import urlopen
import re

ROOT = Path.cwd()
EMAIL = "info@sriskpartners.com"
GRAPH_COMMIT = "ef1b8a786e90f034da9152664ad13e6cb45e6528"
GRAPH_URL = "https://raw.githubusercontent.com/JJennings728/ZipSmart360/" + GRAPH_COMMIT + "/website-public/aerocie-demo/index.html"
demo_path = ROOT / "aerocie-demo" / "index.html"
demo_path.parent.mkdir(parents=True, exist_ok=True)
with urlopen(GRAPH_URL, timeout=35) as response:
    content = response.read()
if len(content) < 100000:
    raise RuntimeError("Synthetic graph asset was incomplete; refusing deployment.")
demo = content.decode("utf-8")
if not all(x in demo for x in ["8,800 SIMULATED NODES", "NOT_DETERMINED", "9,000 SIMULATED SOURCE DOCUMENTS", "INTERACTIVE DEMO | SYNTHETIC"]):
    raise RuntimeError("Graph disclosure and simulation checks failed.")
demo_path.write_bytes(content)

def inject(path, fragment, mark):
    path = ROOT / path
    if not path.is_file():
        raise RuntimeError(f"Expected website page not found: {path}")
    raw = path.read_text("utf-8")
    if mark in raw:
        return
    match = re.search(r"</main\s*>", raw, re.I)
    if not match:
        match = re.search(r"</body\s*>", raw, re.I)
    if not match:
        raise RuntimeError(f"Cannot locate safe insertion point: {path}")
    raw = raw[:match.start()] + fragment + "\n" + raw[match.start():]
    path.write_text(raw, encoding="utf-8")

base_css = """
<style>
.srp-public-demo{padding:46px 0 54px;background:linear-gradient(115deg,#051327,#0b2340);color:#eef8ff}
.srp-public-demo *{box-sizing:border-box}
.srp-public-demo .srp-inner{width:min(1150px,calc(100% - 48px));margin:auto}
.srp-public-demo h2{font:700 clamp(26px,3.2vw,40px)/1.15 Montserrat,Arial,sans-serif;color:white;margin:12px 0 17px}
.srp-public-demo p{color:#b7d3e8;line-height:1.65;max-width:880px}
.srp-public-demo .srp-eyebrow{font:700 12px Montserrat,Arial,sans-serif;color:#5ee4ef;letter-spacing:.13em;text-transform:uppercase}
.srp-public-demo a.srp-demo-btn{display:inline-block;padding:13px 19px;background:#0a79cc;color:white;border-radius:6px;text-decoration:none;font:700 13px Montserrat,Arial,sans-serif;margin-top:14px}
.srp-public-demo .srp-demo-frame{height:720px;width:100%;border:1px solid #244963;border-radius:10px;margin-top:27px;background:#030b1c;display:block}
.srp-public-demo .srp-note{font-size:12px;color:#b1bfcf;margin-top:14px}
@media(max-width:780px){.srp-public-demo .srp-demo-frame{height:530px}.srp-public-demo .srp-inner{width:calc(100% - 28px)}}
</style>
"""
home = base_css + """
<section class="srp-public-demo" id="aerocie-showcase" data-srp-addendum="aerocie">
<div class="srp-inner">
<div class="srp-eyebrow">AeroCIE | Interactive technology demonstration</div>
<h2>Explore the source-linked knowledge network</h2>
<p>See how seven research stages can organize source evidence, context, relationships, risk observations, and review decisions. The interactive network demonstrates navigation and human-review workflows using <strong>synthetic</strong> nodes and records.</p>
<a class="srp-demo-btn" href="/aerocie-demo/">Explore interactive demo</a>
<p class="srp-note">Illustrative simulation only | No live FAA, NASA, or DoD feeds | No verified regulatory decisions | Compliance: NOT_DETERMINED</p>
</div></section>
"""
intel = base_css + """
<section class="srp-public-demo" id="aerocie-network" data-srp-addendum="aerocie">
<div class="srp-inner">
<div class="srp-eyebrow">AeroCIE | L1–L7 research network</div>
<h2>Interactive evidence-flow demonstration</h2>
<p>Explore the simulated relationships, search records, select graph nodes, and inspect illustrative evidence traces. This demo uses 8,800 simulated nodes and 9,000 simulated documents; it is not a validated live data service.</p>
<a class="srp-demo-btn" href="/aerocie-demo/">Open full-screen demonstration</a>
<iframe class="srp-demo-frame" src="/aerocie-demo/" title="AeroCIE L1 through L7 synthetic interactive graph demonstration" sandbox="allow-scripts" loading="lazy"></iframe>
<p class="srp-note">Synthetic demonstration | No actual government, customer, classified, CDI, or CUI data | NOT_DETERMINED | Human verification required for real findings</p>
</div></section>
"""
defense = base_css + """
<section class="srp-public-demo" id="defense-contractor-services" data-srp-addendum="defense">
<div class="srp-inner">
<div class="srp-eyebrow">Government industry | Prime contractors | Subcontractors</div>
<h2>Technical research, risk intelligence and technology consulting</h2>
<p>StrategicRisk Partners LLC offers scoped, nonclassified research and development support for aviation, aerospace, defense-industry suppliers, and subcontractors. Services include:</p>
<ul style="line-height:1.9;color:#d6e7f4;padding-left:21px">
<li><strong>Aerospace technical and regulatory research:</strong> public FAA, NTSB, and Federal Register source-linked evidence reviews, dated research briefs, and questions for qualified technical review.</li>
<li><strong>Supplier and operational risk intelligence:</strong> public-source counterparty screening, supply-chain developments, operating exposures, research registers, and exception reporting.</li>
<li><strong>AI, PowerShell and Python workflow prototyping:</strong> local-first data intake, deterministic checks, evidence provenance, source change identification, document workflow automation, and human-approval gates.</li>
<li><strong>Cyber risk and compliance-readiness advisory:</strong> scoped cyber-risk assessment planning, control inventories, NIST CSF 2.0 mapping and defensive zero-trust architecture roadmaps; not certified compliance determinations.</li>
<li><strong>Financial and operational analytics:</strong> reconciliations, discrepancy and variance reporting, dashboard prototypes and management-ready decision support, subject to engagement-specific validation.</li>
<li><strong>Aviation and space research advisory:</strong> public NASA event research, aircraft and engine exposure analysis, mission-assurance research candidates and source-linked decision briefs.</li>
</ul>
<p><strong>Primary documented NAICS: 541690</strong> | Other Scientific and Technical Consulting Services. Additional classifications, if any, should be reconciled to SRP's actual SAM.gov registration before being represented as registered.</p>
<p class="srp-note">AeroCIE is an early-stage research prototype. SRP does not claim CMMC, AS9100, ISO 9001, RTX/Lockheed supplier approval, cleared status, or authorization to process CDI/CUI. SAM.gov entity registration was submitted and remains subject to validation; government awards and sponsorship are not implied.</p>
<a class="srp-demo-btn" href="mailto:info@sriskpartners.com?subject=SRP%20Defense%20Supplier%20Consultation">Request a confidential scope discussion: info@sriskpartners.com</a>
<p class="srp-note">Do not send CUI, classified, export-controlled, or other restricted information by email. Begin with a high-level, non-sensitive statement of need.</p>
</div></section>
"""
defense_intro = base_css + """
<section class="srp-public-demo" id="defense-consulting" data-srp-addendum="defense">
<div class="srp-inner">
<div class="srp-eyebrow">Defense-industry consulting | NAICS 541690</div>
<h2>Research and technology support for primes and subcontractors</h2>
<p>Source-linked aerospace evidence | Supplier risk intelligence | AI and PowerShell workflow prototypes | Cybersecurity readiness advisory | Data validation and exception reporting. Nonclassified, authorized-data engagements only.</p>
<a class="srp-demo-btn" href="/services-pricing/#defense-contractor-services">Explore defense-industry services</a>
<p class="srp-note">Capabilities are scoped individually; no federal registration approval, contract award, CMMC certification, or clearance implied.</p>
</div></section>
"""
price = re.compile(r"\$(?:995|2,995|7,500)\b")
changed = []
for path in ROOT.rglob("*.html"):
    if path == demo_path or "node_modules" in path.parts:
        continue
    raw = path.read_text("utf-8")
    updated = re.sub(r"(?is)<p>\s*Existing starting prices:.*?</p>", '<p>Project fees are quoted after scope confirmation. Direct all inquiries to <a href="mailto:info@sriskpartners.com">info@sriskpartners.com</a>.</p>', raw)
    updated = re.sub(r"(?i)\bFrom\s+\$(?:995|2,995|7,500)(?:\s*<small>one time</small>)?", "By consultation", updated)
    updated = price.sub("By consultation", updated)
    updated = updated.replace("Transparent starting prices for scoped projects.", "Custom quotations for scoped research and technology projects.")
    updated = updated.replace("Services & Pricing", "Services & Consulting")
    updated = updated.replace("Services &amp; Pricing", "Services &amp; Consulting")
    updated = updated.replace("href=\"/payments/\"", "href=\"/contact/\"")
    updated = updated.replace("href=\"../payments/\"", "href=\"../contact/\"")
    updated = updated.replace("href=\"/services-pricing/\"", "href=\"/services-pricing/\"")
    if updated != raw:
        path.write_text(updated,"utf-8")
        changed.append(str(path.relative_to(ROOT)))

inject("index.html", home + defense_intro, 'data-srp-addendum="aerocie"')
inject("intelligence/index.html", intel, 'data-srp-addendum="aerocie"')
inject("services-pricing/index.html", defense, 'data-srp-addendum="defense"')
contact = ROOT / "contact/index.html"
if contact.exists():
    txt=contact.read_text("utf-8")
    if "mailto:info@sriskpartners.com" not in txt:
        inject("contact/index.html", '<p style="padding:18px;text-align:center">For consultation and quotations: <a href="mailto:info@sriskpartners.com">info@sriskpartners.com</a></p>', 'href="mailto:info@sriskpartners.com"')

# Do not expose legacy direct payment page while all service fees are quoted individually.
payment = ROOT / "payments/index.html"
if payment.exists():
    payment.write_text("""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Consultations | StrategicRisk Partners</title></head><body style="font:16px/1.65 system-ui,sans-serif;max-width:720px;margin:12vh auto;padding:20px;color:#142a44"><h1>StrategicRisk Partners</h1><h2>Request a consultation</h2><p>All services are individually scoped and quoted by written proposal. Public checkout is not available.</p><p>Direct inquiries to <a href="mailto:info@sriskpartners.com">info@sriskpartners.com</a>.</p><p><a href="/">Return to website</a></p></body></html>""","utf-8")

if any(price.search(p.read_text("utf-8")) for p in ROOT.rglob("*.html") if p != demo_path):
    raise RuntimeError("Unexpected public legacy service pricing remains.")
for route in ["index.html", "intelligence/index.html", "services-pricing/index.html", "aerocie-demo/index.html"]:
    if not (ROOT/route).is_file():
        raise RuntimeError("Required route missing: " + route)
if 'iframe class="srp-demo-frame"' not in (ROOT/"intelligence/index.html").read_text("utf-8"):
    raise RuntimeError("Interactive embedded preview missing.")
print("SRP_SITE_BUILD_OK", "synthetic_demo_bytes",len(content),"edited_prices",len(changed),"demo_in_intelligence",True)
