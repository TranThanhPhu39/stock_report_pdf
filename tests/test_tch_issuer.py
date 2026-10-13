from copy import deepcopy
from datetime import date
import hashlib,json
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory
from unittest.mock import patch
from src.analysis.financial import analyze_financials
from src.analysis.trailing import trailing_from_interim
from src.data.tch_issuer import snapshot_records,collect_tch_issuer
from src.data.providers import DataSourceError
from src.data.quarterly import parse_quarters

ROOT=Path(__file__).resolve().parents[1]


class TchIssuerTests(unittest.TestCase):
    def fixture(self):
        data=json.loads((ROOT/'config/issuer_snapshots/TCH_2025.json').read_text(encoding='utf-8'))
        content=b'%PDF-fixture'
        data['sha256']=hashlib.sha256(content).hexdigest()
        return data,content

    def test_fiscal_year_and_comparatives_survive_financial_analysis(self):
        data,content=self.fixture()
        records=snapshot_records(data,content,date(2026,10,13),'issuer')
        financial=analyze_financials(records)
        self.assertEqual([(p['year'],p['period_end']) for p in financial['periods']],
                         [(2025,'2026-03-31'),(2024,'2025-03-31')])
        self.assertEqual(financial['industry_group'],'nonfinancial')
        self.assertEqual(financial['periods'][0]['fields']['net_profit']['value'],259196467437)
        self.assertEqual(financial['periods'][1]['fields']['net_profit']['value'],1121497661342)
        self.assertLess(next(m['value'] for m in financial['metrics'] if m['key']=='net_profit_growth'),0)
        self.assertEqual(financial['periods'][0]['fields']['parent_profit']['page'],10)
        self.assertFalse(financial['errors'])
        trailing=trailing_from_interim(financial,None,date(2026,10,13))
        self.assertFalse(trailing['available'])
        self.assertIn('Đã có BCTC năm',trailing['reason'])

    def test_replaced_pdf_or_non_pdf_is_rejected(self):
        data,content=self.fixture()
        with self.assertRaises(DataSourceError):snapshot_records(data,content+b'changed',date(2026,10,13),'issuer')
        data['sha256']=hashlib.sha256(b'not pdf').hexdigest()
        with self.assertRaises(DataSourceError):snapshot_records(data,b'not pdf',date(2026,10,13),'issuer')

    def test_collector_exposes_consolidated_scope_and_document_provenance(self):
        data,content=self.fixture()
        with TemporaryDirectory() as tmp:
            root=Path(tmp);config=root/'config/issuer_snapshots';config.mkdir(parents=True)
            (config/'TCH_2025.json').write_text(json.dumps(data),encoding='utf-8')
            html=b'<p>26/6/2026 01/04/2025 31/03/2026</p>'
            with patch('src.data.tch_issuer.cached_file',side_effect=[(html,{}),(content,{'retrieved_at':'2026-10-13'})]):
                out=collect_tch_issuer('TCH',date(2026,10,13),root,'test')
        self.assertTrue(out['available'])
        self.assertEqual(out['scope'],'consolidated')
        self.assertEqual(out['sources'][0]['url_or_file'],data['url'])
        self.assertFalse(out['checks']) # A reviewed transcription is not an independent source match.

    def test_future_disclosure_wrong_fiscal_range_and_scopes_are_rejected(self):
        data,content=self.fixture()
        with self.assertRaises(DataSourceError):snapshot_records(data,content,date(2026,6,25),'issuer')
        for key,value in [('period_end','2025-12-31'),('ticker','HHS'),('unit','thousand VND'),('scope','parent')]:
            changed=deepcopy(data);changed[key]=value
            with self.subTest(key=key),self.assertRaises(DataSourceError):
                snapshot_records(changed,content,date(2026,10,13),'issuer')

    def test_both_columns_require_balanced_assets_and_profit_allocation(self):
        for key in ('assets','net_profit'):
            for column in ('value','previous'):
                data,content=self.fixture();data['fields'][key][column]+=1
                with self.subTest(key=key,column=column),self.assertRaises(DataSourceError):
                    snapshot_records(data,content,date(2026,10,13),'issuer')

    def test_internal_organ_identifier_can_differ_from_ticker(self):
        row=dict(ticker='TCH',organCode='HHSF',yearReport=2026,lengthReport=2,
                 publicDate='2026-07-29',updateDate='2026-07-29',isa3=450946642867,
                 isa20=163753308779,isa22=125416921400)
        records=parse_quarters({'data':{'quarters':[row]}},'TCH',date(2026,10,13),'source','nonfinancial')
        self.assertEqual(records[0]['period_end'],'2026-06-30')
        with self.assertRaises(DataSourceError):
            parse_quarters({'data':{'quarters':[row,{**row,'organCode':'OTHER'}]}},'TCH',date(2026,10,13),'source','nonfinancial')
        with self.assertRaises(DataSourceError):
            parse_quarters({'data':{'quarters':[{**row,'ticker':'HHS'}]}},'TCH',date(2026,10,13),'source','nonfinancial')
