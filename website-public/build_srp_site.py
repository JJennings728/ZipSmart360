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

# Immutable, reviewed visual enhancement — standalone JS, no live data.
GLOW_COMMIT = "afad0ab0ffabd40852955873f5f35ab3661e86ee"
GLOW_URL = "https://raw.githubusercontent.com/JJennings728/ZipSmart360/" + GLOW_COMMIT + "/website-public/aerocie-demo/glow-effects.js"
with urlopen(GLOW_URL, timeout=35) as response:
    glow_js = response.read().decode("utf-8")
if len(glow_js) < 9000 or not all(token in glow_js for token in ["AeroCIEHoverEffects", "ILLUSTRATIVE_SYNTHETIC", "srp-stage-rail", "prefers-reduced-motion"]):
    raise RuntimeError("Interactive glow source invalid or incomplete.")
(ROOT / "aerocie-demo" / "glow-effects.js").write_text(glow_js, encoding="utf-8")
html = demo_path.read_text(encoding="utf-8")
if "glow-effects.js" not in html:
    if html.count("</body>") != 1:
        raise RuntimeError("Unexpected synthetic demo HTML closing tag.")
    html = html.replace("</body>", '<script src="/aerocie-demo/glow-effects.js" defer></script></body>')
    demo_path.write_text(html, encoding="utf-8")

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
print("SRP_SITE_BUILD_OK", "synthetic_demo_bytes",len(content),"edited_prices",len(changed),"demo_in_intelligence",True,"hover_effects",True,"seven_stages",True)

# SRP VISUAL + SPACE ANALYTICS SITE UPDATE | 2026-10-26
# Keeps the source-verified AeroCIE synthetic demo, safeguards and consultation-only pricing.
import hashlib
from html import escape as srp_escape

MEDIA_ASSETS = {
    'srp-digital-engineering.webp': ('77e85cb3f762c22f63c58cbb948c13733896cb92', 55066),
    'srp-aircraft-night.webp': ('2493e24a46cd2134f25b98a408d9a02724b6b91c', 29574),
    'srp-engine-manufacturing.webp': ('614ff5cd3d6e8b77de997d08520a3ac14df1f088', 178924),
    'srp-launch.webp': ('ddd951197df2e3fc9520ea090903d42cad1cc9ce', 39980),
    'srp-data-network.webp': ('1c7edfe96187f9105d7b5b7409e02c730e653ca3', 144690),
    'srp-satellite.webp': ('798bc6f0ef37929ef7e9f85246241ec4dbd08c1e', 52708),
}
MEDIA_BASE_URL = 'https://dmmcy0pwk6bqi.cloudfront.net/'
MEDIA_ROOT = ROOT / 'assets' / 'srp'
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
for image_name, (digest, expected_size) in MEDIA_ASSETS.items():
    target = MEDIA_ROOT / image_name
    with urlopen(MEDIA_BASE_URL + digest, timeout=40) as response:
        blob = response.read()
    if len(blob) != expected_size or hashlib.sha1(blob).hexdigest() != digest or blob[:4] != b'RIFF':
        raise RuntimeError('Adobe Stock image was incomplete or altered: ' + image_name)
    target.write_bytes(blob)

# Remove only the public NAICS label; underlying formal supplier capability documents stay unchanged.
for p in ROOT.rglob('*.html'):
    if p == demo_path:
        continue
    before = p.read_text('utf-8')
    after = re.sub(r'\s*\|\s*NAICS\s*541690\b', '', before, flags=re.I)
    after = re.sub(r'(?is)<p>\s*<strong>Primary documented NAICS:\s*541690</strong>.*?</p>', '', after)
    if before != after:
        p.write_text(after, encoding='utf-8')

