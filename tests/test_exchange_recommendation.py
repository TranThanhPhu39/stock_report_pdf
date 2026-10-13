"""HNX/UPCoM source fallbacks, recommendation gates and physical PDF columns."""
from copy import deepcopy
from datetime import date,datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch
from src.data.providers import parse_vietcap_chart,fetch_kbs_prices,DataSourceError,VN_TIME
from src.data.research import collect_research,compare_prices
from src.data.acquisition import acquire
from src.data.normalize import parse_annual_financials
from src.analysis.recommendation import build_recommendation
from src.reporting.pdf_exporter import generate_report
from test_analysis_reporting import payload
from test_valuation_upgrade import result,financial,value,market,NOW


class ExchangeTests(unittest.TestCase):
    def chart(self):
        return [{"symbol":"SHS","t":[int(datetime(2026,10,8,tzinfo=VN_TIME).timestamp()),int(datetime(2026,10,9,tzinfo=VN_TIME).timestamp())],
                 "o":[12000,12100],"h":[12200,12500],"l":[11800,12000],"c":[12100,12200],"v":[100,200]}]
    def test_vietcap_preserves_vnd_and_filters_dates(self):
        rows=parse_vietcap_chart(self.chart(),"SHS",date(2026,10,1),date(2026,10,8))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]["close"],12100);self.assertIsNone(rows[0]["adjusted_close"])
    def test_wrong_symbol_and_array_lengths_rejected(self):
        for kind in ["symbol","length"]:
            p=self.chart()
            if kind=="symbol":p[0]["symbol"]="VNZ"
            else:p[0]["c"].pop()
            with self.assertRaises(DataSourceError):parse_vietcap_chart(p,"SHS",date(2026,10,1),NOW)
    def test_kbs_request_buffer_does_not_admit_future_rows(self):
        raw=json.dumps({'symbol':'SHS','data_day':[{'t':d,'o':10,'h':11,'l':9,'c':10,'v':2} for d in ['2026-10-08','2026-10-09','2026-10-10']]}).encode()
        with patch('src.data.providers.download',return_value=raw) as call:
            r=fetch_kbs_prices('SHS',date(2026,10,1),date(2026,10,9))
        self.assertIn('edate=11-10-2026',call.call_args[0][0]);self.assertEqual([p['date'] for p in r['rows']],['2026-10-08','2026-10-09'])
    def test_third_price_provider_when_both_fail(self):
        rows=parse_vietcap_chart(self.chart(),"SHS",date(2026,10,1),date(2026,10,8))
        response={"raw":b'[]',"rows":rows,"url":"https://example.test/chart","retrieved_at":NOW.isoformat(),"cutoff":"2026-10-08","meta":{}}
        with TemporaryDirectory() as d,patch('src.data.acquisition.fetch_daily_prices',side_effect=DataSourceError('missing')),patch('src.data.acquisition.fetch_kbs_prices',side_effect=DataSourceError('offline')),patch('src.data.acquisition.fetch_vietcap_prices',return_value=response):
            r=acquire('SHS',date(2026,10,1),NOW,Path(d));self.assertEqual(r['prices']['provider'],'Vietcap');self.assertFalse(r['errors'])
    def test_kbs_primary_uses_vietcap_when_yahoo_missing(self):
        rows=parse_vietcap_chart(self.chart(),"SHS",date(2026,10,1),date(2026,10,8))
        for row in rows:row['price_provider']='KBS'
        resp={"raw":json.dumps(self.chart()).encode(),"rows":rows,"url":"https://example.test/chart","retrieved_at":NOW.isoformat()}
        with TemporaryDirectory() as d,patch('src.data.research.download',side_effect=DataSourceError('other offline')),patch('src.data.research.fetch_daily_prices',side_effect=DataSourceError('Yahoo missing')),patch('src.data.research.fetch_vietcap_prices',return_value=resp) as fetch:
            r=collect_research('SHS',NOW,rows,Path(d),'fixture')
            q=r['quote_check'];self.assertEqual(q['reference_provider'],'Vietcap');self.assertEqual(q['status'],'matched')
            self.assertEqual(q['checks'][0]['primary_close'],12100);self.assertEqual(q['checks'][0]['reference_close'],12100)
            self.assertTrue(q['source_id'].startswith('VIETCAP'));fetch.assert_called_once()
            self.assertFalse(any(e['stage']=='price_check' for e in r['errors']))
    def test_three_periods_only_when_unused_value_empty(self):
        p=payload();p['Head']=p['Head'][:3]
        with self.assertRaises(DataSourceError):parse_annual_financials(p,'income',NOW,'fixture')
        for row in p['Content']['income']:row['Value4']=None
        self.assertEqual(len(parse_annual_financials(p,'income',NOW,'fixture')),3)
        p['Head']=p['Head'][:2]
        with self.assertRaises(DataSourceError):parse_annual_financials(p,'income',NOW,'fixture')
    def test_securities_cfo_4735_is_available_without_industrial_conversion(self):
        p=payload();p['Content']={'cashflow':[{'ReportNormID':4735,'Name':'CFO chứng khoán','Value1':-1403638756}]}
        parsed=parse_annual_financials(p,'cashflow',NOW,'fixture')
        self.assertEqual(parsed[0]['fields']['cfo']['value'],-1403638756000)


