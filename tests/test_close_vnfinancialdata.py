"""Close/Adj Close separation and defensive financial dataset integration."""
from datetime import date
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
import unittest
from unittest.mock import patch

import pandas as pd

from src.analysis.market import analyze_market
from src.data.financial_status import financial_status
from src.data.providers import DataSourceError
from src.data.vnfinancialdata_provider import (collect_vnfinancialdata, compare_statements,
                                              load_statement, mapped_records, validate_frame)

AS_OF=date(2026,10,11)


def frame(statement="balance_sheet",name="TỔNG TÀI SẢN",value=100,code="assets"):
    return pd.DataFrame([dict(ticker="SHS",year=2025,exchange="HNX",statement=statement,
                             item_code=code,item_name=name,value=value,source_file="source.xlsx",source_sheet="sheet")])


def dictionary(f,unit="VND"):
    return f[["statement","item_code","item_name"]].drop_duplicates().assign(unit=unit)


def config(root,d):
    raw=d.to_csv(index=False).encode()
    cfg={"package_version":"0.1.2","repository":"example/data","revision":"v1.0.0",
         "commit":"a"*40,"available_at":"2026-08-17T14:43:52Z","schema_version":"1.0",
         "dictionary_sha256":hashlib.sha256(raw).hexdigest(),"files":{}}
    (root/"config").mkdir();(root/"config/vnfinancialdata.json").write_text(json.dumps(cfg))
    return cfg,raw


class CloseBasisTests(unittest.TestCase):
    def test_split_does_not_replace_close_chart_with_adjusted_history(self):
        rows=[dict(close=c,adjusted_close=a,date=f"2026-10-0{i+1}",volume=1) for i,(c,a) in enumerate([(100,50),(50,50),(60,60)])]
        m=analyze_market(rows,{"status":"matched"})
        self.assertEqual(m["chart_prices"],[100,50,60]);self.assertEqual(m["latest_close_vnd"],60)
        self.assertAlmostEqual(m["return_pct"],20);self.assertEqual(m["max_drawdown_pct"],0)
        self.assertEqual(m["statistics_basis"],"provider_adjusted_close")
        self.assertFalse(m["adjustment_verified"]);self.assertIn("đóng cửa",m["series_basis"])

    def test_moving_average_uses_close_even_with_adjusted_history(self):
        rows=[dict(close=100+i,adjusted_close=(100+i)/2,date="2026-10-09",volume=1) for i in range(50)]
        m=analyze_market(rows,{"status":"matched"})
        self.assertEqual(m["ma20_vnd"],sum(range(130,150))/20)
        self.assertEqual(m["ma50_vnd"],sum(range(100,150))/50)
        self.assertEqual(m["chart_prices"],list(range(100,150)))

    def test_missing_or_unmatched_history_keeps_close_and_correct_basis(self):
        rows=[dict(close=100,adjusted_close=50,date="2026-10-09",volume=1)]
        m=analyze_market(rows,{"status":"unverified"})
        self.assertEqual(m["chart_prices"],[100]);self.assertIsNone(m["return_pct"])
        self.assertEqual(m["statistics_basis"],"source_close");self.assertNotIn("giá điều chỉnh",m["return_label"])
        rows[0]["adjusted_close"]=True
        self.assertFalse(analyze_market(rows)["adjusted_series_available"])


