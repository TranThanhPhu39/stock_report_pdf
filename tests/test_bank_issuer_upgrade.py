"""Original bank PDFs supply period metadata; vendor labels are never repaired."""
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.data.bank_issuer import (REQUIRED, amount_pair, parse_bank_pages,
                                  compare_bank_values, collect_bank_issuer)
from src.data.normalize import FIELD_IDS, parse_annual_financials
from src.data.providers import DataSourceError
from src.data.industry import collect_industry
from src.analysis.ai_commentary import evidence_bundle
from src.analysis.conclusion import build_conclusion
from src.analysis.financial import analyze_financials
from src.analysis.recommendation import build_recommendation
import test_exchange_recommendation as exchange

ASOF = date(2026,10,12)
RAW = b'Pinned bank PDF fixture'


def manifest():
    return dict(year=2025,period_end='2025-12-31',period_type='annual',available_at='2026-10-12',
                availability_basis='first_verified_public_availability_upper_bound',
                availability_note='Only available after first verified date; publication unknown.',
                hosting='Public disclosure archive',identity='ngan hang quan doi',assurance_label='kiem toan doc lap',
                unit_multiplier=1_000_000,url='https://example.test/mbb.pdf',sha256=hashlib.sha256(RAW).hexdigest(),
                pages=[dict(page=i,kind=k) for i,k in enumerate(REQUIRED,1)],
                headers={k:['hop nhat','trieu dong','2025','2024'] for k in REQUIRED},
                column_headers={k:'2025 2024' for k in REQUIRED})


def pages():
    def row(label,current,prior):return f'{label} {current:,} {prior:,}'
    header='Ngân hàng Quân đội\nKiểm toán độc lập\nHợp nhất\n2025 2024\nTriệu đồng\n'
    return [dict(page=1,kind='balance',text=header+'\n'.join([
        row('Tổng tài sản',1_000_000,800_000),row('Tổng nợ phải trả',900_000,720_000),
        row('Tổng vốn chủ sở hữu',100_000,80_000),row('Lợi ích cổ đông không kiểm soát',5_000,4_000)])),
        dict(page=2,kind='income',text=header+'\n'.join([
        row('Thu nhập lãi thuần',50_000,40_000),row('Lợi nhuận sau thuế',20_000,15_000),
        row('Lợi nhuận sau thuế thuộc về Ngân hàng mẹ',19_000,14_000),
        row('Lợi ích cổ đông không kiểm soát',1_000,1_000),row('Tổng lợi nhuận trước thuế',25_000,18_000)])),
        dict(page=3,kind='cashflow',text=header+'Lưu chuyển tiền thuần từ hoạt động kinh doanh (30,000) 10,000')]


def snapshots(fields):
    result={}
    for kind in REQUIRED:
        result[kind]=dict(Head=[dict(ID=1,YearPeriod=2025,United='HN',TermCode='N',BusinessType=3,
            DatePubDepartment='2026-03-10',LastUpdate='2026-03-14',PeriodBegin='202501',PeriodEnd='202612')],
            Content={'rows':[dict(ReportNormID=next(i for i,k in FIELD_IDS[kind].items() if k==key),
                                 Value1=v['value']/1000) for key,v in fields[kind].items() if key in REQUIRED[kind]]})
    return result


