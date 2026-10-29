"""Static AeroCIE underwriting research dashboard for local synthetic demonstration."""
from __future__ import annotations
import argparse
from html import escape
import json
from pathlib import Path
import sqlite3
import sys


def render(db: Path) -> str:
    from . import underwriting_quality
    quality = underwriting_quality.audit_database(db)
    underwriting_quality.require_pass(quality)
    # SQLite opened read-only; no writes or remote resources.
    with sqlite3.connect(f"file:{db.resolve()}?mode=ro", uri=True) as con:
        con.row_factory=sqlite3.Row
        data=[dict(r) for r in con.execute("SELECT * FROM v_submission_triage ORDER BY submission_id")]
        stress=[dict(r) for r in con.execute("SELECT * FROM v_severity_scenarios ORDER BY scenario_base_usd DESC, submission_id") ]
        sources=[dict(r) for r in con.execute("SELECT source_id,provider,source_as_of,is_synthetic,license_status FROM source_registry ORDER BY source_id")]
        if not data or not sources or any(src["is_synthetic"] != 1 for src in sources):
            raise ValueError("Dashboard requires complete synthetic data")
    e=lambda x:escape("Unknown" if x is None else str(x),quote=True)
    # SQL computes all three scenarios; the HTML never fabricates a value for missing inputs.
    stress_available=[r for r in stress if r["scenario_base_usd"] is not None]
    max_stress=max((r["scenario_high_usd"] for r in stress_available),default=0) or 1
    formatted_usd=lambda v:"Unavailable" if v is None else "$"+format(round(v),",")
    missing_count=sum(r["scenario_base_usd"] is None for r in stress)
    exposed_hull=sum(int(r["requested_hull_value_usd"]) for r in stress if r["requested_hull_value_usd"] is not None)
    scenario_rows=[]
    for record in stress:
        base_value=record["scenario_base_usd"]
        high_value=record["scenario_high_usd"]
        low_value=record["scenario_low_usd"]
        label=record["submission_id"]+" | "+record["manufacturer"]+" "+record["model"]
        if base_value is None:
            scenario_rows.append('<div class="scenario-row unresolved"><div class="scenario-case"><strong>'+e(label)+'</strong>'
                                 '<small>Evidence incomplete | Review required</small></div>'
                                 '<div class="scenario-unavailable">No cost scenario calculated</div></div>')
        else:
            width=max(1,100*float(base_value)/max_stress)
            high_width=max(1,100*float(high_value)/max_stress)
            scenario_rows.append('<div class="scenario-row"><div class="scenario-case"><strong>'+e(label)+'</strong>'
                                 '<small>'+e(record["triage_recommendation"])+" review | "+e(record["mro_severity_days"])+
                                 ' proxy wait days | parts '+e(record["mro_cost_pressure_index"])+
                                 '</small></div><div class="bar-area"><div class="bar-range" style="width:'+
                                 format(high_width,'.2f')+'%"></div><div class="bar-core" style="width:'+
                                 format(width,'.2f')+'%"></div></div><strong class="bar-value">'+
                                 e(formatted_usd(base_value))+'</strong><small class="scenario-range">'+
                                 e(formatted_usd(low_value))+" – "+e(formatted_usd(high_value))+'</small></div>')
    quote_spotlight=max(
        (r for r in stress_available if r["triage_recommendation"] == "Quote"),
        key=lambda r: r["scenario_base_usd"], default=None)
    spotlight=(
        '<p class="spotlight"><strong>Underwriting review example:</strong> '
        +e(quote_spotlight["submission_id"])+ ' received a Quote review label while its illustrative '
        'base repair scenario is <strong>'+e(formatted_usd(quote_spotlight["scenario_base_usd"]))+'</strong>. '
        'The scoring label does not measure price adequacy. Check the assumptions and policy terms.</p>'
        if quote_spotlight else '<p class="spotlight">No complete Quote-labelled case is present in this sample.</p>')
    stress_cards=''.join('<div class="stress-stat"><b>'+e(v)+'</b><span>'+e(title)+'</span></div>' for v,title in [
        (len(stress),"Submissions reviewed"),
        (missing_count,"Insufficient evidence"),
        (formatted_usd(exposed_hull),"Requested hull total | not insured sum"),
        ("Unknown","Premium adequacy | no policy rates supplied")
    ])
    cards=''.join(f'<div class="stat"><b>{n}</b><span>{label}</span></div>' for n,label in [
        (len(data),"Synthetic submissions"),
        (sum(x["triage_recommendation"]=="Quote" for x in data),"Quote candidates"),
        (sum(x["triage_recommendation"]=="Refer" for x in data),"Refer for review"),
        (sum(x["triage_recommendation"]=="Decline" for x in data),"Decline review candidates")
    ])
    rows=[]
    for rec in data:
        status=rec["triage_recommendation"]
        risk=rec["risk_points"]
        badge={'Quote':'quote','Refer':'refer','Decline':'decline'}[status]
        rows.append(f'<tr><td><strong>{e(rec["submission_id"])}</strong><small>{e(rec["category"])}</small></td>'
         f'<td>{e(rec["manufacturer"])} {e(rec["model"])}</td><td>{e(rec["aircraft_age_years"])} yr</td>'
         f'<td>{e(rec["total_flight_hours"])} hr</td><td>{e(rec["mro_severity_days"])} days</td>'
         f'<td>{e(rec["mro_cost_pressure_index"])}</td><td>{e(risk) if risk is not None else "Missing data"}</td>'
         f'<td><span class="pill {badge}">{e(status)}</span></td></tr>')
    factor_keys=[('age_points','Aircraft age'),('total_time_points','Pilot total hours'),
                 ('type_time_points','Make/model hours'),('loss_points','Reported loss history'),
                 ('mro_points','MRO wait proxy'),('composite_points','Composite material'),
                 ('training_points','Recurrent training')]
    traces=[]
    for rec in data:
        factors=' | '.join(f'{name}: {rec[key]}' for key,name in factor_keys if rec[key] is not None)
        notes=('Missing or stale source fields; obtain evidence and refer to underwriter.'
               if rec['insufficient_evidence'] else f'Illustrative factors: {factors}.')
        traces.append('<details><summary>'+e(rec['submission_id'])+' | '+e(rec['manufacturer'])+' '
                      +e(rec['model'])+'</summary><p>'+e(notes)+'</p>'
                      '<p>Source: '+e(rec['submission_source_id'])+' | Latest MRO: '+e(rec['latest_observation'])+
                      ' | Oldest MRO: '+e(rec['oldest_observation'])+'</p></details>')
    srclines=''.join(f'<li><strong>{e(s["provider"])}</strong><span>{e(s["source_as_of"])} | {e(s["license_status"])}</span></li>' for s in sources)
    checks=quality["summary"]
    quality_kpis=''.join(
        '<div class="stress-stat"><b>'+e(value)+'</b><span>'+e(name)+'</span></div>'
        for name, value in [
            ("Local fingerprints matched", str(checks["source_fingerprints_matched"] + checks["dimension_fingerprints_matched"]) + " / " +
             str(checks["source_fingerprints_expected"] + checks["dimension_fingerprints_expected"])),
            ("Inputs present | synthetic", checks["inputs_present"]),
            ("Refer for evidence", checks["referred_for_missing_evidence"]),
            ("Quality gate", quality["quality_gate"]),
        ])
    quality_rows=''.join(
        '<div class="quality-row"><b>' + e(x["submission_id"]) + '</b><span>' +
        e(x["quality_status"]) + '</span><span>' +
        e(" | ".join(x["issue_codes"]) or "No input completeness issues detected") + '</span></div>'
        for x in quality["submissions"])
    css="""
    *{box-sizing:border-box}body{margin:0;font:15px/1.55 Montserrat,Arial,sans-serif;color:#152f4c;background:#eef4f9}
    header{background:linear-gradient(115deg,#061c35,#163f6d);color:white;padding:38px max(28px,calc((100vw - 1150px)/2))}
    .brand{font-size:13px;letter-spacing:2px;font-weight:700;color:#9ed6ff}h1{font-size:clamp(28px,4.5vw,46px);margin:14px 0 10px;line-height:1.1}
    .desc{color:#c1d8ec;max-width:780px}main{max-width:1190px;padding:24px;margin:auto}.notice{border-left:4px solid #b58134;background:#fff6e6;padding:14px 17px;border-radius:4px;margin-bottom:20px}
    .metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.stat{background:#fff;border:1px solid #d6e3ee;border-radius:8px;padding:18px}
    .stat b{font-size:30px;display:block;color:#1464a6}.stat span{font-size:11px;letter-spacing:.3px;color:#516a83}
    section{margin:22px 0;padding:22px;background:white;border:1px solid #dbe4ed;border-radius:8px}
    h2{font-size:18px;margin:0 0 13px}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:930px;font-size:12px}
    th,td{text-align:left;padding:12px 9px;border-bottom:1px solid #e3eaf2}th{background:#edf4fb;color:#376085;white-space:nowrap}
    small{display:block;color:#6b849a}.pill{font-size:11px;border-radius:4px;padding:6px 9px;font-weight:bold;white-space:nowrap}
    .quote{color:#0a6b49;background:#daf5e9}.refer{color:#7e5512;background:#fcf1d7}.decline{color:#9b3131;background:#fbe3e4}
    ul{display:grid;grid-template-columns:repeat(2,1fr);gap:13px;padding-left:18px}li span{display:block;color:#678299;font-size:12px}
    .fine{font-size:12px;color:#526e87}details{padding:11px;border-bottom:1px solid #dce6ef}summary{cursor:pointer;color:#144b7c;font-weight:700}@media(max-width:760px){.metrics,ul{grid-template-columns:repeat(2,1fr)}section{padding:15px}}

    .risk-hero{border:1px solid #21496c;background:linear-gradient(130deg,#061b32,#103b61);color:#e8f4ff;padding:28px}
    .risk-hero h2{font-size:clamp(22px,3vw,31px);line-height:1.2;max-width:850px;margin:7px 0}
    .spotlight{padding:12px 14px;border-left:3px solid #2973ae;background:#edf6fe;color:#254b68;font-size:13px}
    .risk-hero .teaser{max-width:780px;color:#c6dbea;font-size:14px}
    .risk-label{color:#80ceff;letter-spacing:2px;font-size:11px;font-weight:800}
    .stress-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:22px 0}
    .stress-stat{background:#f1f7fc;border:1px solid #d7e7f4;border-radius:8px;padding:13px;min-width:0}
    .stress-stat b{display:block;font-size:24px;color:#153e65;overflow-wrap:anywhere}
    .stress-stat span{display:block;font-size:10px;color:#45607c}
    .scenario-row{display:grid;grid-template-columns:250px minmax(110px,1fr) 110px 126px;gap:13px;align-items:center;padding:14px 0;border-bottom:1px solid #dbe5ee}
    .scenario-case strong{display:block;font-size:13px}.scenario-case small{display:block;font-size:11px;color:#5c7089}
    .bar-area{position:relative;height:22px;border-radius:5px;background:#eef3f8;overflow:hidden}
    .bar-range{position:absolute;left:0;top:0;height:100%;background:#b9d6ea;border-radius:4px}
    .bar-core{position:absolute;left:0;top:4px;height:14px;background:#236ba8;border-radius:4px}
    .bar-value{font-size:15px;text-align:right;color:#164d7d}.scenario-range{font-size:11px;text-align:right;color:#506b84}
    .scenario-unavailable{color:#97542c;font-size:12px;grid-column:2/5}
    .quality-row{display:grid;grid-template-columns:90px 230px 1fr;align-items:start;gap:13px;padding:12px 0;border-bottom:1px solid #e1e9f1;font-size:12px}
    .quality-row span{overflow-wrap:anywhere}.quality-row b{color:#123e63}
    @media(max-width:760px){.quality-row{grid-template-columns:70px minmax(0,1fr)}.quality-row span:last-child{grid-column:2}}
    .assumptions{padding:13px;background:#f4f7fb;border:1px solid #d9e4ee;font-size:12px;color:#46637c;margin-top:16px;line-height:1.65}
    .assumptions strong{color:#163b61}
    @media(max-width:760px){.stress-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.scenario-row{grid-template-columns:1fr 100px;gap:6px}.bar-area{grid-column:1/3;grid-row:2}.bar-value{grid-column:2;grid-row:1}.scenario-case{grid-column:1;grid-row:1}.scenario-range{grid-column:2;grid-row:3}.scenario-unavailable{grid-column:1/3;grid-row:2}}
    @media print{body{background:white}header{background:#061c35;print-color-adjust:exact;-webkit-print-color-adjust:exact}section{break-inside:avoid}}
    """
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src &#39;none&#39;;style-src &#39;unsafe-inline&#39;;base-uri &#39;none&#39;">'
        '<title>AeroCIE | GA Underwriting Intelligence</title><style>'+css+'</style></head><body><header>'
        '<div class="brand">STRATEGICRISK PARTNERS | AEROCIE</div><h1>Aviation underwriting<br>decision support</h1>'
        '<p class="desc">General aviation triage | MRO constraints | Source evidence | Power BI staging</p></header><main>'
        '<div class="notice"><strong>SYNTHETIC DEMONSTRATION</strong> | Model scores are uncalibrated research heuristics. '
        'All Quote, Refer and Decline labels require an authorized underwriter. No premium, loss expectation or binding recommendation is calculated.</div>'
        '<section class="risk-hero"><div class="risk-label">POTENTIAL SEVERITY EXPOSURE</div>'
        '<h2>Which risks deserve another look before you quote?</h2>'
        '<p class="teaser">See simulated repair delay and parts cost pressure alongside underwriting review flags. '
        'Inspect evidence gaps before making a pricing decision.</p></section>'
        '<section aria-label="Evidence quality and decision controls"><h2>Integrity checks and evidence gaps</h2>'
        '<p class="fine">A matching local fingerprint confirms a dataset has not changed since import. '
        'It does not authenticate an external provider or establish predictive accuracy. '
        'All labels require underwriting review.</p>'
        '<div class="stress-metrics">'+quality_kpis+'</div><div class="quality-list">'+quality_rows+'</div></section>'
        '<section aria-label="Repair stress scenarios"><h2>Repair cost sensitivity | synthetic stress scenarios</h2>'
        '<p class="fine">Each bar ranks an illustrative cost stress under explicit assumptions. '
        'Darker bar = base scenario; pale bar = high scenario. Amounts are not observed losses, expected claims, '
        'premium gaps, or price recommendations.</p>'
        '<div class="stress-metrics">'+stress_cards+'</div>'+spotlight+
        '<div role="list" aria-label="Synthetic repair stress comparison">'+''.join(scenario_rows)+'</div>'
        '<div class="assumptions"><strong>Scenario assumptions:</strong> low = $100 per wait day and 0.25% '
        'of requested hull value per parts index increment over 1.0; base = $250 and 0.50%; '
        'high = $500 and 1.00%. Formula = wait proxy × daily assumption + hull value × parts '
        'percentage × max(parts index − 1.0, 0). These assumptions are not calibrated using '
        'claim records. A price adequacy conclusion requires premium and verified loss data.</div></section>'
        '<div class="metrics">'+cards+'</div><section><h2>Underwriting submission triage</h2><div class="scroll"><table><thead><tr>'
        '<th>Case</th><th>Airframe</th><th>Age</th><th>Pilot time</th><th>MRO severity</th><th>Parts cost index</th>'
        '<th>Risk points</th><th>Research label</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></section><section><h2>Evidence and scoring explanations</h2><p class="fine">Expand a synthetic submission to inspect its factor contributions and source dates.</p>'+''.join(traces)+'</section>'
        '<section><h2>Source registry and data lineage</h2><ul>'+srclines+'</ul>'
        '<p class="fine">Synthetic FAA SWIM-shaped operational counts and NTSB-shaped model context are available as separate tables. '
        'They are excluded from individual pilot or claims scoring. MRO severity is a repair wait-time proxy weighted by parts scarcity.</p></section>'
        '<section><h2>Methodology</h2><p class="fine">Airframe age, synthetic pilot experience, five-year declared submission losses, '
        'composite material flag, recurrent training status and MRO wait-time index produce a transparent 0–100 score. '
        'Missing evidence returns Refer with no score. Thresholds: Quote ≤25, Refer 26–69, Decline ≥70; all are review labels. '
        'No demonstrated predictive accuracy or actual insurance rates. The cost stress scenarios are assumption sensitivity examples, with unavailable values when evidence is missing.</p></section></main></body></html>')


def write(db: Path, output: Path) -> dict:
    html=render(db)
    if output.suffix.lower()!='.html' or output.exists() or output.resolve()==db.resolve():
        raise ValueError('New .html output path required')
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f: f.write(html)
    return {'html_path':str(output),'external_release_authorized':False}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',type=Path,required=True);p.add_argument('--out-html',type=Path,required=True)
    a=p.parse_args(argv)
    try: print(json.dumps(write(a.db,a.out_html),indent=2))
    except (ValueError,OSError,sqlite3.Error) as exc:
        print(f'Preview refused: {exc}',file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
