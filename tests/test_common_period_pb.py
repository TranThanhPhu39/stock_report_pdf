from copy import deepcopy
from datetime import date
import hashlib,json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from src.data.common_period_pb import valid_balance,collect_common_period_pb
from src.data.tch_issuer import balance_snapshot_record
from src.data.providers import DataSourceError
from src.analysis.investment_valuation import investment_valuation
from src.analysis.decision import decision_summary
from test_valuation_upgrade import financial,value,market

ROOT=Path(__file__).resolve().parents[1]
ASOF=date(2026,10,13)


class CommonPeriodPbTests(unittest.TestCase):
    def snapshot(self):
        data=json.loads((ROOT/'config/issuer_snapshots/TCH_2025_Q3_balance.json').read_text(encoding='utf-8'))
        content=b'%PDF-test';data['sha256']=hashlib.sha256(content).hexdigest()
        return data,content

    def test_snapshot_is_interim_balance_only_and_checksum_dated(self):
        data,content=self.snapshot();p=balance_snapshot_record(data,content,ASOF,'issuer')
        self.assertEqual(p['period_end'],'2025-12-31');self.assertEqual(p['basis'],'interim_balance')
        self.assertNotIn('parent_profit',p['fields'])
        self.assertEqual(p['fields']['equity']['value']-p['fields']['non_controlling_equity']['value'],11431959862100)
        for changed,raw,asof in [(data,content+b'changed',ASOF),(data,content,date(2026,1,28)),({**data,'scope':'parent'},content,ASOF)]:
            with self.assertRaises(DataSourceError):balance_snapshot_record(changed,raw,asof,'issuer')

    def test_invalid_balance_scope_nci_unit_and_identity_are_rejected(self):
        data,content=self.snapshot();p=balance_snapshot_record(data,content,ASOF,'issuer')
        for key,replacement in [('assets',1),('non_controlling_equity',None),('equity',float('inf'))]:
            wrong=deepcopy(p);wrong['fields'][key]['value']=replacement
            self.assertFalse(valid_balance(wrong,'consolidated',1))
        wrong=deepcopy(p);wrong['fields']['equity']['unit']='thousand VND'
        self.assertFalse(valid_balance(wrong,'consolidated',1))
        self.assertFalse(valid_balance(p,'parent',1));self.assertFalse(valid_balance(p,'consolidated',3))

    def common(self):
        p=financial()['periods'][0];p['basis']='interim_balance'
        for field in p['fields'].values():field['unit']='VND'
        benchmark=dict(period_end=p['period_end'],scope=p['scope'],price_date=market()['latest_date'],
                       period_policy='exact_balance',median_pb=1.5,pb_sample_size=2,
                       peers=[dict(ticker=t,equity_period=p['period_end'],price_date=market()['latest_date'],pb=1.5,pe=None,
                                   inputs=[dict(source_id=t+'_balance')]) for t in ['AAA','BBB']])
        return dict(available=True,period=p,benchmark=benchmark)

    def test_primary_uses_own_same_date_equity_without_annual_profit_or_latest_overwrite(self):
        f=financial();f['periods'][0]['period_end']='2026-03-31';v=value(f)
        common=self.common();primary=investment_valuation(f,market(),v,{},common_pb=common)
        self.assertTrue(primary['available']);self.assertEqual(primary['period_end'],'2025-12-31')
        self.assertEqual([m['key'] for m in primary['methods']],['pb'])
        self.assertEqual(f['periods'][0]['period_end'],'2026-03-31')
        capital=common['period']['fields']['equity']['value']-common['period']['fields']['non_controlling_equity']['value']
        self.assertAlmostEqual(primary['target_price_vnd'],capital/v['shares']*1.5)
        summary=decision_summary(dict(financial=f,valuation=dict(primary=primary)))
        self.assertIn('2025-12-31',summary['annual_basis'])

    def test_mismatched_peer_dates_scope_price_and_small_sample_never_create_primary(self):
        f=financial();f['periods'][0]['period_end']='2026-03-31';v=value(f)
        for key,replacement in [('period_end','2026-03-31'),('scope','parent'),('price_date','2026-10-09'),('pb_sample_size',1),('period_policy','prior_balance_90_days')]:
            common=self.common();common['benchmark'][key]=replacement
            self.assertFalse(investment_valuation(f,market(),v,{},common_pb=common)['available'])
        common=self.common();common['benchmark']['peers'][0]['equity_period']='2026-03-31'
        self.assertFalse(investment_valuation(f,market(),v,{},common_pb=common)['available'])

    def test_collector_selects_latest_available_common_balance_and_rejects_future_snapshot(self):
        f=financial();f['periods'][0]['period_end']='2026-03-31';v=value(f)
        f['periods'][0]['published_at']='2026-06-26'
        for field in f['periods'][0]['fields'].values():field['unit']='VND'
        data,content=self.snapshot();p=balance_snapshot_record(data,content,ASOF,'issuer')
        peer=deepcopy(p);peer['fields']['assets']['source_id']='peer'
        benchmark=self.common()['benchmark'];benchmark['available']=True;benchmark['sources']=[]
        industry=dict(available=True,name='Fixture',members=['TCH','AAA','BBB'])
        quote=dict(status='matched',checks=[dict(date=market()['latest_date'],match=True,primary_close=market()['latest_close_vnd'],reference_close=market()['latest_close_vnd'])])
        with TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'data/raw/industry';folder.mkdir(parents=True)
            for ticker in ['AAA','BBB']:(folder/f'PEER_{ticker}_balance_test.json').write_text('{}')
            with patch('src.data.common_period_pb.parse_annual_financials',return_value=[peer]),patch('src.data.common_period_pb.collect_valuation_peers',return_value=benchmark) as collect:
                out=collect_common_period_pb('TCH',ASOF,f,[p],industry,v,market(),quote,root,'test')
                self.assertTrue(out['available']);self.assertEqual(out['period']['period_end'],'2025-12-31')
                self.assertEqual(out['attempts'][0]['candidate_count'],0)
                self.assertEqual(collect.call_args.kwargs['period_policy'],'exact_balance')
                future={**p,'published_at':'2026-10-14'}
                self.assertFalse(collect_common_period_pb('TCH',ASOF,f,[future],industry,v,market(),quote,root,'test')['available'])

    def test_primary_blocker_explains_dcf_and_does_not_require_project_model(self):
        f=financial();v=value(f);v['dcf']=dict(available=False,reason='Thiếu lãi vay đã trả.')
        out=investment_valuation(f,market(),v,{})
        self.assertIn('DCF toàn doanh nghiệp',out['reason']);self.assertIn('lãi vay',out['reason'])

    def test_exact_balance_quote_collector_never_creates_pe_from_profit(self):
        from src.data.valuation_peers import collect_valuation_peers
        from test_near_period_pb import NearPeriodPbTests
        from datetime import datetime
        industry,profile,quote=NearPeriodPbTests().setup_sources()
        industry['period_end']='2025-12-31'
        with TemporaryDirectory() as temp,patch('src.data.valuation_peers.datetime') as clock,patch('src.data.valuation_peers.download',side_effect=profile),patch('src.data.valuation_peers.fetch_daily_prices',return_value=quote),patch('src.data.valuation_peers.fetch_kbs_prices',return_value=quote):
            clock.now.return_value=datetime(2026,10,13)
            out=collect_valuation_peers(industry,ASOF,'2026-10-12',Path(temp),'test',period_policy='exact_balance')
        self.assertTrue(out['available']);self.assertEqual(out['pe_sample_size'],0)
        self.assertTrue(all(p['pe'] is None and p['period_gap_days']==0 for p in out['peers']))
