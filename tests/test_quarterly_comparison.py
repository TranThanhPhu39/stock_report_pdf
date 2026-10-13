from copy import deepcopy
from datetime import date
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from src.data.quarterly import parse_quarters,quarter_observation,collect_quarterly
from src.data.providers import DataSourceError
from src.analysis.trailing import trailing_from_interim
from src.analysis.comparison import compare_results
from src.analysis.decision import decision_summary
from src.models import AnalysisRequest
from src.data.ssi_interim import parse_ssi_interim,collect_ssi_interim
import test_exchange_recommendation as rec_fixtures

ASOF=date(2026,10,13)


def row(year,quarter,profit=10):
    return dict(ticker='HPG',organCode='HPG',yearReport=year,lengthReport=quarter,
                publicDate=f'{year if quarter<4 else year+1}-{quarter*3+1 if quarter<4 else 1:02d}-20',
                updateDate=f'{year if quarter<4 else year+1}-{quarter*3+1 if quarter<4 else 1:02d}-21',
                isa20=profit,isa22=profit-1,isa3=100)


class QuarterlyTests(unittest.TestCase):
    def parse(self,rows,asof=ASOF):
        return parse_quarters({'data':{'quarters':rows}},'HPG',asof,'fixture','nonfinancial')

    def test_quarters_sort_and_preserve_independent_three_month_period(self):
        records=self.parse([row(2026,1),row(2026,2)])
        self.assertEqual(records[0]['period_begin'],'2026-04-01')
        self.assertEqual(records[0]['period_end'],'2026-06-30')

    def test_future_publication_revision_and_unpublished_period_excluded(self):
        r=row(2026,2)
        for key in ['publicDate','updateDate']:
            bad=deepcopy(r);bad[key]='2026-11-01'
            self.assertFalse(self.parse([bad]))
        r['publicDate']='2026-06-01'
        self.assertFalse(self.parse([r]))

    def test_missing_publication_dates_are_not_guessed(self):
        r=row(2026,2);r.pop('publicDate')
        self.assertFalse(self.parse([r]))

    def test_wrong_symbol_duplicate_conflict_and_invalid_values_fail(self):
        for key,value in [('ticker','FPT'),('isa20',True),('isa20',float('nan')),('lengthReport',0),('lengthReport',True)]:
            bad=row(2026,2);bad[key]=value
            with self.assertRaises(DataSourceError):self.parse([bad])
        with self.assertRaises(DataSourceError):self.parse([row(2026,2,10),row(2026,2,20)])

    def test_identical_duplicate_not_double_counted_and_zero_is_retained(self):
        r=row(2026,2,0)
        records=self.parse([r,r]);self.assertEqual(len(records),1)
        self.assertEqual(records[0]['fields']['net_profit']['value'],0)

    def test_ttm_requires_four_consecutive_quarters_and_is_not_valuation_input(self):
        records=self.parse([row(2025,3,10),row(2025,4,20),row(2026,1,30),row(2026,2,40)])
        t=quarter_observation(records)
        self.assertTrue(t['available']);self.assertEqual(t['fields']['net_profit']['value'],100)
        self.assertEqual(t['period_begin'],'2025-07-01');self.assertFalse(t['usable_for_valuation'])
        self.assertFalse(quarter_observation(records[:2]+records[3:])['available'])

    def test_missing_parent_profit_does_not_become_consolidated_profit(self):
        records=self.parse([row(2025,3),row(2025,4),row(2026,1),row(2026,2)])
        records[0]['fields'].pop('parent_profit')
        t=quarter_observation(records)
        self.assertTrue(t['available']);self.assertNotIn('parent_profit',t['fields'])

    def test_provider_outage_does_not_replace_primary_financials(self):
        with TemporaryDirectory() as d,patch('src.data.quarterly.download',side_effect=DataSourceError('offline')):
            out=collect_quarterly('HPG',ASOF,{},Path(d),'test')
            self.assertFalse(out['available']);self.assertTrue(out['errors'])


