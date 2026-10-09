"""Collect independent macro and industry sources without manual data entry."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from src.data.macro import collect_macro
from src.data.industry import collect_industry
from src.analysis.context import analyze_context

def collect_context(ticker,as_of,financial,root,run_id):
    with ThreadPoolExecutor(max_workers=2) as pool:
        macro_future=pool.submit(collect_macro,as_of,root,run_id)
        industry_future=pool.submit(collect_industry,ticker,as_of,financial,root,run_id)
        macro,industry=macro_future.result(),industry_future.result()
    macro,industry=analyze_context(macro,industry,financial)
    return {"macro":macro,"industry":industry,"sources":macro["sources"]+industry["sources"],
            "errors":macro["errors"]+industry["errors"],"warnings":macro["warnings"]+industry["warnings"]}
