"""Macro period semantics, broader industry selection and sector-specific formulas."""
from __future__ import annotations
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from src.data.macro import discover_releases,parse_nso,parse_world_bank
from src.data.industry import parse_vci_universe,collect_industry
from src.data.normalize import parse_annual_financials
from src.analysis.financial import analyze_financials
from src.analysis.context import analyze_context,integrated_thesis
from src.models import AnalysisRequest
from test_analysis_reporting import payload,period

ARTICLE="""<article><div class='post-content'>
<p>GDP quý III/2026 ước tính tăng 9,95% so với cùng kỳ năm trước.</p>
<p>GDP chín tháng năm 2026 ước tăng 9,01% so với cùng kỳ năm trước.</p>
<p>Chỉ số giá tiêu dùng, chỉ số giá vàng và đô la Mỹ. CPI tháng Chín tăng 0,62% so với tháng trước; tăng 5,08% so với cùng kỳ năm trước. Bình quân chín tháng năm 2026, CPI tăng 4,52% so với cùng kỳ năm trước.</p>
<p>Chỉ số giá đô la Mỹ tháng Chín giảm 0,69% so với tháng trước; giảm 1,34% so với cùng kỳ năm trước; giảm 1,07% so với tháng 12/2025.</p>
<p>Tính đến thời điểm 28/9/2026, huy động vốn tăng 9,78%; tăng trưởng tín dụng của nền kinh tế đạt 10,89% so với cuối năm trước.</p>
<p>Tính chung chín tháng năm 2026, doanh thu hoạt động viễn thông ước đạt 308,3 nghìn tỷ đồng, tăng 6,86% so với cùng kỳ.</p>
<p>Tính chung chín tháng năm 2026, kim ngạch xuất khẩu hàng hóa đạt 434,30 tỷ USD, tăng 24,5% so với cùng kỳ.</p>
</div></article>"""
RELEASE={"period":"9/2026","published_at":"2026-10-03","url":"https://www.nso.gov.vn/report"}

class MacroTests(unittest.TestCase):
    def test_distinguishes_gdp_cumulative_cpi_average_and_usd_index(self):
        fields={f['key']:f for f in parse_nso(ARTICLE,RELEASE,'NSO')}
        self.assertEqual(fields['gdp_ytd']['value'],9.01)
        self.assertEqual(fields['cpi_ytd']['value'],4.52)
        self.assertEqual(fields['usd_index_yoy']['value'],-1.34)
        self.assertEqual(fields['credit_growth']['value'],10.89)
        self.assertIn('28/9/2026',fields['credit_growth']['period'])
        self.assertEqual(fields['exports_growth']['value'],24.5)
    def test_soft_hyphen_does_not_break_label(self):
        fields=parse_nso(ARTICLE.replace('doanh thu','d\u00adoanh thu'),RELEASE,'NSO')
        self.assertEqual(next(f for f in fields if f['key']=='telecom_growth')['value'],6.86)
    def test_release_dates_filter_future_and_use_empty_link_sibling(self):
        html="""<p><a href='https://www.nso.gov.vn/report'></a></p><section class='item'><h3>Báo cáo</h3><span class='archive-issue-date'>Ngày đăng: 03/10/2026</span><span class='archive-reference-period'>Kỳ tham chiếu: 9/2026</span></section>"""
        self.assertFalse(discover_releases(html,date(2026,10,2)))
        self.assertEqual(discover_releases(html,date(2026,10,9))[0]['published_at'],'2026-10-03')
    def test_wdi_update_is_not_publication_missing_and_future_year_omitted(self):
        rows=[{'countryiso3code':'VNM','indicator':{'id':'NY.GDP.MKTP.KD.ZG'},'date':str(y),'value':v} for y,v in [(2026,9),(2025,8),(2024,None)]]
        p=[{'lastupdated':'2026-10-08'},rows]
        result=parse_world_bank(p,'gdp_annual',date(2026,10,9),'WB')
        self.assertEqual([r['period'] for r in result],['2025']);self.assertIsNone(result[0]['published_at'])
        self.assertFalse(parse_world_bank(p,'gdp_annual',date(2026,10,7),'WB'))
    def test_stale_interest_labeled_historical(self):
        p=[{'lastupdated':'2026-10-08'},[{'countryiso3code':'VNM','indicator':{'id':'FR.INR.LEND'},'date':'2023','value':9.3}]]
        self.assertTrue(parse_world_bank(p,'lending_annual',date(2026,10,9),'WB')[0]['stale'])