def verified_inputs():
    def field(value,period,previous=None):
        f=dict(value=value,period=period,unit='VND',statement_scope='consolidated',source_id='fixture',published_at='2026-08-01')
        if previous is not None:f['previous']=previous
        return f
    annual=dict(year=2025,scope='consolidated',period_end='2025-12-31',fields={k:field(v,'2025') for k,v in [('net_profit',100),('parent_profit',90),('revenue',1000),('cfo',80)]})
    interim=dict(valid=True,period_type='half_year',period_begin='2026-01-01',period_end='2026-06-30',fields={k:field(v,'2026-06-30',previous) for k,v,previous in [('net_profit',60,40),('parent_profit',54,36),('revenue',600,400),('cfo',30,20)]})
    return {'periods':[annual]},interim


class TrailingTests(unittest.TestCase):
    def test_nonfinancial_ttm_uses_annual_plus_ytd_minus_comparative_not_double_ytd(self):
        f,i=verified_inputs();ttm=trailing_from_interim(f,i,ASOF)
        self.assertTrue(ttm['available']);self.assertEqual(ttm['fields']['net_profit']['value'],120)
        self.assertEqual(ttm['fields']['parent_profit']['value'],108)
        self.assertEqual(ttm['fields']['cfo']['value'],90)
        self.assertEqual(len(ttm['fields']['net_profit']['inputs']),3)

    def test_bad_scope_dates_missing_comparative_or_units_block(self):
        for problem in ['scope','unit','published','comparative','period','valid']:
            f,i=verified_inputs()
            if problem=='scope':f['periods'][0]['scope']='separate'
            elif problem=='valid':i['valid']=False
            else:
                b=i['fields']['net_profit']
                if problem=='unit':b['unit']='thousand_VND'
                elif problem=='published':b['published_at']='2026-11-01'
                elif problem=='comparative':b.pop('previous')
                else:b['period']='2026-03-31'
            self.assertFalse(trailing_from_interim(f,i,ASOF)['available'],problem)

    def test_missing_parent_profit_never_substituted(self):
        f,i=verified_inputs();i['fields'].pop('parent_profit')
        ttm=trailing_from_interim(f,i,ASOF)
        self.assertTrue(ttm['available']);self.assertNotIn('parent_profit',ttm['fields'])


class SsiInterimTests(unittest.TestCase):
    def fixture(self):
        header='Công ty Cổ phần Chứng khoán SSI. Soát xét hợp nhất sáu tháng kết thúc ngày 30 tháng 6 năm 2026. Công bố vào ngày 14/8/2026.'
        pages=[dict(page=1,text=header),
               dict(page=2,text='B01a-CTCK/HN hợp nhất VND ngày 30 tháng 6 năm 2026; năm 2025\nTổng cộng tài sản 10.000.000.000 8.000.000.000\n300 | Nợ phải trả 6.000.000.000 5.000.000.000\n400 | Vốn chủ sở hữu 4.000.000.000 3.000.000.000'),
               dict(page=3,text='B02a-CTCK/HN hợp nhất VND sáu tháng kết thúc ngày 30 tháng 6 năm 2026; năm 2025\n20 | Cộng doanh thu hoạt động 6.000.000.000 5.000.000.000\n200 | Lợi nhuận kế toán sau thuế 2.000.000.000 1.000.000.000\n201 | Lợi nhuận sau thuế phân bổ cho chủ sở hữu 1.800.000.000 900.000.000'),
               dict(page=4,text='B03b-CTCK/HN hợp nhất VND sáu tháng kết thúc ngày 30 tháng 6 năm 2026; năm 2025\n60 | Lưu chuyển tiền thuần (1.000.000.000) (2.000.000.000)')]
        annual={'periods':[dict(period_end='2025-12-31',scope='consolidated',fields={k:dict(value=v) for k,v in [('assets',8e9),('liabilities',5e9),('equity',3e9)]})]}
        qs=[dict(year=2026,quarter=q,fields={k:dict(value=v) for k,v in [('revenue',3e9),('net_profit',1e9),('parent_profit',.9e9)]}) for q in (1,2)]
        return pages,annual,qs

    def test_reviewed_pdf_validates_opening_balance_and_current_ytd(self):
        p,a,q=self.fixture();out=parse_ssi_interim(p,2026,'fixture',a,q,ASOF)
        self.assertTrue(out['valid']);self.assertEqual(out['fields']['cfo']['value'],-1e9)
        self.assertEqual(out['fields']['parent_profit']['previous'],.9e9)
        self.assertEqual(len(out['checks']),6)

    def test_collector_recognizes_real_ssi_listing_markup(self):
        pages,annual,qs=self.fixture()
        html=b'<div class="chart__content__item"><p>Bao cao tai chinh hop nhat soat xet ban nien 2026</p><a href="/upload/files/IR/reviewed.pdf"></a></div>'
        meta={'retrieved_at':'2026-10-13T10:00:00+07:00'}
        with TemporaryDirectory() as d,patch('src.data.ssi_interim.cached_file',side_effect=[(html,meta),(b'%PDF',meta)]),patch('src.data.ssi_interim.extract_pages',return_value=(pages,'sha')):
            out=collect_ssi_interim(ASOF,annual,{'records':qs},Path(d),'test')
        self.assertTrue(out['available']);self.assertTrue(out['sources'])

    def test_conflicting_columns_future_publication_or_missing_comparisons_block(self):
        for problem in ['balance','quarters','date','scope']:
            p,a,q=self.fixture()
            if problem=='balance':a['periods'][0]['fields']['equity']['value']=99e9
            elif problem=='quarters':q.pop()
            elif problem=='date':p[0]['text']=p[0]['text'].replace('14/8/2026','14/11/2026')
            else:a['periods'][0]['scope']='separate'
            with self.assertRaises(DataSourceError):parse_ssi_interim(p,2026,'fixture',a,q,ASOF)