class BankStatementTests(unittest.TestCase):
    def parse(self,p=None,m=None):return parse_bank_pages(p or pages(),m or manifest(),'BANK_fixture')

    def test_units_parent_equity_and_negative_cashflow(self):
        f=self.parse()
        self.assertEqual(f['balance']['assets']['value'],1_000_000_000_000)
        self.assertEqual(f['cashflow']['cfo']['value'],-30_000_000_000)
        self.assertEqual(f['income']['parent_profit']['value'],19_000_000_000)
        self.assertIsNone(f['balance']['assets']['published_at'])
        self.assertEqual(f['balance']['assets']['available_at'],'2026-10-12')

    def test_wrong_issuer_scope_currency_assurance_or_columns_rejected(self):
        for old,new in [('Quân đội','Khác'),('Hợp nhất','Riêng lẻ'),('Triệu đồng','USD'),
                        ('Kiểm toán độc lập','Chưa kiểm toán'),('2025 2024','2024 2025')]:
            with self.subTest(old=old):
                p=pages()
                for page in p:page['text']=page['text'].replace(old,new)
                with self.assertRaises(DataSourceError):self.parse(p)

    def test_current_and_comparative_balance_must_reconcile(self):
        for old,new in [('1,000,000','1,001,000'),('800,000','801,000')]:
            p=pages();p[0]['text']=p[0]['text'].replace(old,new)
            with self.assertRaisesRegex(DataSourceError,'không cân bằng'):self.parse(p)

    def test_parent_profit_allocation_must_reconcile(self):
        p=pages();p[1]['text']=p[1]['text'].replace('19,000','18,000')
        with self.assertRaisesRegex(DataSourceError,'LNST'):self.parse(p)

    def test_missing_nci_and_conflicting_rows_rejected(self):
        p=pages();p[0]['text']='\n'.join(s for s in p[0]['text'].splitlines() if 'kiểm soát' not in s)
        with self.assertRaisesRegex(DataSourceError,'thiếu dòng'):self.parse(p)
        p=pages();p[0]['text']+='\nTổng vốn chủ sở hữu 101,000 80,000'
        with self.assertRaisesRegex(DataSourceError,'nhiều dòng'):self.parse(p)

    def test_punctuation_in_labels_does_not_repair_numbers(self):
        p=pages();p[0]['text']=p[0]['text'].replace('Tổng nợ','Tổng nợ’')
        self.assertEqual(self.parse(p)['balance']['liabilities']['value'],900_000_000_000)
        self.assertIsNone(amount_pair('(30,000 10,000'))
        self.assertIsNone(amount_pair('30,O00 10,000'))

    def test_numeric_check_cannot_relabel_invalid_vendor_period(self):
        f=self.parse();raw=snapshots(f);original=deepcopy(raw)
        checks=compare_bank_values(f,raw,manifest(),'BANK_fixture','run')
        self.assertEqual(len(checks),9);self.assertTrue(all(c['match'] for c in checks))
        self.assertEqual(raw,original)
        # Give the strict parser a valid four-column contract, but an invalid end.
        data=raw['balance'];data['Head'] += [dict(data['Head'][0],ID=i,YearPeriod=2026-i) for i in [2,3,4]]
        self.assertFalse(parse_annual_financials(data,'balance',ASOF,'KBS_fixture'))

    def test_mismatched_missing_or_wrong_scope_vendor_cannot_promote_pdf(self):
        for kind in ['mismatch','missing','scope','type']:
            f=self.parse();raw=snapshots(f)
            if kind=='mismatch':raw['cashflow']['Content']['rows'][0]['Value1']+=10_000
            if kind=='missing':raw.pop('cashflow')
            if kind=='scope':raw['balance']['Head'][0]['United']='CTM'
            if kind=='type':raw['balance']['Head'][0]['BusinessType']=1
            with self.assertRaises(DataSourceError):compare_bank_values(f,raw,manifest(),'BANK_fixture','run')

    def test_pinned_units_and_future_end_rejected(self):
        for key,value in [('unit_multiplier',1000),('period_end','2026-12-31')]:
            m=manifest();m[key]=value
            with self.assertRaises(DataSourceError):self.parse(m=m)


class BankCollectionTests(unittest.TestCase):
    def collect(self,entries=None,asof=ASOF,bad_checksum=False,interim_error=False):
        m=manifest();p=pages();f=parse_bank_pages(p,m,'BANK_fixture')
        with TemporaryDirectory() as directory:
            root=Path(directory);(root/'config').mkdir()
            (root/'config/bank_issuer_sources.json').write_text(json.dumps({'MBB':entries or [m]}),encoding='utf-8')
            def read(path,root,manifest):
                if interim_error and manifest['period_type']=='half_year':raise DataSourceError('Interim OCR unclear')
                return p
            with patch('src.data.bank_issuer.cached_file',return_value=(b'changed' if bad_checksum else RAW,{'retrieved_at':'2026-10-12'})) as fetch,patch('src.data.bank_issuer.read_bank_pages',side_effect=read):
                output=collect_bank_issuer('MBB',asof,root,'run',snapshots(f))
        return output,fetch

    def test_collect_promotes_original_year_and_its_comparative(self):
        r,_=self.collect();self.assertTrue(r['available']);self.assertEqual(len(r['checks']),9)
        f=analyze_financials(r['records']);self.assertEqual([p['year'] for p in f['periods']],[2025,2024])
        self.assertEqual(f['industry_group'],'bank')
        self.assertEqual(f['periods'][1]['fields']['assets']['source_value'],800_000)

    def test_historical_date_never_uses_later_first_verified_document(self):
        r,fetch=self.collect(asof=date(2026,10,11))
        self.assertFalse(r['available']);fetch.assert_not_called()

    def test_changed_checksum_not_promoted(self):
        r,_=self.collect(bad_checksum=True)
        self.assertFalse(r['available']);self.assertFalse(r['records'])
        self.assertIn('checksum',r['errors'][0]['message'])

    def test_interim_failure_preserves_verified_annual(self):
        h=dict(manifest(),period_type='half_year',period_end='2026-06-30',year=2026)
        r,_=self.collect(entries=[manifest(),h],interim_error=True)
        self.assertTrue(r['available']);self.assertIsNone(r['interim'])
        self.assertEqual(r['errors'][0]['stage'],'bank_interim')


