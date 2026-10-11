"""Issuer PDF period/column gates, source-close statistics and earnings quality."""
from copy import deepcopy
from datetime import date, datetime
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest
import pymupdf

from src.data.shs_issuer import parse_shs_pdf, compare_kbs_pdf, row_amounts, collect_shs_issuer
from src.data.providers import DataSourceError, VN_TIME
from src.data.industry import collect_industry
from src.analysis.context import analyze_context
from src.analysis.market import analyze_market
from src.analysis.financial import analyze_financials
from src.analysis.recommendation import build_recommendation
from src.analysis.valuation import analyze_valuation
import test_exchange_recommendation as exchange_fixtures
from test_valuation_upgrade import value
from test_analysis_reporting import period

ASOF=date(2026,10,11)


class Page:
    rect=pymupdf.Rect(0,0,595,842)
    def __init__(self,text):self.text=text
    def get_text(self,**kwargs):return self.text


class Document(list):
    def __enter__(self):return self
    def __exit__(self,*args):pass


def document():
    return Document([Page('CÔNG TY CỔ PHẦN CHỨNG KHOÁN SÀI GÒN - HÀ NỘI\nCho năm tài chính kết thúc ngày 31/12/2025 (đã được kiểm toán)\nBáo cáo tài chính của Công ty'),
                     Page('Báo cáo tình hình tài chính\n31/12/2025\n01/01/2025\nVND\nVND\n270\nTỔNG CỘNG TÀI SẢN\n3.000.000\n2.500.000\n300\nNỢ PHẢI TRẢ\n2.000.000\n1.600.000\n400\nVỐN CHỦ SỞ HỮU\n1.000.000\n900.000'),
                     Page('Báo cáo kết quả hoạt động\nNăm 2025\nNăm 2024\nVND\nVND\n20\nCộng doanh thu hoạt động\n600.000\n500.000\n200\nLỢI NHUẬN KẾ TOÁN SAU THUẾ TNDN\n150.000\n100.000'),
                     Page('Báo cáo lưu chuyển tiền tệ\nNăm 2025\nNăm 2024\nVND\nVND\n60\nLưu chuyển tiền thuần từ hoạt động kinh doanh\n(200.000)\n(100.000)')])


