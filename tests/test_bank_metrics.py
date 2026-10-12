"""Reject wrong scopes/periods and distinguish reported bank ratios from calculations."""
from copy import deepcopy
from datetime import date
import unittest

from src.analysis.bank_metrics import trailing_profit, attach_bank_metrics
from src.analysis.valuation import analyze_valuation
from src.analysis.conclusion import build_conclusion
from src.analysis.ai_commentary import evidence_bundle
from src.data.bank_ratios import parse_mbb_ratios
from src.data.bank_issuer import parse_bank_pages
from src.data.providers import DataSourceError
import test_exchange_recommendation as exchange
import test_bank_issuer_upgrade as issuer_tests

ASOF=date(2026,10,12)


def ratio_fixture():
    m=dict(year=2025,period_end='2025-12-31',period_type='annual',available_at='2026-10-12',
        availability_basis='first_verified_public_availability_upper_bound',
        ratio_pages={'table':{'page':46,'side':0},'nim_scope':{'page':58,'side':1},
                     'car_scope':{'page':67,'side':1},'loans':{'page':161,'side':0}})
    p=dict(table='''Các chỉ tiêu tài chính chủ yếu của MB trong năm 2025
Đơn vị: tỷ VND
Chỉ tiêu Năm 2024 Năm 2025 % Tăng/(Giảm)
- Vốn chủ sở hữu 117.060 142.023 21,3%
- Tổng Tài sản 1.128.801 1.615.764 43,1%
- Tỷ lệ an toàn vốn (CAR) 11,8% 11,0% (6,3%)
- Tỷ lệ nợ xấu / Tổng dư nợ 1,6% 1,3% (20%) Tích cực
- Tỷ lệ thu nhập lãi thuần (NIM) 4,2% 3,9% (7,1%)''',
        nim_scope='NIM năm 2025 đạt 3,9%. Nguồn: BCTC hợp nhất các ngân hàng',
        car_scope='Năm 2025 CAR hợp nhất đạt 11,0%.',
        loans='''Báo cáo tài chính hợp nhất đã kiểm toán
9.1 Phân tích chất lượng nợ cho vay
31/12/2025 31/12/2024 triệu đồng
Nợ đủ tiêu chuẩn 1.044.741.249 741.581.903
Nợ cần chú ý 10.210.040 12.196.782
Nợ dưới tiêu chuẩn 3.276.216 3.379.646
Nợ nghi ngờ 4.330.016 4.599.274
Nợ có khả năng mất vốn 6.421.264 4.606.512
Các khoản cho vay giao dịch ký quỹ và 15.040.585 10.293.729
ứng trước cho khách hàng giao dịch đầu tư chứng khoán – Nợ đủ tiêu chuẩn
1.084.019.370 776.657.846''')
    fields={'balance':{'equity':dict(value=142022525e6,previous=117060000e6),
                       'assets':dict(value=1615763927e6,previous=1128801000e6)}}
    return p,m,fields


def trailing_fixture():
    def field(value,previous=None,annual=False):
        return dict(value=value*1e6,previous=previous*1e6 if previous is not None else None,
            statement_scope='consolidated',unit='VND',source_id='ANNUAL' if annual else 'HALF',
            available_at='2026-10-12',period='2025' if annual else '2026-06-30',unit_multiplier=1e6)
    f=dict(periods=[dict(year=2025,period_end='2025-12-31',scope='consolidated',fields={
        'parent_profit':field(26778939,annual=True),'net_profit':field(27382978,annual=True),
        'non_controlling_profit':field(604039,annual=True),'net_interest_income':field(51610117,annual=True)})],
        metrics=[],errors=[],industry_group='bank')
    h=dict(valid=True,period_type='half_year',period_begin='2026-01-01',period_end='2026-06-30',fields={
        'parent_profit':field(15744575,12445345),'net_profit':field(16148193,12679585),
        'non_controlling_profit':field(403618,234240),'net_interest_income':field(31806771,24064301)})
    return f,h


