"""AeroCIE synthetic GA underwriting and MRO pipeline, Phase 24.

No network, claims prediction, personal pilot records or automatic insurance decisions.
Provides reproducible SQLite views, audit metadata and Power BI import tables.
"""
from __future__ import annotations
import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "sql" / "underwriting_schema.sql"
VERSION = "AEROCIE-UW-SYNTHETIC-2026-10-v1"
SEED = 20261029
AS_OF = "2026-10-29"
EXPORT_VIEWS = ("v_submission_triage", "v_triage_factors", "v_submission_features", "v_mro_latest", "v_mro_model_metrics", "v_severity_scenarios", "fact_ntsb_model_context", "fact_swim_operations", "source_registry")


def _hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def synthetic_fixture() -> dict:
    """Generate a fixed reproducible test fixture with missing-data examples."""
    rng = random.Random(SEED)
    aircraft = [
      ("A001", "N-DEMO01", "Cessna", "172S", "FIXED_WING", 2011, 0),
      ("A002", "N-DEMO02", "Beechcraft", "King Air 350", "FIXED_WING", 2001, 0),
      ("A003", "N-DEMO03", "Bell", "407", "ROTOR_WING", 1998, 1),
      ("A004", "N-DEMO04", "Gulfstream", "G650", "BUSINESS_JET", 2018, 1),
      ("A005", "N-DEMO05", "Cessna", "172S", "FIXED_WING", 1983, 0),
      ("A006", "N-DEMO06", "Pilatus", "PC-12", "FIXED_WING", 2015, 1),
    ]
    pilots = [
      ("P001", "COMMERCIAL", 2150, 680, 1),
      ("P002", "ATP", 5250, 1800, 1),
      ("P003", "PRIVATE", 420, 12, 0),
      ("P004", "ATP", 3200, 420, 1),
      ("P005", "COMMERCIAL", 880, 72, 1),
      ("P006", "COMMERCIAL", 1250, 99, 0),
    ]
    facilities = [("F001", "Synthetic MRO Northwest", "US-NW", "US"),
                  ("F002", "Synthetic MRO Central", "US-MW", "US"),
                  ("F003", "Synthetic MRO Atlantic", "US-NE", "US")]
    mro = []
    models = sorted({(a[2],a[3]) for a in aircraft})
    for manufacturer, model in models:
        if model == "PC-12":
            continue  # intentionally missing MRO coverage -> must refer
        for idx,facility in enumerate(facilities):
            days = rng.randint(12,78)
            availability = round(rng.uniform(.15,.95),3)
            cost = round(rng.uniform(1.00,1.72),3)
            mro.append((f"M-{len(mro)+1:03d}", facility[0],manufacturer,model,AS_OF,days,availability,cost,"SRC-MRO"))
    mro.append(("M-OLD", "F001","Cessna","172S","2026-08-15",200,.05,2.6,"SRC-MRO"))
    submissions = [(f"S{i+1:03d}",AS_OF,a[0],pilots[i][0],
                    "PRIVATE_PLEASURE" if i%2==0 else "COMMERCIAL_NON_SCHEDULED",
                    130 + i*155, (0,0,2,0,1,0)[i],(220000,2800000,1700000,24000000,175000,4900000)[i],"SRC-INTAKE")
                   for i,a in enumerate(aircraft)]
    # Missing pilot means no synthetic personal-data enrichment or inferred risk.
    submissions.append(("S007",AS_OF,"A001",None,"PRIVATE_PLEASURE",None,None,250000,"SRC-INTAKE"))
    nt = [(f"N{i:03d}",manufacturer,model,"2021-01-01","2025-12-31",rng.randint(0,8),rng.randint(10000,120000),"SRC-NTSB") for i,(manufacturer,model) in enumerate(models,1)]
    swim = [(f"O{i:03d}",manufacturer,model,"2026-09-01","2026-09-30",rng.randint(80,9000),"SRC-SWIM") for i,(manufacturer,model) in enumerate(models,1)]
    return {"aircraft":aircraft,"pilots":pilots,"facilities":facilities,"mro":mro,"submissions":submissions,"ntsb":nt,"swim":swim}


def _sql_insert(con: sqlite3.Connection, table: str, columns: tuple[str, ...], rows: list | tuple) -> None:
    # Column and table names are constants supplied by internal callers, never user input.
    cols=",".join(columns)
    marks=",".join("?" for _ in columns)
    con.executemany(f"INSERT INTO {table} ({cols}) VALUES ({marks})",rows)


