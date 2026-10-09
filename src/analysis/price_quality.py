"""Verify the exact dated closing quote used by a valuation, separately from history."""
import math

PRICE_TOLERANCE = 0.001


def latest_price_matches(quote_check, market):
    if not market or not market.get("latest_date"):
        return False
    check = next((c for c in quote_check.get("checks", [])
                  if c.get("date") == market["latest_date"]), None)
    if not check:
        return False
    primary = check.get("primary_close", check.get("yahoo_close"))
    reference = check.get("reference_close", check.get("kbs_close"))
    price = market.get("latest_close_vnd")
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v <= 0
           for v in (primary, reference, price)):
        return False
    return abs(primary / price - 1) <= 1e-9 and abs(primary - reference) / reference <= PRICE_TOLERANCE
