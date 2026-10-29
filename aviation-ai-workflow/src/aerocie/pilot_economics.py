"""AeroCIE pilot economics calculator using client supplied timing assumptions.

Projected labor savings are scenarios, not verified claims savings or guarantees.
"""
from __future__ import annotations
import argparse
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_CEILING
import json
from pathlib import Path
import sys

FIELDS = frozenset({"monthly_submissions", "baseline_minutes_per_submission", "aerocie_minutes_per_submission",
                    "loaded_hourly_analyst_cost_usd", "monthly_subscription_usd",
                    "monthly_source_license_cost_usd", "monthly_support_cost_usd"})
MONEY = Decimal("0.01")


def _value(obj: dict, key: str) -> Decimal:
    raw = obj[key]
    if type(raw) is bool or not isinstance(raw, (int, float, str)):
        raise ValueError(f"Invalid {key}")
    try:
        x = Decimal(str(raw))
    except InvalidOperation as e:
        raise ValueError(f"Invalid {key}") from e
    if not x.is_finite() or x < 0 or x > Decimal("10000000"):
        raise ValueError(f"Invalid range for {key}")
    return x


def _money(x: Decimal) -> float:
    return float(x.quantize(MONEY, rounding=ROUND_HALF_UP))


def calculate(assumptions: dict) -> dict:
    if not isinstance(assumptions, dict) or set(assumptions) != FIELDS:
        raise ValueError("Expected exactly the economic assumption fields")
    vals = {k:_value(assumptions,k) for k in FIELDS}
    if vals["monthly_submissions"] != vals["monthly_submissions"].to_integral_value():
        raise ValueError("monthly_submissions must be an integer")
    volume = vals["monthly_submissions"]
    manual = vals["baseline_minutes_per_submission"]
    assisted = vals["aerocie_minutes_per_submission"]
    minutes = volume * (manual - assisted)
    hours = minutes / Decimal(60)
    gross = hours * vals["loaded_hourly_analyst_cost_usd"]
    recurring = sum((vals[k] for k in ("monthly_subscription_usd", "monthly_source_license_cost_usd", "monthly_support_cost_usd")),Decimal("0"))
    value_per_submission = (manual - assisted) * vals["loaded_hourly_analyst_cost_usd"] / Decimal(60)
    break_even_volume = (recurring / value_per_submission).to_integral_value(rounding=ROUND_CEILING) if value_per_submission > 0 else None
    return {
        "schema":"AEROCIE-PILOT-ECONOMICS-v1",
        "monthly_submission_volume":int(volume),
        "net_monthly_hours_saved":float(round(hours,2)),
        "gross_monthly_labor_value_usd":_money(gross),
        "monthly_total_cost_usd":_money(recurring),
        "monthly_submissions_for_labor_only_break_even": int(break_even_volume) if break_even_volume is not None else None,
        "monthly_net_operational_value_usd":_money(gross-recurring),
        "annual_subscription_revenue_to_srp_usd":_money(vals["monthly_subscription_usd"]*12),
        "monthly_cost_coverage_ratio":float(round(gross/recurring,2)) if recurring else None,
        "assumptions": {k:float(v) for k,v in sorted(vals.items())},
        "note":"Scenario from supplied assumptions only; excludes implementation, change management, model errors and loss severity. No claim savings included."
    }


def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--assumptions",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args(argv)
    try:
        if args.assumptions.resolve()==args.out.resolve() or args.out.exists() or args.out.suffix.lower()!=".json":
            raise ValueError("Supply a new .json output path")
        result=calculate(json.loads(args.assumptions.read_text(encoding="utf-8-sig")))
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open("x",encoding="utf-8") as out:
            json.dump(result,out,indent=2)
            out.write("\n")
        print(json.dumps({"output":str(args.out),"net_monthly_value":result["monthly_net_operational_value_usd"]}))
        return 0
    except (ValueError,KeyError,OSError,TypeError,json.JSONDecodeError) as exc:
        print(f"Pilot economics refused: {exc}",file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