class IndustryTests(unittest.TestCase):
    @staticmethod
    def normalized_period(year,profit=10,equity=100,scope="consolidated"):
        return {**period(year,profit,equity,scope),"period_end":f"{year}-12-31"}
    def test_classification_ignores_ratings_quotes_indexes_and_otc(self):
        company={'code':'AAA','floor':'HOSE','icbLv4':{'code':'1757','name':'Thép','level':4},'rating':'BUY','currentPrice':999}
        groups=parse_vci_universe({'data':[company,dict(company,code='OTC',floor='OTC'),dict(company,code='VNINDEX',isIndex=True)]})
        self.assertEqual(groups[0]['symbols'],['AAA']);self.assertNotIn('rating',str(groups))
    def test_median_excludes_target_and_different_missing_metrics(self):
        financial=analyze_financials([period(2025,30,100),period(2024,20,80)])
        peers=[{'ticker':t,'financial':analyze_financials([period(2025,p,100),period(2024,10,80)])} for t,p in [('BBB',10),('CCC',20),('DDD',100)]]
        macro={'indicators':[]};industry={'peers':peers,'period_end':'2025-12-31','code':'1757','taxonomy':'Vietcap ICB','name':'Thép'}
        _,result=analyze_context(macro,industry,financial)
        roe=next(c for c in result['comparisons'] if c['key']=='roe')
        self.assertAlmostEqual(roe['sample_median'],20/90*100);self.assertEqual(roe['sample_size'],3)
        self.assertTrue(integrated_thesis(macro,result,financial))
    def test_broader_group_only_when_same_period_peers_insufficient(self):
        target=analyze_financials([period(2025,30,100),period(2024,20,80)])
        groups=[{'level':4,'code':'9537','name':'Phần mềm','symbols':['AAA'],'url':'test'}, {'level':2,'code':'9500','name':'Công nghệ','symbols':['AAA','BBB','CCC'],'url':'test'}]
        universe={'groups':groups,'retrieved_at':'2026-10-09T10:00:00+07:00','complete':True,'taxonomy':'Vietcap ICB','retrieval_mode':'test'}
        with TemporaryDirectory() as folder,patch('src.data.industry.collect_universe',return_value=universe),patch('src.data.industry.download',return_value=b'{}'),patch('src.data.industry.parse_annual_financials',side_effect=lambda *a:[self.normalized_period(2025),self.normalized_period(2024)]):
            result=collect_industry('AAA',date(2026,10,9),target,Path(folder),'fixture')
        self.assertEqual(result['code'],'9500');self.assertEqual(len(result['peers']),2)
        self.assertTrue(any('mở rộng' in w for w in result['warnings']))
    def test_peer_comparison_rejects_different_end_date_or_scope(self):
        target=analyze_financials([period(2025,30,100)])
        group={'code':'1757','level':4,'name':'Thép','symbols':['AAA','BBB','CCC','DDD','EEE'],'url':'test'}
        universe={'groups':[group],'retrieved_at':'2026-10-09T10:00:00+07:00','complete':True,'taxonomy':'Vietcap ICB','retrieval_mode':'test'}
        def parse(*args):
            symbol=args[3].split('_')[1]
            return [self.normalized_period(2024 if symbol=='DDD' else 2025,scope='parent' if symbol=='EEE' else 'consolidated')]
        with TemporaryDirectory() as folder,patch('src.data.industry.collect_universe',return_value=universe),patch('src.data.industry.download',return_value=b'{}'),patch('src.data.industry.parse_annual_financials',side_effect=parse):
            result=collect_industry('AAA',date(2026,10,9),target,Path(folder),'fixture')
        self.assertEqual({p['ticker'] for p in result['peers']},{'BBB','CCC'})
        self.assertEqual({p['ticker'] for p in result['excluded']},{'DDD','EEE'})
    def test_macro_missing_never_creates_fake_driver(self):
        f=analyze_financials([period(2025,20,100)])
        macro,industry=analyze_context({'indicators':[]},{'peers':[],'code':'1757'},f)
        self.assertEqual(industry['drivers'],[]);self.assertFalse(industry['comparisons'])
    def test_new_sections_are_valid_requests(self):
        self.assertEqual(AnalysisRequest('HPG',date(2025,1,1),date(2026,10,9),sections=['macro','industry']).sections,['macro','industry'])

class FinancialSectorTests(unittest.TestCase):
    def test_invalid_24_month_annual_period_omitted_with_reason(self):
        p=payload();p['Head'][0].update({'PeriodBegin':'202501','PeriodEnd':'202612'})
        issues=[];records=parse_annual_financials(p,'income',date(2026,10,9),'test',issues)
        self.assertNotIn(2025,[r['year'] for r in records]);self.assertTrue(issues)
    def test_bank_ratios_use_bank_specific_inputs(self):
        r=period(2025,20,100)
        r['business_type']=3
        for k,v in {'net_interest_income':60,'operating_cost':20,'pre_provision_profit':80,'customer_loans':150,'customer_deposits':200}.items():r['fields'][k]={'value':v}
        f=analyze_financials([r,dict(period(2024,10,80),business_type=3)])
        metrics={m['key']:m['value'] for m in f['metrics']}
        self.assertEqual(metrics['loan_deposit'],75);self.assertEqual(metrics['cir'],20)
        self.assertNotIn('cash_conversion',metrics);self.assertNotIn('gross_margin',metrics)
    def test_securities_revenue_mix_not_industrial_margin(self):
        r=period(2025,20,100);r['business_type']=2
        r['fields']['brokerage_revenue']={'value':50};r['fields']['lending_revenue']={'value':30}
        f=analyze_financials([r]);metrics={m['key']:m['value'] for m in f['metrics']}
        self.assertEqual(metrics['brokerage_share'],25);self.assertEqual(metrics['lending_share'],15)
        self.assertNotIn('gross_margin',metrics)

if __name__=='__main__':unittest.main()