SITE_STOCK_CSS = r'''
<style id="srp-stock-photos-2026">
.srp-stock-panel{position:relative;isolation:isolate;min-height:300px;display:flex;align-items:center;background:#06162c;overflow:hidden;color:#fff;border-radius:0}
.srp-stock-panel::before{content:"";position:absolute;inset:0;z-index:-2;background:var(--srp-photo) center/cover no-repeat}
.srp-stock-panel::after{content:"";position:absolute;inset:0;z-index:-1;background:linear-gradient(90deg,rgba(2,11,29,.97) 0%,rgba(3,16,37,.91) 36%,rgba(4,19,43,.49) 66%,rgba(3,13,31,.19) 100%)}
.srp-stock-panel .srp-stock-inner{width:min(1140px,calc(100% - 44px));margin:0 auto;padding:54px 0;color:#fff}
.srp-stock-panel .srp-stock-copy{max-width:645px}
.srp-stock-panel .srp-stock-eyebrow{margin:0 0 12px;color:#63dff5;font:700 12px/1.6 system-ui,sans-serif;letter-spacing:.12em;text-transform:uppercase}
.srp-stock-panel h2{color:#fff!important;font:700 clamp(27px,3.6vw,44px)/1.13 system-ui,sans-serif;letter-spacing:-.025em;margin:0 0 18px;text-shadow:0 2px 12px #04162a}
.srp-stock-panel p{color:#e8f3ff!important;font:400 16px/1.7 system-ui,sans-serif;margin:0 0 21px;max-width:660px;text-shadow:0 1px 8px #061329}
.srp-stock-panel a.srp-stock-cta{display:inline-block;padding:12px 18px;border-radius:5px;background:#1468b5;color:#fff!important;text-decoration:none;font:700 13px system-ui,sans-serif}
.srp-stock-panel a.srp-stock-cta:hover,.srp-stock-panel a.srp-stock-cta:focus-visible{background:#0b88d1;text-decoration:underline}
.srp-stock-panel.srp-compact{min-height:275px}
@media(max-width:700px){.srp-stock-panel{min-height:300px}.srp-stock-panel::after{background:linear-gradient(90deg,rgba(2,11,29,.96),rgba(3,15,33,.73))}.srp-stock-panel .srp-stock-inner{padding:40px 0}.srp-stock-panel h2{font-size:clamp(26px,6.4vw,36px)}}
</style>
'''

def srp_stock_section(section_id,photo,eyebrow,title,description,link,button,compact=True):
    assert photo in MEDIA_ASSETS
    cls=' srp-compact' if compact else ''
    return '''<section class="srp-stock-panel%s" id="%s" style="--srp-photo:url('/assets/srp/%s')" aria-label="%s">
<div class="srp-stock-inner"><div class="srp-stock-copy"><p class="srp-stock-eyebrow">%s</p><h2>%s</h2><p>%s</p><a class="srp-stock-cta" href="%s">%s</a></div></div></section>''' % (
      cls, srp_escape(section_id), srp_escape(photo), srp_escape(title),
      srp_escape(eyebrow),srp_escape(title),srp_escape(description),srp_escape(link),srp_escape(button))

def srp_insert_in_main(page, html, mark, near_top=False):
    path=ROOT/page
    if not path.exists():
        raise RuntimeError('Expected site route missing: '+page)
    text=path.read_text('utf-8')
    if mark in text:
        return
    if near_top:
        # Insert within main without replacing existing hero/nav.
        match=re.search(r'<main\b[^>]*>',text,re.I)
        if match:
            at=match.end()
        else:
            match=re.search(r'</header\s*>',text,re.I)
            if not match: raise RuntimeError('Missing insertion anchor: '+page)
            at=match.end()
    else:
        match=re.search(r'</main\s*>',text,re.I)
        if not match: raise RuntimeError('Missing main closing tag: '+page)
        at=match.start()
    path.write_text(text[:at]+'\n'+SITE_STOCK_CSS+'\n'+html+'\n'+text[at:],encoding='utf-8')

# Six individual stock images; each is used in a relevant section, not combined.
srp_insert_in_main('index.html',srp_stock_section(
    'srp-aerospace-advisory-photo','srp-digital-engineering.webp','Aerospace intelligence | Digital consulting',
    'Technical insight for complex aerospace risk',
    'Source-linked aviation and aerospace research, operational analytics, and tailored technology consulting.',
    '/services-pricing/','Explore consulting capabilities'),'id="srp-aerospace-advisory-photo"',near_top=False)

srp_insert_in_main('intelligence/index.html',srp_stock_section(
    'srp-data-network-photo','srp-data-network.webp','AeroCIE | Evidence workflows',
    'Research built on traceable sources',
    'Prototype source provenance, record reconciliation, human-review gates and deterministic checks—with simulation clearly identified.',
    '/aerocie-demo/','Explore interactive demo'),'id="srp-data-network-photo"',near_top=False)