class ReportedBankRatioTests(unittest.TestCase):
    def test_nci_printed_deduction_is_not_a_loss(self):
        p=issuer_tests.pages();m=issuer_tests.manifest()
        p[1]['text']=p[1]['text'].replace('1,000 1,000','(1,000) (1,000)')
        m['profit_allocation_convention']='deduction_to_parent'
        r=parse_bank_pages(p,m,'BANK')
        self.assertEqual(r['income']['non_controlling_profit']['value'],1e9)
        self.assertEqual(r['income']['non_controlling_profit']['source_value'],-1000)
        # A negative actual NCI loss keeps its sign when no deduction contract exists.
        m.pop('profit_allocation_convention')
        p[1]['text']=p[1]['text'].replace('19,000 14,000','21,000 16,000')
        r=parse_bank_pages(p,m,'BANK')
        self.assertEqual(r['income']['non_controlling_profit']['value'],-1e9)

    def test_reported_columns_and_audited_loan_calculation(self):
        p,m,f=ratio_fixture();r=parse_mbb_ratios(p,m,f,'BANK')
        self.assertEqual((r['metrics']['nim']['value'],r['metrics']['nim']['previous']),(3.9,4.2))
        self.assertEqual(r['metrics']['car']['value'],11)
        self.assertAlmostEqual(r['metrics']['npl']['value'],14027496/1084019370*100)
        self.assertEqual(r['metrics']['npl']['reported_value'],1.3)
        self.assertEqual(r['metrics']['npl']['reported_source']['page'],46)
        self.assertEqual(r['metrics']['npl']['page'],161)
        self.assertEqual(r['gross_loans']['value'],1084019370e6)
        self.assertTrue(all(c['valid'] for c in r['checks']))

    def test_wrong_columns_currency_year_bank_or_balances_rejected(self):
        for old,new in [('Năm 2024 Năm 2025','Năm 2025 Năm 2024'),('tỷ VND','USD'),
                        ('của MB','của KHAC'),('142.023','143.023')]:
            p,m,f=ratio_fixture();p['table']=p['table'].replace(old,new)
            with self.subTest(old=old),self.assertRaises(DataSourceError):parse_mbb_ratios(p,m,f,'BANK')

    def test_scope_and_numeric_corroboration_required(self):
        for key,old,new in [('nim_scope','hợp nhất','riêng lẻ'),('nim_scope','3,9%','4,0%'),
                            ('car_scope','hợp nhất','riêng lẻ'),('car_scope','11,0%','11,1%'),
                            ('loans','hợp nhất','riêng lẻ'),('loans','triệu đồng','tỷ đồng')]:
            p,m,f=ratio_fixture();p[key]=p[key].replace(old,new)
            with self.subTest(key=key,new=new),self.assertRaises(DataSourceError):parse_mbb_ratios(p,m,f,'BANK')

    def test_loan_totals_negative_group_and_missing_group_rejected(self):
        for old,new in [('1.084.019.370','1.084.019.371'),('3.276.216','(3.276.216)'),
                        ('Nợ nghi ngờ','Không có nhóm 4'),('1,3%','1,8%'),
                        ('31/12/2025 31/12/2024','31/12/2024 31/12/2025')]:
            p,m,f=ratio_fixture()
            for key in ('table','loans'):p[key]=p[key].replace(old,new)
            with self.subTest(old=old),self.assertRaises(DataSourceError):parse_mbb_ratios(p,m,f,'BANK')

    def test_duplicate_and_out_of_range_ratios_rejected(self):
        for change in ('duplicate','range'):
            p,m,f=ratio_fixture()
            p['table']=p['table']+'\n'+p['table'].splitlines()[-1] if change=='duplicate' else p['table'].replace('3,9%','103,9%')
            with self.assertRaises(DataSourceError):parse_mbb_ratios(p,m,f,'BANK')


