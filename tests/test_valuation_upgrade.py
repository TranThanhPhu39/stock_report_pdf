"""Regression tests for the ACB failures and ZIP valuation integration."""
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch
from src.data.acquisition import acquire
from src.data.providers import DataSourceError
from src.data.research import compare_prices
from src.data.valuation_peers import collect_valuation_peers
from src.data.normalize import parse_annual_financials
from src.analysis.financial import analyze_financials
from src.analysis.conclusion import build_conclusion
from src.analysis.valuation import analyze_valuation
from src.analysis.ai_commentary import generate_commentary, validate_commentary, evidence_bundle, resolve_key
from src.reporting.pdf_exporter import generate_report
from test_analysis_reporting import period,payload

NOW=date(2026,10,9)


def financial(bank=False):
    records=[period(2025,20e9,120e9),period(2024,25e9,100e9)]
    for p in records:
        p["business_type"]=3 if bank else 1
        for k,v in {"parent_profit":p["fields"]["net_profit"]["value"],"cash":5e9,"capex_cash":-3e9,"interest_paid":-1e9,"short_debt":10e9,"long_debt":10e9}.items():p["fields"][k]={"value":v,"source_id":"fixture","period":str(p["year"])}
        if bank:
            p["fields"].pop("revenue")
            for k,v in {"net_interest_income":30e9,"operating_cost":10e9,"pre_provision_profit":20e9,"customer_loans":150e9,"customer_deposits":200e9}.items():p["fields"][k]={"value":v,"source_id":"fixture","period":str(p["year"])}
    return analyze_financials(records)


def company():return {"ticker":"ACB","snapshot_at":NOW.isoformat(),"outstanding_shares":10e6,"source_id":"fixture"}
def market():return {"latest_close_vnd":20000,"latest_date":"2026-10-08"}
def value(f=None,**kw):return analyze_valuation(f or financial(),market(),company(),{"status":"matched"},NOW,**kw)


def result(sections=None):
    return {"request":{"ticker":"ACB","start":"2016-03-20","as_of":NOW.isoformat(),"mode":"summary","sections":sections or ["overview","macro","industry","financial","valuation"],"use_ai":True},
            "acquisition":{"run_id":"fixture","prices":None},"company":company(),"financial":financial(True),"market":None,"price_rows":[],"interim":None,
            "valuation":{"available":False,"reason":"Thiếu giá."},"news":[],"conclusion":{"summary":"Phân tích bằng chứng","opportunities":[],"risks":[],"integrated_thesis":["Vĩ mô → ngành: kiểm tra","Ngành → doanh nghiệp: kiểm tra"]},
            "macro":{"indicators":[{"key":"cpi_ytd","label":"CPI","value":4.52,"unit":"%","period":"9/2026","published_at":"2026-10-03","source_id":"fixture"}],"assessment":"Có dữ liệu có kỳ."},
            "industry":{"available":True,"name":"Ngân hàng","code":"8355","taxonomy":"ICB","classification_snapshot":"2026-10-09","members":["ACB"],"selection":"Mẫu đồng kỳ","eligible_candidates":0,"peers":[],"comparisons":[{"label":"ROE","key":"roe","company_value":18.,"sample_median":17.,"sample_size":2,"period_end":"2025-12-31","unit":"%","difference":1.}],"drivers":[],"structural_risks":[],"sources":[{"source_id":"fixture"}]},
            "quality":{"warnings":[],"price_check":{"status":"unverified"},"financial_check":{"status":"not_independently_checked","checks":[]}},"errors":[],"status":"partial","sources":[{"source_id":"fixture","url_or_file":"https://example.test/report","retrieved_at":"2026-10-09","page_or_table":"Table 1"}]}