srp_insert_in_main('sectors/index.html',srp_stock_section(
    'srp-engine-manufacturing-photo','srp-engine-manufacturing.webp','Manufacturing | MRO | Supplier research',
    'Technical evidence for aerospace suppliers',
    'Independent public-source research on aviation engines, manufacturing considerations, regulatory developments and supplier exposure.',
    '/services-pricing/','Discuss your research scope'),'id="srp-engine-manufacturing-photo"',near_top=False)

srp_insert_in_main('solutions/space/index.html',srp_stock_section(
    'srp-launch-photo','srp-launch.webp','Launch | Mission exposure',
    'Space risk analytics and launch intelligence',
    'Source-linked public research on launch events, space-sector exposures, mission context and aerospace loss history. No real-time mission assurance or safety prediction is represented.',
    '/services-pricing/#space-risk-analytics','Request space risk research'),'id="srp-launch-photo"',near_top=False)

space_service=srp_stock_section(
    'space-risk-analytics','srp-satellite.webp','Space risk analytics | Earth observation',
    'Satellite, launch and aerospace risk research',
    'Scope-limited analysis of public launch, satellite and space-event records, selected NASA EONET natural-hazard context and DONKI space-weather context, and source-linked operational exposure research. Research support only—not live hazard warnings, engineering certification, insurance rating or verified mission predictions.',
    'mailto:info@sriskpartners.com?subject=Space%20Risk%20Analytics%20Consultation','Request a consultation')
srp_insert_in_main('services-pricing/index.html',space_service,'id="space-risk-analytics"',near_top=False)

# Make the insurance-market landing-page hero compact and high-contrast. Replace bright cockpit photo
# with original dark aircraft photo and limit the separate report-cover image footprint.
market=ROOT/'research/aviation-market-overview-2026/index.html'
if not market.is_file():raise RuntimeError('Insurance market page missing')
market_html=market.read_text('utf-8')
market_style=r'''<style id="srp-market-legibility-fix">
.market-hero{background-image:linear-gradient(90deg,rgba(2,10,27,.99) 0%,rgba(2,13,33,.94) 40%,rgba(3,17,37,.71) 73%,rgba(3,14,30,.55) 100%),url('/assets/srp/srp-aircraft-night.webp')!important;background-position:center 58%!important;background-size:cover!important;padding:clamp(52px,5.2vw,78px) 0 clamp(46px,5vw,70px)!important;min-height:0!important}
.market-hero h1{font-size:clamp(32px,4.2vw,58px)!important;max-width:780px!important;line-height:1.13!important;text-shadow:0 3px 16px #030d20!important}
.market-hero h1 span{color:#63dfff!important}
.market-hero .sub,.market-hero p{color:#f4faff!important;text-shadow:0 2px 10px #061329!important}
.market-hero .container{position:relative;z-index:1}
img[src*='Market_Overview_2026_Cover'],img[src*='market-overview-2026-cover'],.market-cover img,.report-cover img{display:block!important;width:auto!important;max-width:min(100%,460px)!important;height:auto!important;max-height:560px!important;object-fit:contain!important;margin-left:auto;margin-right:auto}
@media(max-width:700px){.market-hero{padding:46px 0 50px!important;background-position:60% center!important}.market-hero h1{font-size:clamp(31px,7.2vw,43px)!important;max-width:100%!important}}
</style>'''
if 'id="srp-market-legibility-fix"' not in market_html:
    if '</head>' not in market_html:raise RuntimeError('Insurance market head missing')
    market_html=market_html.replace('</head>',market_style+'</head>',1)
    market.write_text(market_html,encoding='utf-8')

# Ensure space analytics is discoverable from our public intelligence section as well as services.
additional='''<div style="margin:26px auto 12px;width:min(1140px,calc(100% - 44px));padding:20px 24px;background:#0b2644;border-left:4px solid #39c8ee;color:white">
<strong style="font-size:18px">Space Risk Analytics</strong><p style="color:#dcecf9">Independent public-source launch, satellite, Earth observation, and operational risk research with dated source references and human review.</p>
<a style="color:#78e4ff" href="/services-pricing/#space-risk-analytics">Explore space risk advisory</a></div>'''
srp_insert_in_main('intelligence/index.html',additional,'Explore space risk advisory',near_top=False)

