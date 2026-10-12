"""SDK unit contract, fallback execution and independent upstream selection."""
from contextlib import ExitStack
from datetime import date, datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import pandas as pd

from src.data.acquisition import acquire
from src.data.providers import DataSourceError, VN_TIME, price_source_family
from src.data.research import collect_research
from src.data.vnstock_provider import fetch_vnstock_kbs_prices, fetch_vnstock_vci_prices, load_quote, normalize_history

AS_OF = date(2026, 10, 11)
START = date(2026, 10, 1)


def history(source="KBS", symbol="SHS"):
    frame = pd.DataFrame([{"time": "2026-10-09", "open": 11.8, "high": 12,
                           "low": 11.5, "close": 11.7, "volume": 1234},
                          {"time": "2026-10-11", "open": 11.8, "high": 12,
                           "low": 11.5, "close": 11.7, "volume": 1234}])
    frame.attrs.update(symbol=symbol, source=source)
    return frame


def response(source="KBS"):
    return {"rows": normalize_history(history(source), "SHS", source, START, date(2026,10,10)),
            "raw": b'{}', "url": "https://example.test/price", "cutoff": "2026-10-10",
            "meta": {}, "retrieved_at": "2026-10-11T10:00:00+07:00"}


class VnstockProviderTests(unittest.TestCase):
    def setUp(self):
        # The fixture's latest completed day must not change with the host date.
        clock = patch("src.data.providers.datetime", wraps=datetime)
        clock.start().now.return_value = datetime(2026, 10, 11, 10, tzinfo=VN_TIME)
        self.addCleanup(clock.stop)

    def test_unit_conversion_volume_and_completed_cutoff(self):
        frame=history();frame.loc[0,"time"]="2026-10-08T18:00:00Z"
        rows=normalize_history(frame,"SHS","KBS",START,date(2026,10,10))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]["date"],"2026-10-09")
        self.assertEqual(rows[0]["close"],11700);self.assertEqual(rows[0]["volume"],1234)
        self.assertIsNone(rows[0]["adjusted_close"])
        self.assertEqual(price_source_family(rows[0]["price_provider"]),"KBS")

    def test_identity_schema_nan_fractional_volume_and_ohlc_rejected(self):
        for defect in ["symbol","source","schema","date","nan","volume","range","duplicate","empty"]:
            with self.subTest(defect=defect):
                frame=history()
                if defect in {"symbol","source"}:frame.attrs[defect]="WRONG"
                elif defect=="schema":frame=frame.drop(columns="close")
                elif defect=="date":frame.loc[0,"time"]=None
                elif defect=="nan":frame.loc[0,"close"]=float("nan")
                elif defect=="volume":frame["volume"]=1.5
                elif defect=="range":frame.loc[0,"high"]=10
                elif defect=="duplicate":frame.loc[1,"time"]=frame.loc[0,"time"]
                elif defect=="empty":frame=frame.iloc[:0]
                with self.assertRaises((DataSourceError,ValueError)):
                    normalize_history(frame,"SHS","KBS",START,date(2026,10,10))

    def test_sdk_request_and_auditable_library_snapshot(self):
        for source,fetch in [("KBS",fetch_vnstock_kbs_prices),("VCI",fetch_vnstock_vci_prices)]:
            with self.subTest(source=source):
                quote=Mock(symbol="SHS",asset_type="stock");quote.history.return_value=history(source)
                with patch("src.data.vnstock_provider.load_quote",return_value=Mock(return_value=quote)):
                    result=fetch("shs",START,AS_OF)
                expected_end="2026-10-12" if source=="KBS" else "2026-10-10"
                self.assertEqual(quote.history.call_args.kwargs["end"],expected_end)
                self.assertEqual(result["rows"][-1]["date"],"2026-10-09")
                snapshot=json.loads(result["raw"])
                self.assertEqual(snapshot["history"][0]["close"],11.7)
                self.assertEqual(snapshot["price_multiplier"],1000)
                self.assertEqual(snapshot["snapshot_kind"],"vnstock_library_output_not_raw_http")

    def test_unsupported_version_missing_package_and_sdk_exit_are_safe_errors(self):
        with patch("src.data.vnstock_provider.version",return_value="99.0"):
            with self.assertRaises(DataSourceError):load_quote()
        with patch("src.data.vnstock_provider.version",side_effect=ImportError("missing")):
            with self.assertRaises(DataSourceError):load_quote()
        for error in [SystemExit(1),RuntimeError("rate limit"),ImportError("dependency")]:
            with patch("src.data.vnstock_provider.load_quote",side_effect=error):
                with self.assertRaises(DataSourceError):fetch_vnstock_kbs_prices("SHS",START,AS_OF)

    def test_fourth_and_fifth_connectors_execute_after_http_failure(self):
        for source in ["KBS","VCI"]:
            with self.subTest(source=source),TemporaryDirectory() as folder,ExitStack() as stack:
                for name in ["fetch_daily_prices","fetch_kbs_prices","fetch_vietcap_prices"]:
                    stack.enter_context(patch("src.data.acquisition."+name,side_effect=DataSourceError("offline")))
                stack.enter_context(patch("src.data.acquisition.fetch_vnstock_kbs_prices",return_value=response("KBS")) if source=="KBS" else patch("src.data.acquisition.fetch_vnstock_kbs_prices",side_effect=DataSourceError("invalid SDK data")))
                vci=stack.enter_context(patch("src.data.acquisition.fetch_vnstock_vci_prices",return_value=response("VCI")))
                result=acquire("SHS",START,AS_OF,Path(folder))
                self.assertEqual(result["prices"]["provider"],"Vnstock-"+source)
                self.assertFalse(result["errors"])
                self.assertEqual(len(result["price_attempts"]),4 if source=="KBS" else 5)
                if source=="KBS":vci.assert_not_called()

    def test_sdk_primary_never_cross_checks_its_own_upstream(self):
        for source in ["KBS","VCI"]:
            with self.subTest(source=source),TemporaryDirectory() as folder,ExitStack() as stack:
                primary=response(source)["rows"]
                stack.enter_context(patch("src.data.research.download",side_effect=DataSourceError("offline")))
                stack.enter_context(patch("src.data.research.fetch_daily_prices",side_effect=DataSourceError("missing")))
                direct_kbs=stack.enter_context(patch("src.data.research.fetch_kbs_prices",return_value=response("KBS")))
                direct_vci=stack.enter_context(patch("src.data.research.fetch_vietcap_prices",return_value=response("VCI")))
                sdk_kbs=stack.enter_context(patch("src.data.research.fetch_vnstock_kbs_prices",side_effect=AssertionError("same upstream")))
                sdk_vci=stack.enter_context(patch("src.data.research.fetch_vnstock_vci_prices",side_effect=AssertionError("same upstream")))
                result=collect_research("SHS",AS_OF,primary,Path(folder),"fixture")
                check=result["quote_check"]
                self.assertEqual(check["status"],"matched")
                self.assertNotEqual(check["primary_upstream"],check["reference_upstream"])
                sdk_kbs.assert_not_called();sdk_vci.assert_not_called()
                if source=="KBS":direct_kbs.assert_not_called()
                else:direct_vci.assert_not_called()

    def test_sdk_reference_fallback_uses_other_upstream(self):
        with TemporaryDirectory() as folder,ExitStack() as stack:
            primary=response("KBS")["rows"]
            stack.enter_context(patch("src.data.research.download",side_effect=DataSourceError("offline")))
            for name in ["fetch_daily_prices","fetch_vietcap_prices"]:
                stack.enter_context(patch("src.data.research."+name,side_effect=DataSourceError("offline")))
            same=stack.enter_context(patch("src.data.research.fetch_vnstock_kbs_prices",side_effect=AssertionError("same upstream")))
            stack.enter_context(patch("src.data.research.fetch_vnstock_vci_prices",return_value=response("VCI")))
            check=collect_research("SHS",AS_OF,primary,Path(folder),"fixture")["quote_check"]
            same.assert_not_called();self.assertEqual(check["reference_provider"],"Vnstock-VCI")
            self.assertEqual(check["reference_upstream"],"Vietcap");self.assertEqual(check["status"],"matched")


if __name__ == "__main__":
    unittest.main()