class SHSPdfTests(unittest.TestCase):
    def parse(self,doc=None,published='2026-04-09',asof=ASOF):
        with patch('src.data.shs_issuer.pymupdf.open',return_value=doc or document()):
            return parse_shs_pdf(b'fixture',2025,published,asof,'issuer')

    def test_standalone_year_columns_vnd_and_parent_profit(self):
        records=self.parse();f=analyze_financials(records)
        self.assertEqual([p['year'] for p in f['periods']],[2025,2024])
        self.assertEqual(f['periods'][0]['fields']['equity']['value'],1000000)
        self.assertEqual(f['periods'][0]['fields']['parent_profit']['value'],150000)
        self.assertEqual(f['periods'][0]['fields']['cfo']['value'],-200000)
        self.assertEqual(f['periods'][0]['scope'],'separate')
        self.assertIn('riêng lẻ',next(m['label'] for m in f['metrics'] if m['key']=='roe'))
        self.assertEqual(f['periods'][0]['fields']['equity']['page'],2)

    def test_future_publication_or_cover_is_rejected(self):
        with self.assertRaises(DataSourceError):self.parse(published='2026-11-01')
        d=document();d.insert(0,Page('Hà Nội, ngày 10 tháng 04 năm 2026'))
        with self.assertRaises(DataSourceError):self.parse(d,asof=date(2026,4,9))
        self.assertEqual(self.parse(d)[0]['published_at'],'2026-04-10')

    def test_bad_period_scope_unit_column_and_identity_rejected(self):
        for index,old,new in [(0,'31/12/2025','30/6/2025'),(0,'Báo cáo tài chính của Công ty','Báo cáo tài chính hợp nhất'),(1,'VND','USD'),(1,'3.000.000','4.000.000'),(2,'Năm 2025\nNăm 2024','Năm 2024\nNăm 2025'),(3,'(200.000)','unknown')]:
            d=document();d[index].text=d[index].text.replace(old,new)
            with self.subTest(new=new),self.assertRaises(DataSourceError):self.parse(d)

    def test_duplicate_or_wrong_label_is_not_silently_extracted(self):
        row='270\nTỔNG CỘNG TÀI SẢN\n3.000.000\n2.500.000\n'
        with self.assertRaises(DataSourceError):row_amounts(row*2,'270','tong cong tai san')
        self.assertIsNone(row_amounts(row,'270','no phai tra'))

    def test_cross_check_numeric_mismatch_does_not_promote_kbs_period(self):
        records=self.parse()
        with TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'data/raw/financials';folder.mkdir(parents=True)
            p={'Head':[{'ID':1,'YearPeriod':2025,'United':'ĐL','TermCode':'N','PeriodEnd':'202612','DatePubDepartment':'2026-03-23','LastUpdate':'2026-03-24'}],
               'Content':{'data':[{'ReportNormID':4478,'Value1':1000}]}}
            path=folder/'run_balance.json';path.write_text(json.dumps(p),encoding='utf8')
            checks=compare_kbs_pdf(records,root,'run',ASOF)
            self.assertTrue(checks[0]['match']);self.assertEqual(records[0]['period_end'],'2025-12-31')
            p['Content']['data'][0]['Value1']=2000;path.write_text(json.dumps(p),encoding='utf8')
            self.assertFalse(compare_kbs_pdf(records,root,'run',ASOF)[0]['match'])

    def test_verified_listing_and_pdf_cache_work_without_network(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'data/raw/documents';folder.mkdir(parents=True)
            url='https://www.shs.com.vn/cong-bo-thong-tin/shs-cbtt-bao-cao-thuong-nien-nam-2025'
            raw='<h1>SHS: CBTT Báo cáo thường niên năm 2025</h1>Ngày đăng: 09/04/2026'.encode()
            p=folder/'SHS_2025_issuer_listing.html';p.write_bytes(raw)
            p.with_suffix('.html.json').write_text(json.dumps(dict(url=url,retrieved_at=datetime.now(VN_TIME).isoformat(),sha256=hashlib.sha256(raw).hexdigest())),encoding='utf8')
            pdf=folder/'fixture.pdf';pdf.write_bytes(b'fixture')
            ref={'reports':[dict(year=2025,file=pdf.relative_to(root).as_posix(),sha256=hashlib.sha256(b'fixture').hexdigest(),download_url='https://example.test/copy.pdf')]}
            with patch('src.data.reference_miner.download',side_effect=DataSourceError('DNS')),patch('src.data.shs_issuer.download',side_effect=DataSourceError('DNS')),patch('src.data.shs_issuer.pymupdf.open',return_value=document()):
                result=collect_shs_issuer('SHS',ASOF,ref,root,'run')
            self.assertTrue(result['available']);self.assertFalse(result['errors'])
            # Tampering must not become a successful fallback when DNS fails.
            p.write_bytes(b'tampered')
            with patch('src.data.reference_miner.download',side_effect=DataSourceError('DNS')):
                result=collect_shs_issuer('SHS',ASOF,ref,root,'run2')
            self.assertFalse(result['available']);self.assertTrue(result['errors'])

    def test_bad_pdf_checksum_cannot_be_promoted(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);pdf=root/'fake.pdf';pdf.write_bytes(b'changed')
            ref={'reports':[dict(year=2025,file='fake.pdf',sha256='0'*64)]}
            html='<h1>Báo cáo thường niên năm 2025</h1>Ngày đăng: 09/04/2026'.encode()
            with patch('src.data.shs_issuer.cached_file',return_value=(html,{})):
                result=collect_shs_issuer('SHS',ASOF,ref,root,'run')
            self.assertFalse(result['available']);self.assertFalse(result['records'])


class NewMarketAndRecommendationTests(unittest.TestCase):
    def test_close_statistics_are_useful_and_never_labelled_total_return(self):
        rows=[dict(close=v,date=f'2026-10-0{i+1}',volume=10,price_provider='KBS') for i,v in enumerate([100,120,90,110])]
        m=analyze_market(rows,{'status':'matched'})
        self.assertAlmostEqual(m['return_pct'],10);self.assertAlmostEqual(m['max_drawdown_pct'],-25)
        self.assertGreater(m['annualized_volatility_pct'],0)
        self.assertFalse(m['adjustment_verified']);self.assertIn('không phải tổng lợi nhuận',m['return_note'])
        rows[0]['adjusted_close']=50
        self.assertEqual(analyze_market(rows,{'status':'matched'})['chart_prices'],[100,120,90,110])
        self.assertIsNone(analyze_market(rows,{'status':'unverified'})['return_pct'])

    def test_declining_realized_profit_prevents_accumulation(self):
        r=exchange_fixtures.RecommendationTests().fixture();r['financial']['industry_group']='securities'
        r['financial']['metrics'].extend([dict(key='realized_profit_growth',value=-18.19,inputs=[]),dict(key='unrealized_profit_share',value=42.88,inputs=[])])
        rec=build_recommendation(r)
        self.assertEqual(rec['stance'],'THEO DÕI');self.assertIn('18.19%',rec['reason']);self.assertIn('42.88%',rec['reason'])

    def test_prior_year_peer_pb_not_used_with_current_year_book_value(self):
        bm=dict(available=True,median_pb=2,period_end='2024-12-31',scope='consolidated')
        v=value(industry_benchmark=bm)
        self.assertFalse(v['industry']['available']);self.assertIn('khác',v['industry']['reason']);self.assertTrue(v['pe']['available'])

    def test_prior_common_industry_period_uses_own_matching_year(self):
        def record(year,profit):
            r=period(year,profit,100);r['period_end']=f'{year}-12-31';return r
        own=analyze_financials([record(2025,30),record(2024,15),record(2023,10)])
        universe=dict(groups=[dict(code='test',name='Test',symbols=['AAA','BBB','CCC'],url='https://example.test')],taxonomy='KBS',complete=True,retrieved_at='2026-10-11T12:00:00+07:00',retrieval_mode='fixture')
        with TemporaryDirectory() as tmp,patch('src.data.industry.collect_universe',return_value=universe),patch('src.data.industry.download',return_value=b'{}'),patch('src.data.industry.parse_annual_financials',side_effect=lambda *args:[record(2024,15),record(2023,10)]):
            industry=collect_industry('AAA',ASOF,own,Path(tmp),'run')
        macro,industry=analyze_context(dict(indicators=[]),industry,own)
        self.assertEqual(industry['period_end'],'2024-12-31')
        comparison=next(c for c in industry['comparisons'] if c['key']=='net_profit_growth')
        self.assertEqual(comparison['company_value'],50)
        self.assertEqual(comparison['sample_median'],50)


if __name__=='__main__':unittest.main()
