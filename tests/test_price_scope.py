"""Latest-quote valuation must remain independent of recent-history verification."""
from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.analysis.market import analyze_market
from src.analysis.price_quality import latest_price_matches
from src.analysis.conclusion import build_conclusion
from src.analysis.valuation import analyze_valuation
from src.data.research import compare_prices
from src.reporting.pdf_exporter import generate_report
from test_valuation_upgrade import financial, company, result

NOW=date(2026,10,9)


class PriceScopeTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{"date":f"2026-09-{i+1:02}","close":19000+i*50,"adjusted_close":18000+i*50,"volume":100,"source_id":"fixture"} for i in range(20)]
        self.rows[-1].update(date="2026-10-08",close=20000)
        self.payload={"data_day":[{"t":r["date"],"c":r["close"]} for r in self.rows]}
        self.payload["data_day"][0]["c"]=18000
        self.quote=compare_prices(self.rows,self.payload,NOW)
        self.market=analyze_market(self.rows,self.quote)

    def valuation(self,q=None,m=None):
        return analyze_valuation(financial(),m or self.market,company(),q or self.quote,NOW)

    def test_history_mismatch_does_not_block_verified_latest_price(self):
        self.assertEqual(self.quote["status"],"unverified")
        self.assertEqual(self.quote["latest_status"],"matched")
        self.assertEqual(self.quote["matched_count"],19)
        self.assertTrue(latest_price_matches(self.quote,self.market))
        v=self.valuation();self.assertTrue(v["available"]);self.assertTrue(v["pe"]["available"])
        self.assertIn("mẫu lịch sử",v["price_warning"])

    def test_stale_missing_or_mismatched_latest_quote_still_blocks(self):
        for change in ["missing","mismatch","stale","nan","zero"]:
            p=deepcopy(self.payload)
            if change=="missing":p["data_day"].pop()
            elif change=="stale":p["data_day"][-1]["t"]="2026-10-07"
            else:p["data_day"][-1]["c"]={"mismatch":19000,"nan":float("nan"),"zero":0}[change]
            q=compare_prices(self.rows,p,NOW)
            self.assertFalse(latest_price_matches(q,self.market),change)
            self.assertFalse(self.valuation(q)["available"],change)

    def test_flags_alone_and_changed_market_price_are_not_evidence(self):
        self.assertFalse(self.valuation({"status":"matched","latest_match":True})["available"])
        self.assertFalse(self.valuation(m={**self.market,"latest_close_vnd":21000})["available"])
        self.assertFalse(self.valuation(m={**self.market,"latest_date":"2026-10-07"})["available"])

    def test_threshold_not_relaxed_for_latest_quote(self):
        p=deepcopy(self.payload);p["data_day"][-1]["c"]=19990
        self.assertTrue(self.valuation(compare_prices(self.rows,p,NOW))["available"])
        p["data_day"][-1]["c"]=19970
        self.assertFalse(self.valuation(compare_prices(self.rows,p,NOW))["available"])

    def test_history_based_statistics_suppressed_but_closing_chart_kept(self):
        for key in ["ma20_vnd","ma50_vnd","return_pct","max_drawdown_pct","annualized_volatility_pct"]:
            self.assertIsNone(self.market[key])
        self.assertEqual(self.market["chart_prices"],[r["close"] for r in self.rows])
        self.assertEqual(self.market["latest_close_vnd"],20000)
        p=deepcopy(self.payload);p["data_day"][0]["c"]=self.rows[0]["close"]
        m=analyze_market(self.rows,compare_prices(self.rows,p,NOW))
        self.assertIsNotNone(m["ma20_vnd"]);self.assertIsNotNone(m["return_pct"])

    def test_conclusion_distinguishes_history_risk_from_valuation_block(self):
        c=build_conclusion(financial(),self.market,self.valuation(),self.quote)
        self.assertTrue(any("Mẫu giá lịch sử" in s for s in c["risks"]))
        self.assertFalse(any("chưa dùng để đối chiếu định giá" in s for s in c["risks"]))
        self.assertFalse(any("MA20" in s for s in c["risks"]+c["opportunities"]))

    def test_pdf_displays_separate_latest_and_history_status(self):
        import pymupdf
        r=result(["overview","market","valuation"]);r.update(market=self.market,price_rows=self.rows,financial=financial(),valuation=self.valuation())
        r["quality"]["price_check"]=self.quote
        with TemporaryDirectory() as d:
            path=generate_report(r,Path(d)/"scope.pdf")
            with pymupdf.open(path) as doc:text="\n".join(p.get_text() for p in doc)
        self.assertIn("Đã khớp đúng ngày",text);self.assertIn("Khớp 19/20 phiên",text)
        self.assertIn("mẫu lịch sử chưa khớp đầy đủ",text)


if __name__=="__main__":unittest.main()