# Release guards: no listed service prices, no visible NAICS label, and six distinct image assets.
for page in ['index.html','intelligence/index.html','sectors/index.html','services-pricing/index.html','solutions/space/index.html','research/aviation-market-overview-2026/index.html']:
    s=(ROOT/page).read_text('utf-8')
    if 'NAICS 541690' in s:raise RuntimeError('Public NAICS label remains: '+page)
    if any(p in s for p in ['$995','$2,995','$7,500']):raise RuntimeError('Public legacy price remains: '+page)
    if page=='research/aviation-market-overview-2026/index.html' and 'id="srp-market-legibility-fix"' not in s:raise RuntimeError('Market hero override not found')
for image_name in MEDIA_ASSETS:
    if not (MEDIA_ROOT/image_name).exists():raise RuntimeError('Missing photo: '+image_name)
print('SRP_VISUAL_UPDATE_OK','images',len(MEDIA_ASSETS),'space_risk_analytics',True,'public_naics_label_removed',True,'market_hero_contrast',True)


# SRP_OPTION_B_2026 | Enterprise presentation and engagement accessibility
# Static-site copy and presentation only; no billing or mail changes.
from html import escape as _esc

_SRP_ENTERPRISE_CSS = """
<style id="srp-enterprise-2026">
:root{--srp-navy:#07182d;--srp-ice:#eaf6fc;--srp-cyan:#77e4fa}
.srp-engagement-card{background:#07182d!important;color:#f4f8fc!important;border:1px solid #284766!important;border-radius:14px!important;padding:clamp(28px,4vw,54px)!important;box-shadow:0 18px 45px rgba(4,17,35,.14)!important;margin:36px 0!important}
.srp-engagement-card h2{color:#fff!important;font-size:clamp(28px,3vw,40px)!important;line-height:1.2!important;margin:0 0 26px!important}
.srp-engagement-card p,.srp-engagement-card li{color:#e2ecf5!important;font-size:16px!important;line-height:1.75!important}
.srp-engagement-card strong{color:#fff!important}
.srp-engagement-card a{color:#77e4fa!important;text-decoration:underline!important;text-underline-offset:3px}
.srp-engagement-card a:hover,.srp-engagement-card a:focus-visible{color:#fff!important}
.srp-engagement-card a:focus-visible{outline:2px solid #77e4fa;outline-offset:4px}
.srp-engagement-card .srp-eyebrow{color:#77e4fa!important;font:700 12px/1.55 system-ui,sans-serif!important;text-transform:uppercase;letter-spacing:.15em}
.srp-engagement-steps{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px 28px;margin:26px 0}
.srp-engagement-step{padding:16px 0;border-top:1px solid #355572}
.srp-engagement-step .srp-number{display:block;color:#77e4fa!important;font:700 15px/1.3 system-ui,sans-serif;margin-bottom:8px}
.srp-engagement-step h3{color:#fff!important;font:700 20px/1.2 system-ui,sans-serif;margin:0 0 8px}
.srp-engagement-step p{margin:0!important;font-size:15px!important}
.srp-engagement-card .srp-engagement-footer{border-top:1px solid #355572;padding-top:18px;margin-top:20px}
.srp-engagement-card .srp-policy-links{display:flex;gap:18px;flex-wrap:wrap;margin-top:15px;font-size:14px}
.srp-engagement-card .srp-contact-link{display:inline-block;margin:8px 0 0;font-weight:700}
.srp-enterprise-lead{color:#e4eef9;font:400 clamp(16px,1.65vw,19px)/1.7 system-ui,sans-serif;max-width:800px}
.srp-enterprise-kicker{font:700 12px/1.6 system-ui,sans-serif;color:#63dff5;letter-spacing:.12em;text-transform:uppercase;margin:0 0 12px}
.srp-enterprise-solution{border-top:1px solid #d6e3ec;padding:28px 0}
.srp-enterprise-solution h2{margin:0 0 8px}
.srp-enterprise-solution p{max-width:800px;line-height:1.75}
@media(max-width:720px){.srp-engagement-steps{grid-template-columns:1fr;gap:8px}.srp-engagement-card{padding:26px 22px!important}.srp-engagement-card p,.srp-engagement-card li{font-size:15px!important}}
</style>
"""

