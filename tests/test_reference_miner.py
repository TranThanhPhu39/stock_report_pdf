"""Reference sources cannot bypass metadata guards or download entire archives."""
from copy import deepcopy
from datetime import date
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch, MagicMock
import zipfile

import pandas as pd

from src.data.providers import DataSourceError
from src.data.reference_miner import cached_file, parse_catalog, parse_parquet, compare_reference, RemoteZip, fetch_report, sha256, collect_reference


def row(**kwargs):
    return {"ticker":"HPG","year":2025,"exchange":"HSX","statement":"income_statement",
            "item_code":"is_doanh_so_thuan","item_name":"Doanh số thuần","value":100.,
            "source_file":"original.xlsx","source_sheet":"income",**kwargs}


class ReferenceTests(unittest.TestCase):
    def test_unknown_metadata_preserved_and_future_year_filtered(self):
        records=parse_parquet(pd.DataFrame([row(),row(year=2026),row(ticker="FPT")]),"HPG","income",date(2026,10,9),"source")
        self.assertEqual(len(records),1)
        self.assertIsNone(records[0]["published_at"])
        self.assertEqual(records[0]["scope"],"unknown")
        self.assertEqual(records[0]["fields"]["revenue"]["unit"],"source_value")

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(DataSourceError):parse_parquet(pd.DataFrame([row(),row()]),"HPG","income",date(2026,10,9),"source")

    def test_missing_and_infinite_values_not_zero(self):
        for value in [None,float("inf"),float("nan")]:
            self.assertEqual(parse_parquet(pd.DataFrame([row(value=value)]),"HPG","income",date(2026,10,9),"s"),[])

    def test_conflicting_equity_aliases_not_selected(self):
        frame=pd.DataFrame([row(statement="balance_sheet",item_code="bs_von_chu_so_huu_4d280b22"),row(statement="balance_sheet",item_code="bs_von_va_cac_quy",value=200)])
        self.assertEqual(parse_parquet(frame,"HPG","balance",date(2026,10,9),"s"),[])

    def test_comparison_does_not_promote_or_change_primary(self):
        records=parse_parquet(pd.DataFrame([row()]),"HPG","income",date(2026,10,9),"s")
        primary={"periods":[{"year":2025,"scope":"consolidated","fields":{"revenue":{"value":99}}}]}
        original=deepcopy(primary)
        checks=compare_reference(records,primary)
        self.assertFalse(checks[0]["match"])
        self.assertFalse(checks[0]["scope_certified"])
        self.assertEqual(primary,original)

    def test_catalog_rejects_future_year_wrong_symbol_and_hash(self):
        header="record_id,ticker_folder,ticker_file,year_full,relative_path,sha256,archive_period,file_size_bytes,status,document_type\n"
        good=f"one,HPG,HPG,2025,HPG/annual.pdf,{'a'*64},2021_2025,100,ok,annual_report\n"
        raw=(header+good+good.replace("2025","2026")+good.replace("HPG,HPG","FPT,HPG")+good.replace("a"*64,"bad")).encode()
        self.assertEqual(len(parse_catalog(raw,"HPG",date(2026,10,9))),1)

    def test_pinned_version_after_asof_not_downloaded(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);(root/"config").mkdir();(root/"config/reference_sources.json").write_text(json.dumps({"commit":"a"*40,"available_at":"2026-10-09T06:43:27Z"}))
            with patch("src.data.reference_miner.download") as network:
                result=collect_reference("HPG",date(2026,10,8),{}, {},root,"test")
                network.assert_not_called()
            self.assertFalse(result["available"])
            self.assertFalse(result["used_in_primary_analysis"])

    def test_cache_checks_hash_and_repairs_corruption(self):
        with TemporaryDirectory() as folder,patch("src.data.reference_miner.download",return_value=b"data") as network:
            path=Path(folder)/"source.parquet"
            _,first=cached_file("https://example.test/pinned",path,"2026-10-09")
            _,second=cached_file("https://example.test/pinned",path,"2026-10-09")
            self.assertEqual(first["retrieved_at"],second["retrieved_at"])
            self.assertEqual(network.call_count,1)
            path.write_bytes(b"corrupt")
            raw,_=cached_file("https://example.test/pinned",path,"2026-10-09")
            self.assertEqual(raw,b"data");self.assertEqual(network.call_count,2)

    def test_server_ignoring_range_never_read(self):
        response=MagicMock();response.status=200;response.__enter__.return_value=response
        with patch("src.data.reference_miner.urlopen",return_value=response):
            with self.assertRaises(DataSourceError):RemoteZip("https://example.test/large.zip")
        response.read.assert_not_called()

    def test_offset_mismatch_rejected(self):
        with patch.object(RemoteZip,"_request",return_value=(b"x"*65536,"bytes 100000-165535/165536")):
            reader=RemoteZip("https://example.test/archive")
        reader.seek(0)
        with patch.object(reader,"_request",return_value=(b"bad","bytes 1-3/165536")):
            with self.assertRaises(DataSourceError):reader.read(3)

    def test_selective_pdf_validates_checksum_and_cached_copy(self):
        raw=b"%PDF-fixture";stream=io.BytesIO()
        with zipfile.ZipFile(stream,"w") as archive:archive.writestr("root/HPG/annual.pdf",raw)
        report={"ticker_file":"HPG","year":2025,"sha256":sha256(raw),"file_size_bytes":len(raw),"archive_period":"2021_2025","relative_path":"HPG/annual.pdf"}
        with TemporaryDirectory() as folder:
            root=Path(folder)
            with patch("src.data.reference_miner.RemoteZip",return_value=io.BytesIO(stream.getvalue())):
                path=fetch_report(report,root)
            with patch("src.data.reference_miner.RemoteZip") as network:
                self.assertEqual(fetch_report(report,root),path);network.assert_not_called()
            with patch("src.data.reference_miner.RemoteZip",return_value=io.BytesIO(stream.getvalue())):
                with self.assertRaises(DataSourceError):fetch_report({**report,"sha256":"b"*64},root)

    def test_mirror_accepted_only_with_catalog_checksum(self):
        raw=b"%PDF-fixture";report={"ticker_file":"HPG","year":2025,"sha256":sha256(raw),"file_size_bytes":len(raw),"archive_period":"2021_2025","relative_path":"HPG/annual.pdf","file_name":"HPG_25CN_BCTN.pdf"}
        response=MagicMock();response.__enter__.return_value=response;response.read.return_value=raw
        with TemporaryDirectory() as folder,patch("src.data.reference_miner.urlopen",return_value=response),patch("src.data.reference_miner.RemoteZip") as archive:
            path=fetch_report(report,Path(folder));archive.assert_not_called()
            self.assertEqual(path.read_bytes(),raw)
            self.assertEqual(report["retrieval_mode"],"catalog_hash_verified_mirror")
            original_date=report["downloaded_at"]
            fetch_report(report,Path(folder))
            self.assertEqual(report["downloaded_at"],original_date)
            self.assertEqual(report["retrieval_mode"],"local_cache_checked_sha256")

    def test_wrong_mirror_falls_back_without_saving_wrong_pdf(self):
        raw=b"%PDF-right";wrong=b"%PDF-wrong";stream=io.BytesIO()
        with zipfile.ZipFile(stream,"w") as archive:archive.writestr("HPG/annual.pdf",raw)
        report={"ticker_file":"HPG","year":2025,"sha256":sha256(raw),"file_size_bytes":len(raw),"archive_period":"2021_2025","relative_path":"HPG/annual.pdf","file_name":"HPG_25CN_BCTN.pdf"}
        response=MagicMock();response.__enter__.return_value=response;response.read.return_value=wrong
        with TemporaryDirectory() as folder,patch("src.data.reference_miner.urlopen",return_value=response),patch("src.data.reference_miner.RemoteZip",return_value=io.BytesIO(stream.getvalue())):
            path=fetch_report(report,Path(folder))
            self.assertEqual(path.read_bytes(),raw)
            self.assertEqual(report["retrieval_mode"],"selective_zip_download")

    def test_reference_pdf_selection_and_raw_unit_label(self):
        import pymupdf
        from src.reporting.pdf_exporter import generate_report
        result={"request":{"ticker":"HPG","as_of":"2026-10-09","start":"2025-10-09","mode":"summary","sections":["reference"]},
                "acquisition":{"run_id":"fixture"},"company":{"name":"Hòa Phát"},"market":None,"financial":{"metrics":[]},
                "valuation":{"available":False},"conclusion":{"summary":"Nguồn bổ sung","opportunities":[],"risks":[]},
                "quality":{"price_check":{"status":"unverified"},"financial_check":{"status":"not_independently_checked"},"warnings":[]},
                "errors":[],"status":"partial","sources":[],"reference":{"available":True,"records":parse_parquet(pd.DataFrame([row(value=123e9)]),"HPG","income",date(2026,10,9),"s")}}
        with TemporaryDirectory() as folder:
            pdf=generate_report(result,Path(folder)/"reference.pdf")
            with pymupdf.open(pdf) as doc:text="".join(p.get_text() for p in doc)
        self.assertIn("123.00",text);self.assertIn("không tự xác nhận đơn vị tỷ VND",text)
        self.assertNotIn("Giá và giao dịch",text)


if __name__=="__main__":unittest.main()