class DataRegressionTests(unittest.TestCase):
    def test_bad_yahoo_range_falls_back_whole_series_and_logs_original(self):
        bad={"ticker":"ACB","date":"2025-06-04","open":18716.,"high":792.,"low":18716.,"close":18805.,"volume":1}
        good={**bad,"high":18900.,"open":18800.,"close":18850.}
        def response(row):return {"rows":[row],"raw":b'{}',"url":"https://example.test/price","retrieved_at":"2026-10-09","meta":{},"cutoff":"2026-10-08"}
        with TemporaryDirectory() as d,patch("src.data.acquisition.fetch_daily_prices",return_value=response(bad)),patch("src.data.acquisition.fetch_kbs_prices",return_value=response(good)):
            out=acquire("ACB",date(2016,3,20),NOW,Path(d))
            self.assertEqual(out["prices"]["provider"],"KBS");self.assertEqual(out["prices"]["row_count"],1)
            self.assertFalse(out["price_attempts"][0]["validation"]["valid"])
            self.assertTrue((Path(d)/out["price_attempts"][0]["raw_file"]).exists())
            self.assertFalse(out["errors"]);self.assertGreater(out["prices"]["coverage"]["start_gap_days"],0)
    def test_all_providers_fail_keeps_prices_unavailable(self):
        with TemporaryDirectory() as d,patch("src.data.acquisition.fetch_daily_prices",side_effect=DataSourceError("offline")),patch("src.data.acquisition.fetch_kbs_prices",side_effect=DataSourceError("offline")):
            out=acquire("ACB",date(2025,1,1),NOW,Path(d));self.assertIsNone(out["prices"]);self.assertEqual(len(out["price_attempts"]),2)
    def test_bank_cfo_alias_is_not_pre_working_capital_subtotal(self):
        p=payload();p["Content"]={"cashflow":[{"ReportNormID":4110,"Name":"CFO ngân hàng","Value1":28160074000},{"ReportNormID":4109,"Name":"Trước vốn lưu động","Value1":18097000000}]}
        parsed=parse_annual_financials(p,"cashflow",NOW,"fixture");self.assertEqual(parsed[0]["fields"]["cfo"]["value"],28160074000000)
    def test_bank_profit_decline_does_not_require_revenue(self):
        f=financial(True);c=build_conclusion(f,None,{}, {"status":"matched"})
        self.assertTrue(any("giảm 20.00%" in r for r in c["risks"]))
        self.assertNotIn("revenue",{m["key"] for m in f["metrics"]})
    def test_quote_check_requires_full_recent_sample(self):
        rows=[{"date":f"2026-10-0{i}","close":10} for i in range(1,9)]
        q=compare_prices(rows,{"data_day":[{"t":"2026-10-08","c":10}]},NOW)
        self.assertEqual(q["status"],"unverified")


class ValuationUpgradeTests(unittest.TestCase):
    def test_all_methods_with_valid_inputs(self):
        v=value(industry_benchmark={"available":True,"median_pb":1.3,"sector_name":"fixture","peers":[]})
        for k in ["gordon","industry","pe","dcf","weighted_average"]:self.assertTrue(v[k]["available"],k)
        self.assertEqual(len(v["pb_methods"]),3)
        self.assertAlmostEqual(sum(c["weight_pct"] for c in v["weighted_average"]["components"]),100)
        self.assertAlmostEqual(v["dcf"]["cash_flow_base"],24e9+.8e9-3e9)
        self.assertAlmostEqual(v["dcf"]["equity_value"],v["dcf"]["enterprise_value"]+5e9-20e9)
    def test_nci_null_blocks_pb_but_not_independent_parent_pe(self):
        f=financial(True);f["periods"][0]["fields"].pop("non_controlling_equity")
        v=value(f);self.assertTrue(v["pe"]["available"]);self.assertFalse(v["scenarios"]);self.assertIsNone(v["book_value_per_share"])
        self.assertTrue(any("NCI" in r for r in v["blocked_reasons"]))
        self.assertFalse(v["weighted_average"]["available"])
    def test_bank_never_receives_nonfinancial_dcf(self):self.assertFalse(value(financial(True))["dcf"]["available"])
    def test_missing_cfo_never_replaced_by_profit(self):
        f=financial();f["periods"][0]["fields"].pop("cfo");self.assertFalse(value(f)["dcf"]["available"])
    def test_gordon_does_not_clip_or_invent_roe(self):
        v=value(discount_rate=.04,perpetual_growth=.035);self.assertGreater(v["gordon"]["justified_pb"],5)
        self.assertFalse(value(discount_rate=.035)["gordon"]["available"])
    def test_unvalidated_industry_and_single_method_not_composite(self):
        self.assertFalse(value()["industry"]["available"])
        self.assertFalse(value(method_weights={"pb":1,"pe":0,"dcf":0})["weighted_average"]["available"])
    def test_nonfinite_assumptions_and_zero_weights_rejected(self):
        for kw in [dict(target_pb=float("nan")),dict(wacc=float("inf")),dict(method_weights={"pb":0,"pe":0,"dcf":0})]:
            with self.assertRaises(ValueError):value(**kw)