engagement_card = """
<section class="srp-engagement-card" id="how-engagements-work" aria-labelledby="engagements-heading">
 <p class="srp-eyebrow">Our engagement process</p>
 <h2 id="engagements-heading">How engagements work</h2>
 <div class="srp-engagement-steps">
  <div class="srp-engagement-step"><span class="srp-number">01</span><h3>Initial consultation</h3><p>Tell us about your organization, aircraft, fleet, supplier concern, technology requirements, or research objective.</p></div>
  <div class="srp-engagement-step"><span class="srp-number">02</span><h3>Scope and proposal</h3><p>We review source availability, authorized data use, timing, deliverables, assumptions, and commercial terms.</p></div>
  <div class="srp-engagement-step"><span class="srp-number">03</span><h3>Engagement authorization</h3><p>After written agreement on the scope, we finalize engagement documentation and provide invoicing instructions.</p></div>
  <div class="srp-engagement-step"><span class="srp-number">04</span><h3>Research and delivery</h3><p>We provide agreed reports, analytical work products, or prototypes with sources, methodological limits, and review requirements.</p></div>
 </div>
 <div class="srp-engagement-footer">
  <p>StrategicRisk Partners provides independent research, analytics, and technology consulting. No insurance coverage is bound and no insurance premiums are collected through this website. Regulated insurance services and restricted-data processing require separate qualifications and authorization.</p>
  <p><strong>Request a consultation:</strong> <a class="srp-contact-link" href="mailto:info@sriskpartners.com">info@sriskpartners.com</a></p>
  <nav aria-label="Business policies" class="srp-policy-links"><a href="/terms-of-service/">Terms of Service</a><a href="/refund-policy/">Refund Policy</a><a href="/contact/">Contact SRP</a></nav>
 </div>
</section>
"""

def _enterprise_style_and_copy(relpath,replacements=(),first_h1=None):
    page=ROOT/relpath
    if not page.is_file():raise RuntimeError("Missing requested enterprise page: "+relpath)
    text=page.read_text("utf-8")
    if "srp-enterprise-2026" not in text:
        if "</head>" not in text:raise RuntimeError("Missing document head: "+relpath)
        text=text.replace("</head>",_SRP_ENTERPRISE_CSS+"</head>",1)
    if first_h1 is not None:
        pat=re.compile(r"<h1\b[^>]*>[\s\S]*?</h1>",re.I)
        if not pat.search(text):raise RuntimeError("Missing primary heading: "+relpath)
        text=pat.sub("<h1>"+_esc(first_h1)+"</h1>",text,count=1)
    for old,new in replacements:
        if old not in text:
            raise RuntimeError("Expected outdated copy was not found in "+relpath+": "+old)
        text=text.replace(old,new)
    page.write_text(text,encoding="utf-8")

_enterprise_style_and_copy("index.html",(
    ("Focused expertise.","Integrated research and technology solutions."),
    ("Defined deliverables. Transparent starting prices.","Defined scopes. Written proposals."),
),first_h1="Advancing decisions through aerospace intelligence")

_enterprise_style_and_copy("intelligence/index.html",(
    ("Four connected lines of business","Research, analytics and emerging technology"),
    ("Start with a paid research engagement","Start with a scoped research engagement"),
),first_h1="Turning complex research into connected intelligence")

_enterprise_style_and_copy("solutions/space/index.html",
    first_h1="Space risk analytics | Launch and satellite intelligence")

_enterprise_style_and_copy("services-pricing/index.html",
    first_h1="Integrated research and technology solutions")

# The gray text-on-gray legacy panel is replaced with a single accessible navy card.
services_file=ROOT/"services-pricing/index.html"
services_text=services_file.read_text("utf-8")
old_panel=r'<div\s+class="srisk-payment-panel"\s*>[\s\S]*?</div>'
if len(re.findall(old_panel,services_text,flags=re.I))!=1:
    raise RuntimeError("Cannot safely identify unique legacy ordering panel.")
services_text=re.sub(old_panel,engagement_card,services_text,count=1,flags=re.I)
services_text=services_text.replace("Services &amp; pricing","Services &amp; Consulting")
services_text=services_text.replace("Services & pricing","Services & Consulting")
services_file.write_text(services_text,encoding="utf-8")

# Reinforce accurate positioning, without introducing a fifth nav tab or public price.
def _add_service_line(page,section_id,heading,description):
    p=ROOT/page
    s=p.read_text("utf-8")
    if 'id="'+section_id+'"' in s:return
    match=re.search(r"</main\s*>",s,re.I)
    if not match:raise RuntimeError("Missing main section for "+page)
    line='<section class="srp-enterprise-solution" id="'+section_id+'"><h2>'+_esc(heading)+'</h2><p>'+_esc(description)+'</p><p><a href="mailto:info@sriskpartners.com?subject=SRP%20Consultation">Discuss your requirements: info@sriskpartners.com</a></p></section>'
    s=s[:match.start()]+line+s[match.start():]
    p.write_text(s,encoding="utf-8")