class BankNarrativeTests(unittest.TestCase):
    def fixture(self):
        r=exchange.RecommendationTests().fixture();r['financial']['industry_group']='bank'
        r['market'].update(ma50_vnd=None,max_drawdown_pct=None)
        fields=parse_bank_pages(pages(),manifest(),'BANK_fixture')
        r['interim']=dict(valid=True,ticker='MBB',period_end='2026-06-30',fields={k:v for group in fields.values() for k,v in group.items()})
        return r

    def test_bank_interim_uses_interest_income_without_revenue_or_doubling(self):
        r=self.fixture()
        conclusion=build_conclusion(r['financial'],r['market'],r['valuation'],r['quality']['price_check'],r['interim'])
        self.assertTrue(any('thu nhập lãi thuần' in s for s in conclusion['opportunities']))
        recommendation=build_recommendation(r)
        self.assertTrue(any(s['title']=='Cập nhật kết quả bán niên' for s in recommendation['opportunities']))

    def test_ai_bundle_keeps_flow_and_stock_periods_separate(self):
        r=self.fixture();b=evidence_bundle(r)
        interim=[e for e in b['evidence'] if e['id'].startswith('H')]
        flows=[e for e in interim if 'Thu nhập' in e['label']]
        self.assertEqual(flows[0]['period'],'2026-01-01 / 2026-06-30')
        self.assertEqual(flows[0]['previous_period'],'2025-01-01 / 2025-06-30')
        stocks=[e for e in interim if 'Tổng tài sản' in e['label']]
        self.assertEqual(stocks[0]['previous_period'],'2025-12-31')

    def test_optional_interim_cannot_bypass_recommendation_price_gate(self):
        r=self.fixture();r['quality']['price_check']['checks']=[]
        self.assertEqual(build_recommendation(r)['stance'],'CHƯA ĐỦ CƠ SỞ KHUYẾN NGHỊ')


class BankIndustryTests(unittest.TestCase):
    def collect(self,fail=False):
        issuer,_=BankCollectionTests().collect()
        own=analyze_financials(issuer['records'])
        older=[r for r in issuer['records'] if r['year']==2024]
        universe=dict(groups=[dict(code='banks',name='Banks',symbols=['MBB','CTG','TCB'],url='https://example.test')],
                      taxonomy='KBS',complete=True,retrieved_at='2026-10-12',retrieval_mode='fixture')
        def bank(symbol,asof,root,run,snapshots,**kwargs):
            if fail:raise OSError('Original PDF temporarily unavailable')
            result=deepcopy(issuer)
            sid=f'BANK_{symbol}_{run}'
            for r in result['records']:
                r['source_id']=sid
                for f in r['fields'].values():f['source_id']=sid
            result['sources']=[dict(source_id=sid,url_or_file='https://example.test',retrieved_at='2026-10-12',page_or_table='PDF',notes='Fixture')]
            result['sources'] += [dict(source_id=key,url_or_file='https://example.test',retrieved_at='2026-10-12',page_or_table='KBS',notes='Fixture') for key in kwargs['reference_source_ids'].values()]
            return result
        with TemporaryDirectory() as directory,patch('src.data.industry.collect_universe',return_value=universe),\
             patch('src.data.industry.download',return_value=b'{}'),\
             patch('src.data.industry.parse_annual_financials',side_effect=lambda p,k,*args:[r for r in older if r['kind']==k]),\
             patch('src.data.industry.collect_bank_issuer',side_effect=bank) as source:
            result=collect_industry('MBB',ASOF,own,Path(directory),'run')
        return result,source

    def test_verified_bank_peers_supply_same_year_and_source_check_records(self):
        r,source=self.collect()
        self.assertEqual(r['period_end'],'2025-12-31')
        self.assertEqual({p['ticker'] for p in r['peers']},{'CTG','TCB'})
        self.assertTrue(all(len(p['issuer_checks'])==9 for p in r['peers']))
        self.assertEqual(source.call_count,2)
        self.assertIn('PEER_CTG_income_run',{s['source_id'] for s in r['sources']})

    def test_original_source_failure_preserves_valid_older_vendor_periods(self):
        r,_=self.collect(fail=True)
        self.assertEqual(r['period_end'],'2024-12-31')
        self.assertEqual(len(r['peers']),2)
        self.assertTrue(any('Original PDF' in s for p in r['peers'] for s in p['warnings']))