class PeerValuationTests(unittest.TestCase):
    def industry(self):
        return {"name":"Fixture", "period_end":"2025-12-31", "scope":"consolidated",
                "peers":[{"ticker":t,"financial":financial()} for t in ["AAA","BBB"]]}

    def test_wrong_period_excluded_before_download(self):
        industry=self.industry();industry["period_end"]="2024-12-31"
        with TemporaryDirectory() as d,patch("src.data.valuation_peers.datetime") as clock,patch("src.data.valuation_peers.download") as download:
            clock.now.return_value=datetime(2026,10,9)
            out=collect_valuation_peers(industry,NOW,"2026-10-08",Path(d),"fixture")
            self.assertFalse(out["available"]);self.assertEqual(len(out["excluded"]),2);download.assert_not_called()

    def test_peer_median_requires_two_known_parent_capitals_and_matched_quotes(self):
        industry=self.industry()
        def profile(url,**kw):return json.dumps({"SB":url.split("/")[-1].split("?")[0],"KLCPLH":10e6}).encode()
        quote={"rows":[{"date":"2026-10-08","close":20000}],"raw":b'{}',"url":"https://example.test/quote","retrieved_at":NOW.isoformat()}
        with TemporaryDirectory() as d,patch("src.data.valuation_peers.datetime") as clock,patch("src.data.valuation_peers.download",side_effect=profile),patch("src.data.valuation_peers.fetch_daily_prices",return_value=quote),patch("src.data.valuation_peers.fetch_kbs_prices",return_value=quote):
            clock.now.return_value=datetime(2026,10,9)
            out=collect_valuation_peers(industry,NOW,"2026-10-08",Path(d),"fixture")
            self.assertTrue(out["available"]);self.assertEqual(out["sample_size"],2);self.assertEqual(len(out["sources"]),6)
            industry["peers"][0]["financial"]["periods"][0]["fields"]["non_controlling_equity"]["value"]=None
            self.assertFalse(collect_valuation_peers(industry,NOW,"2026-10-08",Path(d),"fixture")["available"])
            wrong={**quote,"rows":[{"date":"2026-10-08","close":25000}]}
            with patch("src.data.valuation_peers.fetch_kbs_prices",return_value=wrong):
                out=collect_valuation_peers(industry,NOW,"2026-10-08",Path(d),"fixture")
                self.assertFalse(out["available"]);self.assertEqual(len(out["excluded"]),2)