_add_service_line("index.html","srp-defining-capabilities","Aviation | Space | Technology | Defense-Industry Research",
    "Independent source-linked aviation risk intelligence, space and mission exposure research, enterprise AI and PowerShell workflow prototyping, supplier research, and management-ready analytics.")
_add_service_line("intelligence/index.html","srp-aerocie-capabilities","Introducing AeroCIE | Source-linked research workflows",
    "AeroCIE is an early-stage technology prototype exploring document provenance, evidence linking, deterministic checks and human review. Its interactive public graph is synthetic, not a validated live government feed or certified regulatory determination system.")
_add_service_line("solutions/space/index.html","srp-space-research-capabilities","Space intelligence beyond the atmosphere",
    "Source-linked research into launch events, satellite operating environments, published space-weather observations and Earth observation context, using appropriately licensed public data. No operational mission assurance, launch certification, flight-safety guidance or real-time hazard forecasting.")

# Validate copy, typography, CTA and portfolio assets before publishing.
out_services=services_file.read_text("utf-8")
if "How ordering works" in out_services or "Financing is offered" in out_services:
    raise RuntimeError("Old checkout and ordering language remains.")
if any(x not in out_services for x in ["How engagements work","srp-engagement-card","info@sriskpartners.com","Terms of Service"]):
    raise RuntimeError("Engagement-card regression.")
for rel in ["index.html","intelligence/index.html","services-pricing/index.html","solutions/space/index.html"]:
    doc=(ROOT/rel).read_text("utf-8")
    if "srp-enterprise-2026" not in doc:raise RuntimeError("Missing enterprise styles: "+rel)
    if "| NAICS 541690" in doc:raise RuntimeError("Unwanted NAICS badge: "+rel)
    if any(v in doc for v in ["$995","$2,995","$7,500"]):raise RuntimeError("Public pricing regression: "+rel)
if not (ROOT/"aerocie-demo/glow-effects.js").exists():raise RuntimeError("AeroCIE interactive asset missing")
if not (ROOT/"assets/srp/srp-satellite.webp").exists():raise RuntimeError("Space stock image missing")
print("SRP_OPTION_B_READY","engagement_card","replaced","readability","enhanced","pages",4,"no_public_prices",True,"aerocie",True)