class RecommendationTests(unittest.TestCase):
    def fixture(self):
        r=result(['overview','financial','valuation','risks']);r['financial']=financial();r['market']=market()
        r['valuation']=value();r['quality']['price_check']=compare_prices([{'date':'2026-10-08','close':20000}],{'data_day':[{'t':'2026-10-08','c':20000}]},NOW)
        r['quality']['financial_check']['status']='matched_selected_fields'
        r['quality']['financial_check']['checks']=[dict(metric='net_profit',period='2025',match=True)]
        next(m for m in r['financial']['metrics'] if m['key']=='net_profit_growth')['value']=20
        r['valuation']['primary']={'available':True,'selected_method':'P/B mẫu','source_ids':['fixture'], 'upside_pct':35,'selection_reason':'Fixture đồng kỳ','methodology':'Mẫu dữ liệu kiểm thử','comparisons':[]}
        r['valuation']['primary']['methods']=[{'method':'P/B','target_price_vnd':26000,'weight_pct':50,'contribution_vnd':13000},{'method':'P/E','target_price_vnd':28000,'weight_pct':50,'contribution_vnd':14000}]
        r['valuation']['primary']['target_price_vnd']=27000
        return r
    def test_opportunity_has_sources_conditions_and_invalidation(self):
        r=build_recommendation(self.fixture());self.assertIn('TÍCH LŨY',r['stance']);self.assertTrue(r['entry_ceiling_vnd'])
        for item in r['opportunities']:
            for key in ['evidence','catalyst','invalidation','source_ids','period']:self.assertTrue(item[key])
    def test_unverified_finance_or_missing_cfo_does_not_recommend_buy(self):
        for kind in ['unverified','missing_cfo']:
            r=self.fixture()
            if kind=='unverified':r['quality']['financial_check']['status']='not_independently_checked'
            else:next(m for m in r['financial']['metrics'] if m['key']=='cfo')['value']=None
            self.assertEqual(build_recommendation(r)['stance'],'THEO DÕI')

    def test_latest_interim_decline_prevents_buy_based_on_old_annual_growth(self):
        r=self.fixture();r['interim']=dict(valid=True,period_end='2026-06-30',fields={'parent_profit':{'value':5,'previous':10}})
        recommendation=build_recommendation(r)
        self.assertEqual(recommendation['stance'],'THEO DÕI');self.assertIn('bán niên',recommendation['reason'])

    def test_older_interim_cannot_override_more_recent_annual(self):
        r=self.fixture();r['interim']=dict(valid=True,period_end='2025-06-30',fields={'parent_profit':{'value':5,'previous':10}})
        self.assertIn('TÍCH LŨY',build_recommendation(r)['stance'])

    def test_prior_year_or_empty_checks_do_not_verify_current_financials(self):
        for checks in [[], [dict(metric='net_profit',period='2024',match=True)],
                       [dict(metric='net_profit',period='2025',match=False)]]:
            r=self.fixture();r['quality']['financial_check']['checks']=checks
            recommendation=build_recommendation(r)
            self.assertEqual(recommendation['stance'],'THEO DÕI')
            self.assertEqual(recommendation['confidence'],'Thấp')

    def test_invalid_primary_target_blocks_instead_of_crashing(self):
        for target in [None,0,float('nan'),float('inf')]:
            r=self.fixture();r['valuation']['primary']['target_price_vnd']=target
            self.assertEqual(build_recommendation(r)['stance'],'CHƯA ĐỦ CƠ SỞ KHUYẾN NGHỊ')

    def test_invalid_market_price_blocks_instead_of_crashing(self):
        for price in [None,0,float('nan'),float('inf')]:
            r=self.fixture();r['market']['latest_close_vnd']=price
            self.assertEqual(build_recommendation(r)['stance'],'CHƯA ĐỦ CƠ SỞ KHUYẾN NGHỊ')
    def test_missing_latest_stale_financials_or_single_method_blocks(self):
        for kind in ['price','financial','method','stale_price']:
            r=self.fixture()
            if kind=='price':r['quality']['price_check']['checks']=[]
            elif kind=='financial':r['financial']['periods'][0]['year']=2024
            elif kind=='method':r['valuation']['primary']['available']=False
            else:r['request']['as_of']='2026-10-20'
            self.assertEqual(build_recommendation(r)['stance'],'CHƯA ĐỦ CƠ SỞ KHUYẾN NGHỊ')
    def test_weak_cash_or_expensive_scenario_prioritizes_risk(self):
        for kind in ['cash','price']:
            r=self.fixture()
            if kind=='cash':next(m for m in r['financial']['metrics'] if m['key']=='cfo')['value']=-1
            else:r['valuation']['primary']['target_price_vnd']=16000
            self.assertEqual(build_recommendation(r)['stance'],'ƯU TIÊN QUẢN TRỊ RỦI RO')
    def test_models_divergent_or_one_below_price_cannot_recommend_buy(self):
        r=self.fixture();r['valuation']['primary']['methods'][0]['target_price_vnd']=10000
        self.assertEqual(build_recommendation(r)['stance'],'THEO DÕI')
    def test_pdf_narrative_in_right_column_and_recommendation_visible(self):
        import pymupdf
        r=self.fixture();r['market']=None;r['recommendation']=build_recommendation(r)
        with TemporaryDirectory() as d:
            pdf=generate_report(r,Path(d)/'columns.pdf')
            with pymupdf.open(pdf) as doc:
                texts=[];locations=[]
                for page in doc:
                    locations.extend(page.search_for('Khuyến nghị và luận điểm đầu tư'))
                    for block in page.get_text('blocks'):
                        texts.append(block[4])
                self.assertTrue(locations)
                for rect in locations:self.assertGreaterEqual(rect.x0,80*72/25.4-1)
                self.assertIn(r['recommendation']['stance'],' '.join(texts))


if __name__=='__main__':unittest.main()