class AiRegressionTests(unittest.TestCase):
    def valid(self,r):
        b=evidence_bundle(r);m=next(e for e in b["evidence"] if e["kind"]=="macro");f=next(e for e in b["evidence"] if e["kind"]=="company");i=next(e for e in b["evidence"] if e["kind"]=="industry")
        def item(ids):return {"text":"Cần kiểm tra tác động tới chi phí vốn và dự phòng.","evidence_ids":ids,"source_ids":["fixture"]}
        return {"macro":[item([m["id"]])],"industry":[item([i["id"]])],"company_impact":[item([m["id"],f["id"]])]}
    def test_missing_key_and_missing_industry_skip_api(self):
        r=result();called=[]
        with patch.dict("os.environ",{},clear=True):self.assertEqual(generate_commentary(r,caller=lambda *a:called.append(a))["status"],"missing_key")
        r["industry"]["available"]=False;self.assertEqual(generate_commentary(r,key="fake",caller=lambda *a:called.append(a))["status"],"missing_industry");self.assertFalse(called)
    def test_api_error_and_invalid_json_preserve_fallback(self):
        for raw in ["{bad",'[]']:
            self.assertEqual(generate_commentary(result(),key="fake",caller=lambda *a:raw)["status"],"failed")
        def fail(*args):raise RuntimeError("sensitive fake key")
        out=generate_commentary(result(),key="fake",caller=fail);self.assertNotIn("sensitive",out["reason"])
    def test_payload_contains_asof_sector_period_values_and_sources(self):
        r=result();seen=[]
        out=generate_commentary(r,key="fake",caller=lambda b,*a:(seen.append(b) or self.valid(r)))
        self.assertTrue(out["available"]);self.assertEqual(seen[0]["as_of"],NOW.isoformat());self.assertEqual(seen[0]["industry"]["code"],"8355");self.assertTrue(seen[0]["sources"])
    def test_unknown_source_or_unvalidated_number_rejected(self):
        r=result()
        for key,v in [("text","GDP tăng 99%"),("source_ids",["not_in_bundle"]),("evidence_ids",["missing"])]:
            data=self.valid(r);data["macro"][0][key]=v
            with self.assertRaises(ValueError):validate_commentary(data,evidence_bundle(r))
    def test_secrets_root_nested_and_env(self):
        self.assertEqual(resolve_key(secrets={"GEMINI_API_KEY":"root"}),"root")
        self.assertEqual(resolve_key(secrets={"gemini":{"api_key":"nested"}}),"nested")
        with patch.dict("os.environ",{"GEMINI_API_KEY":"env"}):self.assertEqual(resolve_key(),"env")
    def test_pdf_macro_industry_selection_and_ai_visibility(self):
        import pymupdf
        for sections in [["overview","macro","industry"],["financial"]]:
            r=result(sections);r["ai_commentary"]=generate_commentary(r,key="fake",caller=lambda *a:self.valid(r))
            with TemporaryDirectory() as d:
                path=generate_report(r,Path(d)/"selected.pdf")
                with pymupdf.open(path) as doc:text="\n".join(p.get_text() for p in doc)
            for heading in ["Tổng quan vĩ mô","Phân tích ngành"]:self.assertEqual(heading in text,"macro" in sections)
            self.assertEqual("Nhận xét hỗ trợ AI" in text,"macro" in sections)
            self.assertNotIn("2016-03-20 đến",text)

    def test_pdf_chart_preserves_aspect_ratio_and_stays_inside_column(self):
        import pymupdf
        from PIL import Image
        with TemporaryDirectory() as d:
            chart=Path(d)/"wide.png"
            Image.new("RGB",(1300,480),"#207a78").save(chart)
            with patch("src.reporting.pdf_exporter.research_chart",return_value=chart):
                path=generate_report(result(["industry"]),Path(d)/"bounded.pdf")
            with pymupdf.open(path) as doc:
                images=[item for page in doc for item in page.get_image_info()]
                self.assertTrue(images)
                for item in images:
                    x0,y0,x1,y1=item["bbox"]
                    self.assertAlmostEqual((x1-x0)/(y1-y0),1300/480,places=5)
                    self.assertLessEqual(x1,(18+115)*72/25.4+1)


if __name__=="__main__":unittest.main()
