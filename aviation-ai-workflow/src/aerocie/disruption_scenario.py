"""Internal synthetic illustration of incremental disruption costs, in USD.

Run: python -m src.aerocie.disruption_scenario
Assumes the same replacement flying and fuel demand for both alternatives.
Direct costs are paid during the scenario; starting cash is illustrative.
"""
from dataclasses import dataclass
from decimal import Decimal as D


@dataclass(frozen=True)
class Disruption:
    downtime_days: int
    replacement_daily_usd: D
    gallons_required: D
    normal_price: D
    starting_cash: D


@dataclass(frozen=True)
class FuelOption:
    name: str
    available_gallons: D
    delivered_price: D
    fixed_fee: D


def compare(case: Disruption, option: FuelOption) -> dict:
    amounts = (case.replacement_daily_usd, case.gallons_required, case.normal_price,
               case.starting_cash, option.available_gallons, option.delivered_price, option.fixed_fee)
    if type(case.downtime_days) is not int or case.downtime_days < 0:
        raise ValueError("Downtime must be a nonnegative whole number of days")
    if any(not value.is_finite() or value < 0 for value in amounts):
        raise ValueError("Amounts must be finite and nonnegative")
    shortfall = max(D(0), case.gallons_required - option.available_gallons)
    if shortfall:
        return {"available": False, "uncovered_gallons": shortfall}
    downtime = case.downtime_days * case.replacement_daily_usd
    fuel_cash = case.gallons_required * option.delivered_price + option.fixed_fee
    fuel_increment = fuel_cash - case.gallons_required * case.normal_price
    return {"available": True, "replacement_cost": downtime, "fuel_cash": fuel_cash,
            "incremental_cost": downtime + fuel_increment,
            "remaining_cash": case.starting_cash - downtime - fuel_cash}


def main():
    print("SRP | Synthetic internal disruption scenario | USD")
    print("Replacement aircraft rate excludes fuel. Same 10,000 gallons under each option.")
    print("Baseline fuel $4.00/gal. Starting cash $150,000. No other cash flows modeled.")
    print("Supplier A: 10,000 gal at $4.60. B: 12,000 at $4.25 + $2,000 fee.")
    print("Supplier C: 7,000 gal at $4.10. Replacement aircraft: $5,000/day.")
    options = (FuelOption("A", D(10000), D("4.60"), D(0)),
               FuelOption("B", D(12000), D("4.25"), D(2000)),
               FuelOption("C", D(7000), D("4.10"), D(0)))
    for days in (3, 7, 14):
        case = Disruption(days, D(5000), D(10000), D(4), D(150000))
        for option in options:
            result = compare(case, option)
            prefix = f"{days:2} days | Supplier {option.name}"
            if result["available"]:
                print(f"{prefix} | incremental cost ${result['incremental_cost']:,.2f}"
                      f" | remaining cash ${result['remaining_cash']:,.2f}")
            else:
                print(f"{prefix} | short {result['uncovered_gallons']:,} gallons")


if __name__ == "__main__":
    main()