class ComparisonTests(unittest.TestCase):
    def fixtures(self):
        a=rec_fixtures.RecommendationTests().fixture();b=deepcopy(a)
        a['request']['ticker']='HPG';b['request']['ticker']='FPT'
        for r in (a,b):r['company']['snapshot_at']=r['request']['as_of']
        return a,b

    def test_common_period_and_price_are_used_for_annual_multiples(self):
        a,b=self.fixtures();out=compare_results([a,b])
        self.assertTrue(out['available']);self.assertEqual(out['period_end'],'2025-12-31')
        self.assertEqual(out['rows'][0]['pe_annual'],10)

    def test_aligns_older_year_instead_of_comparing_different_years(self):
        a,b=self.fixtures();b['financial']['periods']=b['financial']['periods'][1:]
        out=compare_results([a,b])
        self.assertEqual(out['period_end'],'2024-12-31');self.assertTrue(out['rows'][0]['notes'])
        b['financial']['periods'][0]['scope']='separate'
        out=compare_results([a,b]);self.assertIsNone(out['period_end'])
        self.assertIsNone(out['rows'][0]['net_profit_vnd'])

    def test_different_price_date_unmatched_quote_or_share_snapshot_hides_multiple(self):
        for problem in ['price','quote','shares']:
            a,b=self.fixtures()
            if problem=='price':b['market']['latest_date']='2026-10-07'
            elif problem=='quote':b['quality']['price_check']['checks']=[]
            else:b['company']['snapshot_at']='2026-10-08'
            r=compare_results([a,b])['rows'][1]
            self.assertIsNone(r['pe_annual']);self.assertIsNone(r['pb'])

    def test_mismatched_ttm_window_hides_ttm_multiple(self):
        a,b=self.fixtures();f,i=verified_inputs();ttm=trailing_from_interim(f,i,ASOF)
        a['financial']['ttm']=ttm;b['financial']['ttm']=deepcopy(ttm)
        b['financial']['ttm']['period_end']='2026-03-31'
        self.assertIsNone(compare_results([a,b])['rows'][1]['pe_ttm'])

    def test_selected_codes_validate_and_deduplicate_before_network(self):
        r=AnalysisRequest('HPG',date(2025,1,1),ASOF,comparison_tickers=['hpg','fpt','FPT','vnm'])
        self.assertEqual(r.comparison_tickers,['FPT','VNM'])
        for symbols in [['../SSI'],['AAA','BBB','CCC','DDD','EEE']]:
            with self.assertRaises(ValueError):AnalysisRequest('HPG',date(2025,1,1),ASOF,comparison_tickers=symbols)

    def test_summary_exposes_basis_confidence_and_missing_ttm(self):
        a,b=self.fixtures();summary=decision_summary(a)
        self.assertIn('2025-12-31',summary['annual_basis'])
        self.assertTrue(any('TTM' in message for message in summary['blockers']))
        self.assertIsNotNone(summary['low_vnd'])