class TrailingBankProfitTests(unittest.TestCase):
    def test_annual_plus_current_minus_latest_comparative(self):
        f,h=trailing_fixture();t=trailing_profit(f,h,ASOF)
        self.assertTrue(t['available'])
        self.assertEqual((t['period_begin'],t['period_end']),('2025-07-01','2026-06-30'))
        self.assertEqual(t['fields']['parent_profit']['value'],30078169e6)
        self.assertEqual(t['fields']['net_profit']['value'],30851586e6)
        comparative=t['fields']['parent_profit']['inputs'][2]
        self.assertEqual(comparative['source_id'],'HALF')
        self.assertEqual(comparative['period_end'],'2025-06-30')
        self.assertEqual(comparative['value'],12445345e6)

    def test_wrong_scope_unit_availability_or_period_blocks_ttm(self):
        for key,value in [('statement_scope','separate'),('unit','USD'),('available_at','2026-10-13'),
                          ('available_at',None),('available_at','2025xxx'),('source_id',None),('period','2024'),('period',None)]:
            f,h=trailing_fixture();f['periods'][0]['fields']['parent_profit'][key]=value
            with self.subTest(key=key):self.assertFalse(trailing_profit(f,h,ASOF)['available'])

    def test_missing_annual_or_invalid_interim_blocks(self):
        for change in ('missing','future','quarter','wrong_end','invalid'):
            f,h=trailing_fixture()
            if change=='missing':f['periods'][0]['year']=2024
            if change=='future':h['period_end']='2027-06-30'
            if change=='quarter':h['period_type']='quarter'
            if change=='wrong_end':h['period_end']='2026-03-31'
            if change=='invalid':h['valid']=False
            with self.subTest(change=change):self.assertFalse(trailing_profit(f,h,ASOF)['available'])

    def test_missing_or_mismatched_profit_allocation_each_column(self):
        for location in ('annual','current','comparative'):
            f,h=trailing_fixture()
            if location=='annual':f['periods'][0]['fields'].pop('non_controlling_profit')
            else:h['fields']['non_controlling_profit']['value' if location=='current' else 'previous']+=2e6
            with self.subTest(location=location):self.assertFalse(trailing_profit(f,h,ASOF)['available'])

    def test_dynamic_missing_ratios_and_nonbank_unchanged(self):
        f,h=trailing_fixture();r=attach_bank_metrics(f,None,h,ASOF)
        self.assertTrue(r['ttm']['available'])
        self.assertEqual([m['value'] for m in r['metrics']],[None]*3)
        self.assertIn('NIM, NPL, CAR',r['errors'][-1])
        f,h=trailing_fixture();f['industry_group']='securities'
        self.assertNotIn('ttm',attach_bank_metrics(f,None,h,ASOF))

    def test_ratios_remove_false_missing_risk_and_supply_ai_evidence(self):
        p,m,annual=ratio_fixture();ratios=parse_mbb_ratios(p,m,annual,'BANK')
        f,h=trailing_fixture();attach_bank_metrics(f,ratios,h,ASOF)
        self.assertFalse(f['errors'])
        c=build_conclusion(f,None,{}, {})
        self.assertFalse(any('Chưa xác minh NIM' in r['evidence'] for r in c['risk_matrix']))
        b=evidence_bundle(dict(financial=f,request=dict(ticker='MBB',as_of=ASOF.isoformat()),
            status='analyzed',quality={'warnings':[]},sources=[]))
        self.assertTrue(any(r['label']=='LNST cổ đông mẹ TTM' and r['source_ids']==['ANNUAL','HALF'] for r in b['evidence']))

    def test_pe_ttm_does_not_replace_annual_or_bypass_price_gate(self):
        result=exchange.RecommendationTests().fixture()
        t,h=trailing_fixture();result['financial']['ttm']=trailing_profit(t,h,ASOF)
        company=dict(outstanding_shares=1e9,snapshot_at=ASOF.isoformat(),source_id='CP')
        val=analyze_valuation(result['financial'],result['market'],company,result['quality']['price_check'],ASOF)
        self.assertTrue(val['pe_ttm']['available'])
        self.assertAlmostEqual(val['pe_ttm']['reference_pe'],result['market']['latest_close_vnd']*1e9/30078169e6)
        self.assertTrue(val['pe']['available'])
        blocked=analyze_valuation(result['financial'],result['market'],company,{},ASOF)
        self.assertFalse(blocked['pe_ttm']['available'])


if __name__=='__main__':unittest.main()