def create_db(path: Path, fixture: dict | None = None) -> dict:
    """Create a new SQLite file atomically at an exclusive path; no overwrite."""
    fixture = synthetic_fixture() if fixture is None else fixture
    if path.suffix.lower() not in (".db", ".sqlite3"):
        raise ValueError("Database output must have .db or .sqlite3 suffix")
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite: {path}")
    if not SCHEMA_PATH.is_file():
        raise FileNotFoundError("Schema is missing")
    path.parent.mkdir(parents=True,exist_ok=True)
    # Claim file exclusively before connecting. Clean only the new output on failure.
    with path.open("xb"):
        pass
    try:
        with sqlite3.connect(path) as con:
            con.execute("PRAGMA foreign_keys=ON")
            con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            for key,provider in (("MRO","Synthetic MRO availability"),("INTAKE","Synthetic underwriting intake"),
                                 ("NTSB","NTSB CAROL shaped synthetic aggregates"),("SWIM","FAA SWIM shaped synthetic operations")):
                source={"data":fixture["mro" if key=="MRO" else "submissions" if key=="INTAKE" else "ntsb" if key=="NTSB" else "swim"],"kind":key,"version":VERSION}
                con.execute("INSERT INTO source_registry VALUES (?,?,?,?,?,?,?, ?,1)",
                            (f"SRC-{key}",provider,f"synthetic_{key.lower()}",None,AS_OF,stamp,_hash(source),"SYNTHETIC_ONLY"))
            _sql_insert(con,"dim_aircraft",("aircraft_id","registration","manufacturer","model","category","year_built","composite_material_flag"),fixture["aircraft"])
            _sql_insert(con,"dim_pilot",("pilot_id","certificate_level","total_flight_hours","make_model_hours","recurrent_training_verified"),fixture["pilots"])
            _sql_insert(con,"dim_mro_facility",("facility_id","name","region","country_code"),fixture["facilities"])
            _sql_insert(con,"fact_mro_constraints",("constraint_id","facility_id","manufacturer","model","as_of","repair_wait_days","parts_availability_index","parts_cost_index","source_id"),fixture["mro"])
            _sql_insert(con,"fact_underwriting_submissions",("submission_id","submitted_on","aircraft_id","pilot_id","operation_type","annual_flight_hours","losses_last_five_years","requested_hull_value_usd","source_id"),fixture["submissions"])
            _sql_insert(con,"fact_ntsb_model_context",("context_id","manufacturer","model","period_start","period_end","event_count","denominator_flight_hours","source_id"),fixture["ntsb"])
            _sql_insert(con,"fact_swim_operations",("observation_id","manufacturer","model","period_start","period_end","operations_count","source_id"),fixture["swim"])
            con.execute("INSERT INTO model_policy VALUES (?,?,?,?,?,?)",
                        ("SYNTHETIC_V1",VERSION,25,70,0,"Uncalibrated synthetic research heuristic. Advisory triage only; human underwriter decides."))
            rows=con.execute("SELECT submission_id,risk_points,triage_recommendation,insufficient_evidence FROM v_submission_triage ORDER BY submission_id").fetchall()
            con.commit()
        return {"db_path":str(path),"schema_version":VERSION,"fixture_hash":_hash(fixture),"submission_count":len(rows),"triage":[{"submission_id":r[0],"risk_points":r[1],"triage_recommendation":r[2],"insufficient_evidence":bool(r[3])} for r in rows],"release_authorized":False}
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def export_tables(db_path: Path, folder: Path) -> dict:
    """Export only allowlisted SQL views and synthetic source metadata as CSV/JSON."""
    if folder.exists():
        raise FileExistsError(f"Refusing to overwrite export folder: {folder}")
    with sqlite3.connect(f"file:{db_path.resolve()}?mode=ro",uri=True) as con:
        con.row_factory=sqlite3.Row
        for (v,) in con.execute("SELECT is_synthetic FROM source_registry"):
            if v != 1:
                raise ValueError("Only synthetic exports supported")
        results=[]
        try:
            folder.mkdir(parents=True,exist_ok=False)
            for view in EXPORT_VIEWS:
                cur=con.execute(f"SELECT * FROM {view}")
                columns=[c[0] for c in cur.description]
                target=folder / f"{view}.csv"
                with target.open("w",newline="",encoding="utf-8-sig") as f:
                    w=csv.writer(f)
                    w.writerow(columns)
                    count=0
                    for row in cur:
                        # Prefix spreadsheet formula tokens so a future CSV consumer will not evaluate injected formulas.
                        values=["'"+v if isinstance(v,str) and v.startswith(("=","+","-","@")) else v for v in row]
                        w.writerow(values)
                        count+=1
                results.append({"view":view,"rows":count,"sha256":hashlib.sha256(target.read_bytes()).hexdigest()})
            (folder/"manifest.json").write_text(json.dumps({"schema":VERSION,"data_mode":"SYNTHETIC_ONLY","authority":"UNDERWRITER_REVIEW_REQUIRED","tables":results},indent=2)+"\n",encoding="utf-8")
            return {"export_path":str(folder),"tables":results,"synthetic_only":True}
        except BaseException:
            # only remove newly created files from claimed folder
            import shutil
            shutil.rmtree(folder)
            raise


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db",type=Path,required=True)
    parser.add_argument("--export-dir",type=Path)
    args=parser.parse_args(argv)
    try:
        result=create_db(args.db)
        if args.export_dir:
            result["exports"]=export_tables(args.db,args.export_dir)
    except (ValueError,FileExistsError,sqlite3.Error,OSError) as e:
        print(f"AeroCIE synthetic pipeline refused: {e}",file=sys.stderr)
        return 1
    print(json.dumps(result,indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