# SRP 2026-10-26 | Corporate information architecture and editorial refresh.
import html as _srp_html
SRP_MENU = [("What We Do","/services-pricing/"),("Who We Are","/#who-we-are"),("Information","/intelligence/"),("Connect Us","/contact/")]
SRP_FOOTER = "2026 StrategicRisk Partners. All Rights Reserved."
PUBLIC_COPY_REPLACEMENTS = [
 ("Four concise examples of how selected FAA and NTSB records can inform better documentation requests and exposure discussions. No proprietary data claims or manufactured risk scores.",
  "Selected aerospace intelligence briefings translate regulatory, safety, and technical signals into clearer exposure insights, evidence priorities, and decision-ready context."),
 ("Research you can examine", "Featured Intelligence"),
 ("research you can examine", "Featured Intelligence"),
 ("public FAA and NTSB records can help answer", "connected aviation intelligence can illuminate"),
 ("Capabilities are scoped individually; no federal registration approval, contract award, CMMC certification, or clearance implied.",""),
 ("Illustrative simulation only | No live FAA, NASA, or DoD feeds | No verified regulatory decisions | Compliance: NOT_DETERMINED","")
]
PAGE_REBRAND_CSS="""<style id="srp-enterprise-nav">
.srp-capabilities{background:#f2f7fb;color:#081d36;padding:68px max(24px,calc((100% - 1130px)/2));}
.srp-capabilities h2{font:700 clamp(30px,3.6vw,48px)/1.15 system-ui,sans-serif;color:#081d36;margin:10px 0 12px}
.srp-capabilities p{color:#35536c;line-height:1.7;max-width:850px;font-size:17px}
.srp-capability-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin-top:28px}
.srp-capability-grid a{background:white;color:#0a3158;text-decoration:none;border:1px solid #d2e2ee;border-top:3px solid #197cbe;border-radius:5px;min-height:94px;display:flex;align-items:center;justify-content:center;padding:15px 10px;text-align:center;font:700 14px/1.4 system-ui,sans-serif}
.srp-capability-grid a:hover,.srp-capability-grid a:focus-visible{background:#e5f6fd;outline:2px solid #1782c5}
.srp-footnote-2026{padding:18px 20px;text-align:center;color:#bcd1e4;background:#051325;font:12px/1.5 system-ui,sans-serif}
.srp-site-nav-upgraded a{white-space:nowrap}
@media(max-width:800px){.srp-capability-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:480px){.srp-capability-grid{grid-template-columns:1fr}.srp-capabilities{padding:46px 20px}}
</style>"""
# No fabricated certifications or market size claims. Domain taxonomy describes offerings, not
# qualifications or completed government contracts.
CAPABILITIES="""
<section class="srp-capabilities" id="what-we-do" aria-labelledby="srp-what-title">
<div style="font:700 12px system-ui,sans-serif;color:#126fc0;letter-spacing:.16em">01 | WHAT WE DO</div>
<h2 id="srp-what-title">Intelligence and technology for complex decisions.</h2>
<p>We combine aerospace risk intelligence, structured data analysis, cyber risk advisory and technology consulting to help organizations assess exposure, improve workflows and manage uncertainty.</p>
<h3 style="font:700 20px system-ui,sans-serif;color:#07182d">Capabilities by Domain</h3>
<div class="srp-capability-grid">
<a href="/services-pricing/#defense-contractor-services">Aerospace</a>
<a href="/intelligence/">Data</a>
<a href="/services-pricing/#defense-contractor-services">Cyber</a>
<a href="/services-pricing/">Management Consulting</a>
<a href="/intelligence/#aerocie-network">Technology Services</a>
</div>
</section>
<section class="srp-capabilities" id="who-we-are" style="background:#07182d;color:#fff" aria-labelledby="srp-who-title">
<div style="font:700 12px system-ui,sans-serif;color:#65e5ef;letter-spacing:.16em">02 | WHO WE ARE</div>
<h2 id="srp-who-title" style="color:#fff">Independent perspective. Source-linked insight.</h2>
<p style="color:#d9e6f4">StrategicRisk Partners LLC is an Iowa-based independent research and technology consulting business serving aviation, aerospace, space and defense-industry organizations. Our work connects technical research, structured analysis and practical workflow development, with documented assumptions and human review.</p>
<a href="mailto:info@sriskpartners.com" style="color:#77e4fa;font-weight:700">Connect with our team | info@sriskpartners.com</a>
</section>
"""
# Place a minimal non-destructive accessibility-safe nav script after the site's own legacy scripts.
_NAV_JS = r"""<script id="srp-navigation-2026">
(function(){
  const items=[["What We Do","/services-pricing/"],["Who We Are","/#who-we-are"],["Information","/intelligence/"],["Connect Us","/contact/"]];
  function update(){
    const navs=[...document.querySelectorAll("header nav, nav#site-nav, header .nav")];
    const nav=navs.find(n=>n.querySelectorAll("a").length>=2);
    if(!nav)return;
    nav.classList.add("srp-site-nav-upgraded");
    nav.querySelectorAll("a").forEach(a=>a.remove());
    items.forEach(([label,href])=>{const a=document.createElement("a");a.textContent=label;a.href=href;nav.appendChild(a)});
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",update);
  else update();
})();
</script>"""
for page in ROOT.rglob("*.html"):
    if page == demo_path or page.parts[-2:] == ("aerocie-demo","index.html"):continue
    raw=page.read_text("utf-8")
    updated=raw
    for old,new in PUBLIC_COPY_REPLACEMENTS:
        updated=updated.replace(old,new)
    if "srp-navigation-2026" not in updated and "</body>" in updated:
        updated=updated.replace("</body>",_NAV_JS+"</body>",1)
    if "srp-enterprise-nav" not in updated and "</head>" in updated:
        updated=updated.replace("</head>",PAGE_REBRAND_CSS+"</head>",1)
    if "srp-footnote-2026" not in updated and "</body>" in updated:
        updated=updated.replace("</body>",'<div class="srp-footnote-2026">© '+SRP_FOOTER+"</div></body>",1)
    if updated!=raw:page.write_text(updated,encoding="utf-8")
