from copy import deepcopy
from datetime import date,datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from src.data.near_period_pb import select_balance_period
from src.data.valuation_peers import collect_valuation_peers
from test_valuation_upgrade import financial
from src.analysis.investment_valuation import investment_valuation
from test_valuation_upgrade import value,market

ASOF=date(2026,10,13)


class NearPeriodPbTests(unittest.TestCase):
    def test_prior_balance_requires_attributable_equity_same_scope_and_90_days(self):
        p=financial()['periods'][0]
        target=dict(period_end='2026-03-31',scope=p['scope'],business_type=p['business_type'])
        self.assertIsNotNone(select_balance_period([p],target,ASOF))
        for key,value in [('period_end','2025-12-30'),('period_end','2026-04-01'),('scope','parent'),('business_type',3)]:
            wrong=deepcopy(p);wrong[key]=value
            with self.subTest(key=key,value=value):self.assertIsNone(select_balance_period([wrong],target,ASOF))
        wrong=deepcopy(p);wrong['fields']['non_controlling_equity']['value']=None
        self.assertIsNone(select_balance_period([wrong],target,ASOF))
        wrong=deepcopy(p);wrong['fields']['equity']['value']=1
        self.assertIsNone(select_balance_period([wrong],target,ASOF))

    def setup_sources(self):
        industry=dict(name='Fixture',period_end='2026-03-31',scope='consolidated',
                      peers=[dict(ticker=t,financial=financial()) for t in ['AAA','BBB']])
        def profile(url,**kw):return json.dumps(dict(SB=url.split('/')[-1].split('?')[0],KLCPLH=10e6)).encode()
        quote=dict(rows=[dict(date='2026-10-12',close=20000)],raw=b'{}',url='https://example.test/quote',retrieved_at=ASOF.isoformat())
        return industry,profile,quote

    def test_missing_yahoo_date_uses_vietcap_but_never_calculates_near_period_pe(self):
        industry,profile,quote=self.setup_sources()
        with TemporaryDirectory() as temp,patch('src.data.valuation_peers.datetime') as clock, \
             patch('src.data.valuation_peers.download',side_effect=profile), \
             patch('src.data.valuation_peers.fetch_daily_prices',return_value={**quote,'rows':[]}), \
             patch('src.data.valuation_peers.fetch_vietcap_prices',return_value=quote) as fallback, \
             patch('src.data.valuation_peers.fetch_kbs_prices',return_value=quote):
            clock.now.return_value=datetime(2026,10,13)
            out=collect_valuation_peers(industry,ASOF,'2026-10-12',Path(temp),'test',period_policy='prior_balance_90_days')
        self.assertTrue(out['available']);self.assertFalse(out['usable_in_primary'])
        self.assertEqual(out['pb_sample_size'],2);self.assertEqual(out['pe_sample_size'],0)
        self.assertEqual(fallback.call_count,2)
        self.assertTrue(all(p['pe'] is None and p['period_gap_days']==90 for p in out['peers']))

    def test_exact_mode_still_rejects_near_period_before_network(self):
        industry,_,_=self.setup_sources()
        with TemporaryDirectory() as temp,patch('src.data.valuation_peers.datetime') as clock,patch('src.data.valuation_peers.download') as network:
            clock.now.return_value=datetime(2026,10,13)
            out=collect_valuation_peers(industry,ASOF,'2026-10-12',Path(temp),'test')
        self.assertFalse(out['available']);network.assert_not_called()

    def test_near_reference_cannot_create_primary_target(self):
        f=financial();v=value(f);v['near_period_pb']=dict(available=True,reference_price_vnd=999999)
        primary=investment_valuation(f,market(),v,{})
        self.assertFalse(primary['available']);self.assertIsNone(primary['target_price_vnd'])