class FinancialDatasetTests(unittest.TestCase):
    def test_actual_dictionary_unit_and_metadata_are_preserved(self):
        f=frame();records,issues=mapped_records(f,dictionary(f),"balance","securities",AS_OF,"VNF")
        self.assertFalse(issues);field=records[0]["fields"]["assets"]
        self.assertEqual(field["value"],100);self.assertEqual(field["unit_multiplier"],1)
        self.assertEqual(field["source_field"],"assets");self.assertEqual(field["source_file"],"source.xlsx")
        self.assertEqual(records[0]["scope"],"unknown");self.assertIsNone(field["published_at"])

    def test_wrong_units_or_code_name_mismatch_do_not_enter_mapped_values(self):
        f=frame()
        for d in [dictionary(f,"unknown"),dictionary(f).assign(item_name="OTHER")]:
            records,issues=mapped_records(f,d,"balance","securities",AS_OF,"VNF")
            self.assertFalse(records);self.assertTrue(issues)

    def test_statement_specific_profit_names_prevent_cross_sector_mapping(self):
        corporate=frame("income_statement","Lãi/(lỗ) thuần sau thuế",0,"ordinary")
        securities=frame("income_statement","Lợi nhuận kế toán sau thuế",123,"securities")
        f=pd.concat([corporate,securities],ignore_index=True)
        records,_=mapped_records(f,dictionary(f),"income","securities",AS_OF,"VNF")
        self.assertEqual(records[0]["fields"]["net_profit"]["value"],123)
        records,_=mapped_records(f,dictionary(f),"income","nonfinancial",AS_OF,"VNF")
        self.assertEqual(records[0]["fields"]["net_profit"]["value"],0)

    def test_conflicting_aliases_and_future_year_are_not_silently_merged(self):
        f=pd.concat([frame(),frame(name="TỔNG CỘNG TÀI SẢN",value=200,code="total")],ignore_index=True)
        records,issues=mapped_records(f,dictionary(f),"balance","securities",AS_OF,"VNF")
        self.assertFalse(records);self.assertTrue(issues)
        f=frame();f["year"]=2026
        self.assertFalse(mapped_records(f,dictionary(f),"balance","securities",AS_OF,"VNF")[0])

    def test_duplicate_keys_wrong_identity_schema_and_year_fail_validation(self):
        for bad in [pd.concat([frame(),frame()]),frame().assign(ticker="VNZ"),frame().drop(columns="value"),frame().assign(year=2025.5),frame().assign(exchange="UPCOM")]:
            with self.assertRaises(DataSourceError):validate_frame(bad,"SHS","HNX","balance_sheet")

    def test_matching_values_never_certify_scope_or_publication(self):
        records,_=mapped_records(frame(),dictionary(frame()),"balance","securities",AS_OF,"VNF")
        financial={"periods":[{"year":2025,"fields":{"assets":{"value":100,"unit":"VND","source_id":"PDF"}}}]}
        checks=compare_statements(records,financial)
        self.assertTrue(checks[0]["match"]);self.assertFalse(checks[0]["scope_certified"])
        self.assertFalse(checks[0]["publication_certified"])
        financial["periods"][0]["fields"]["assets"]["value"]=200
        self.assertFalse(compare_statements(records,financial)[0]["match"])

    def test_upcom_and_future_dataset_never_attempt_downloads(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);config(root,dictionary(frame()))
            with patch("src.data.vnfinancialdata_provider.load_statement",side_effect=AssertionError("network")),patch("src.data.vnfinancialdata_provider.cached_file",side_effect=AssertionError("network")):
                r=collect_vnfinancialdata("F88",AS_OF,{"exchange":"UPCOM"},{},root,"test")
                self.assertEqual(r["status"],"unsupported_exchange")
                r=collect_vnfinancialdata("SHS",date(2026,1,1),{"exchange":"HNX"},{},root,"test")
                self.assertEqual(r["status"],"future_snapshot")

    def test_expense_sign_difference_is_explained_without_changing_raw_values(self):
        f=frame("income_statement","Trong đó: Chi phí lãi vay",-100,"interest")
        records,_=mapped_records(f,dictionary(f),"income","nonfinancial",AS_OF,"VNF")
        financial={"periods":[{"year":2025,"fields":{"interest_expense":{"value":100,"unit":"VND"}}}]}
        check=compare_statements(records,financial)[0]
        self.assertEqual(check["status"],"different_sign_convention");self.assertFalse(check["match"])
        self.assertEqual(check["reference_vnd"],-100);self.assertEqual(check["primary_vnd"],100)

    def test_full_csv_partial_failure_and_no_primary_promotion(self):
        f=frame();f.loc[1]=dict(f.iloc[0],item_code="not_mapped",item_name="Other",value=42)
        f.loc[2]=dict(f.iloc[0],year=2026)
        with TemporaryDirectory() as folder:
            root=Path(folder);cfg,raw=config(root,dictionary(f))
            with patch("src.data.vnfinancialdata_provider.cached_file",return_value=(raw,{"retrieved_at":"2026-10-11"})),patch("src.data.vnfinancialdata_provider.load_statement",side_effect=[(f,{"sha256":"abc"}),DataSourceError("offline"),DataSourceError("offline")]):
                r=collect_vnfinancialdata("SHS",AS_OF,{"exchange":"HNX"},{"industry_group":"securities"},root,"test")
            self.assertTrue(r["available"]);self.assertEqual(r["status"],"partial_reference")
            self.assertFalse(r["used_in_primary_analysis"])
            self.assertEqual(len(pd.read_csv(root/r["csv"])),2)
            self.assertEqual(r["years"],[2025])
            self.assertEqual(len(r["errors"]),2)

    def test_dictionary_tamper_rejected_before_sdk(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);config(root,dictionary(frame()))
            with patch("src.data.vnfinancialdata_provider.cached_file",return_value=(b"corrupt",{})),patch("src.data.vnfinancialdata_provider.load_statement") as sdk:
                r=collect_vnfinancialdata("SHS",AS_OF,{"exchange":"HNX"},{},root,"test")
            sdk.assert_not_called();self.assertFalse(r["available"]);self.assertTrue(r["errors"])

    def test_sdk_boundary_pins_hash_and_restores_loader_on_error(self):
        sdk=ModuleType("vnfinancialdata");loader=ModuleType("vnfinancialdata.loader");hub=ModuleType("huggingface_hub")
        loader.DATASET_REVISION="original";original=lambda **kwargs:None;loader.hf_hub_download=original
        with TemporaryDirectory() as folder:
            root=Path(folder);p=root/"data.parquet";p.write_bytes(b"checked")
            cfg={"package_version":"0.1.2","repository":"example","commit":"a"*40,"files":{"balance_sheet/HNX":{"size":7,"sha256":hashlib.sha256(b"checked").hexdigest()}}}
            hub.hf_hub_download=lambda **kwargs:str(p)
            def load(**kwargs):
                loader.hf_hub_download(repo_id="example",repo_type="dataset",filename="data/balance_sheet/HNX.parquet",revision=loader.DATASET_REVISION)
                return frame()
            sdk.load=load
            with patch.dict("sys.modules",{"vnfinancialdata":sdk,"vnfinancialdata.loader":loader,"huggingface_hub":hub}),patch("src.data.vnfinancialdata_provider.version",return_value="0.1.2"):
                result,snapshot=load_statement("SHS","HNX","balance_sheet",AS_OF,root,cfg)
                self.assertEqual(snapshot["sha256"],cfg["files"]["balance_sheet/HNX"]["sha256"])
                p.write_bytes(b"corrupt")
                with self.assertRaises(Exception):load_statement("SHS","HNX","balance_sheet",AS_OF,root,cfg)
            self.assertEqual(loader.DATASET_REVISION,"original");self.assertIs(loader.hf_hub_download,original)

    def test_financial_diagnostics_distinguish_period_metadata_and_model_limits(self):
        result={"request":{"as_of":"2026-10-11"},"financial":{"periods":[{"year":2024,"scope":"consolidated"}],"metrics":[]},
                "quality":{"warnings":["KBS_balance: loại kỳ 2025, metadata 202501–202612 không phải 12 tháng"]},
                "valuation":{"pe":{"available":False,"reason":"Lợi nhuận âm"}}}
        d=financial_status(result)
        self.assertEqual(d["latest_valid_year"],2024);self.assertEqual(d["rejected_kbs_years"],[2025])
        self.assertFalse(d["missing_fields"]);self.assertEqual(d["blocked_methods"][0]["reason"],"Lợi nhuận âm")


if __name__=="__main__":unittest.main()