# Homepage information hierarchy follows the exact five services and four-nav structure.
homepage=ROOT/"index.html"
s=homepage.read_text("utf-8")
if 'id="what-we-do"' not in s:
    location=re.search(r'</main\s*>',s,re.I)
    if not location:raise RuntimeError("Homepage missing main insertion point")
    s=s[:location.start()]+CAPABILITIES+s[location.start():]
    homepage.write_text(s,encoding="utf-8")
# Preserve the separate interactive demo disclaimer, without a long marketing warning on homepage.
demo_text=demo_path.read_text("utf-8")
if not ("SIMULATED" in demo_text and "NOT_DETERMINED" in demo_text):
    raise RuntimeError("Synthetic graph's own disclosure must remain on its demo page.")
# Reformat featured preview on the site: no narrow strip and no white text on a bright cover.
MARKET_PREVIEW_CSS="""<style id="srp-featured-publication-fix">
.market-home-teaser{grid-template-columns:minmax(0,1fr) minmax(250px,38%)!important;gap:26px!important;align-items:center!important;padding:30px!important}
.market-home-teaser img{display:block!important;width:100%!important;max-width:390px!important;height:auto!important;max-height:330px!important;object-fit:contain!important;margin:0 auto!important;border-radius:4px}
.market-home-teaser h2,.market-home-teaser h3,.market-home-teaser p,.market-home-teaser a{color:#f6fbff!important;text-shadow:0 2px 10px #061328}
.market-home-teaser a{color:#8be9ff!important}
@media(max-width:800px){.market-home-teaser{grid-template-columns:1fr!important;padding:22px!important}.market-home-teaser img{max-width:320px!important;max-height:240px!important}}
</style>"""
s=homepage.read_text("utf-8")
if "srp-featured-publication-fix" not in s and "</head>" in s:
    homepage.write_text(s.replace("</head>",MARKET_PREVIEW_CSS+"</head>",1),encoding="utf-8")
for rel in ["index.html","research/index.html","intelligence/index.html","services-pricing/index.html","research/aviation-market-overview-2026/index.html"]:
    txt=(ROOT/rel).read_text("utf-8")
    for old in ["Four concise examples of how selected FAA and NTSB records can inform better documentation requests and exposure discussions. No proprietary data claims or manufactured risk scores.","Capabilities are scoped individually; no federal registration approval, contract award, CMMC certification, or clearance implied.","Illustrative simulation only | No live FAA, NASA, or DoD feeds | No verified regulatory decisions | Compliance: NOT_DETERMINED"]:
        if old in txt:raise RuntimeError("Outdated copy remains: "+rel)
if len(re.findall(r'<a href="/(services-pricing|intelligence)/"',CAPABILITIES))<2:raise RuntimeError("Domain links incomplete")
print("SRP_NAV_COPY_2026_OK",len(SRP_MENU),"navitems",5,"domains", "publication_preview",True,"demo_disclosure_retained",True)

# SRP_REFUND_CTA_HIDDEN_2026
# A separate refund policy remains at its existing direct URL for contractual reference.
# This removes its prominent link from sales/consulting pages, not the policy itself.
import re as _srp_re
for _srp_rel in ["index.html","services-pricing/index.html","intelligence/index.html","contact/index.html","research/index.html"]:
    _srp_page = ROOT / _srp_rel
    if not _srp_page.is_file():
        continue
    _srp_html_str = _srp_page.read_text("utf-8")
    _srp_clean = _srp_re.sub(r'(?is)<a\b[^>]*\bhref\s*=\s*["\'][^"\']*refund-policy/["\'][^>]*>.*?</a>', "", _srp_html_str)
    _srp_clean = _srp_re.sub(r'(?is)<(?:a|button)\b[^>]*>\s*(?:Request a refund|Refund / Return|Refund &amp; Return|Refund Policy)\s*</(?:a|button)>', "", _srp_clean)
    if _srp_clean != _srp_html_str:
        _srp_page.write_text(_srp_clean, encoding="utf-8")
    if _srp_re.search(r'(?is)<a\b[^>]*\bhref\s*=\s*["\'][^"\']*refund-policy/["\']', _srp_clean):
        raise RuntimeError("Refund link remains on public marketing page: " + _srp_rel)
if not (ROOT / "refund-policy/index.html").is_file():
    raise RuntimeError("Underlying refund policy must remain accessible")
if "info@sriskpartners.com" not in (ROOT/"services-pricing/index.html").read_text("utf-8"):
    raise RuntimeError("Sales consultation CTA missing")
print("SRP_REFUND_CTA_REMOVED", True, "policy_retained", True)
