from copy import deepcopy
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from src.data.ssi_issuer import parse_ssi_pages,collect_ssi_issuer
from src.data.tvs_issuer import parse_tvs_pages
from src.data.providers import DataSourceError
from src.data.industry import exclusion_detail
from src.analysis.ai_commentary import checked_sections,validate_commentary
from src.analysis.ai_commentary import generate_commentary
from src.analysis.financial import analyze_financials
from src.analysis.context import analyze_context
from src.data.context_news import collect_context_news


def pages():
    def number(v):return f'{v:,}'.replace(',','.') if v>=0 else '('+f'{-v:,}'.replace(',','.')+')'
    def row(code,label,current,prior):return f'{code} | {label} {number(current)} | {number(prior)}'
    end='ngày 31 tháng 12 năm 2025\nĐơn vị tính: VND'
    return [
      dict(page=1,text='Công ty Cổ phần Chứng khoán SSI\nNgày 27 tháng 3 năm 2026\nBÁO CÁO KIỂM TOÁN ĐỘC LẬP'),
      dict(page=10,text='BÁO CÁO TÌNH HÌNH TÀI CHÍNH HỢP NHẤT B01-CTCK/HN\n'+end+'\nSố cuối năm | Số đầu năm\n'+'\n'.join([
        row('270','Tổng cộng tài sản',1_000_000_000_000,700_000_000_000),row('300','Nợ phải trả',600_000_000_000,400_000_000_000),
        row('400','Vốn chủ sở hữu',400_000_000_000,300_000_000_000),row('418','Lợi ích cổ đông không kiểm soát',10_000_000_000,8_000_000_000),
        row('114','Các khoản cho vay',100_000_000_000,80_000_000_000)])),
      dict(page=16,text='BÁO CÁO KẾT QUẢ HOẠT ĐỘNG HỢP NHẤT B02-CTCK/HN\n'+end+'\nNăm trước\nNăm nay (trình bày lại)\n'+'\n'.join([
        row('20','Cộng doanh thu hoạt động',400_000_000_000,300_000_000_000),row('200','Lợi nhuận kế toán sau thuế',100_000_000_000,60_000_000_000),
        row('201','Lợi nhuận sau thuế phân bổ cho chủ sở hữu',90_000_000_000,50_000_000_000),row('90','Tổng lợi nhuận kế toán trước thuế',120_000_000_000,78_000_000_000),
        row('91','Lợi nhuận đã thực hiện',110_000_000_000,80_000_000_000),row('92','Lợi nhuận chưa thực hiện',10_000_000_000,-2_000_000_000),
        row('03','Lãi từ các khoản cho vay',90_000_000_000,70_000_000_000),row('06','Doanh thu nghiệp vụ môi giới',100_000_000_000,80_000_000_000)])),
      dict(page=19,text='BÁO CÁO LƯU CHUYỂN TIỀN TỆ HỢP NHẤT B03b-CTCK/HN\n'+end+'\nNăm nay | Năm trước\n'+row('60','Lưu chuyển tiền thuần sử dụng vào hoạt động kinh doanh',-50_000_000_000,-30_000_000_000)),
    ]


class SsiStatementTests(unittest.TestCase):
    def parse(self,p=None):return parse_ssi_pages(p or pages(),2025,'2026-03-27','issuer')
    def test_ocr_keeps_signed_cash_flow_parent_profit_and_restatement(self):
        records=self.parse();f=analyze_financials(records)
        self.assertEqual([p['year'] for p in f['periods']],[2025,2024])
        self.assertEqual(f['periods'][0]['fields']['cfo']['value'],-50_000_000_000)
        self.assertEqual(f['periods'][1]['fields']['parent_profit']['value'],50_000_000_000)
        self.assertEqual(f['periods'][0]['scope'],'consolidated')
        self.assertEqual(f['periods'][0]['fields']['revenue']['page'],16)
    def test_wrong_year_scope_currency_or_issuer_is_not_promoted(self):
        for old,new in [('năm 2025','năm 2024'),('HỢP NHẤT','RIÊNG'),('VND','USD'),('Chứng khoán SSI','Chứng khoán XXX')]:
            p=pages()
            for page in p:page['text']=page['text'].replace(old,new)
            with self.assertRaises(DataSourceError):self.parse(p)
    def test_imbalanced_assets_are_rejected(self):
        p=pages();p[1]['text']=p[1]['text'].replace('1.000.000.000.000','1.001.000.000.000')
        with self.assertRaisesRegex(DataSourceError,'không cân bằng'):self.parse(p)
    def test_realized_and_unrealized_profit_must_reconcile(self):
        p=pages();p[2]['text']=p[2]['text'].replace('110.000.000.000','111.000.000.000')
        with self.assertRaisesRegex(DataSourceError,'không khớp tổng'):self.parse(p)
    def test_wrong_publication_date_and_missing_column_rejected(self):
        with self.assertRaises(DataSourceError):parse_ssi_pages(pages(),2025,'2026-03-28','issuer')
        p=pages();p[1]['text']=p[1]['text'].replace('Số đầu năm','')
        with self.assertRaises(DataSourceError):self.parse(p)
    def test_new_ratios_do_not_apply_industrial_cash_conversion_to_broker(self):
        f=analyze_financials(self.parse());m={r['key']:r['value'] for r in f['metrics']}
        self.assertEqual(m['liabilities_equity'],1.5);self.assertEqual(m['assets_equity'],2.5)
        self.assertEqual(m['loans_equity'],.25);self.assertEqual(m['securities_net_margin'],25)
        self.assertNotIn('cash_conversion',m)
        industry={'peers':[{'ticker':ticker,'financial':f} for ticker in ['AAA','BBB']], 'period_end':'2025-12-31','comparison_financial':f}
        _,i=analyze_context({'indicators':[]},industry,f)
        keys={row['key'] for row in i['comparisons']}
        self.assertTrue({'loans_equity','securities_net_margin','liabilities_equity','lending_revenue_growth'}<=keys)


class TvsStatementTests(unittest.TestCase):
    def fixture(self):
        result=pages()
        for page in result:
            page['text']=page['text'].replace('Chứng khoán SSI','Chứng khoán Thiên Việt').replace('Cộng doanh thu','Tổng doanh thu')
            if page['page']!=1:page['text']+='\nCho năm tài chính kết thúc ngày 31 tháng 12 năm 2025 | Cho năm tài chính kết thúc ngày 31 tháng 12 năm 2024'
        return result
    def test_explicit_year_columns_parent_profit_and_signed_cashflow(self):
        result=parse_tvs_pages(self.fixture(),2025,'2026-03-27','tvs')
        f=analyze_financials(result)
        self.assertEqual(f['periods'][0]['year'],2025)
        self.assertEqual(f['periods'][0]['fields']['parent_profit']['value'],90_000_000_000)
        self.assertEqual(f['periods'][0]['fields']['cfo']['value'],-50_000_000_000)
    def test_ocr_digit_error_is_blocked_by_profit_identity(self):
        p=self.fixture();p[2]['text']=p[2]['text'].replace('110.000.000.000','111.000.000.000')
        with self.assertRaisesRegex(DataSourceError,'không khớp tổng'):parse_tvs_pages(p,2025,'2026-03-27','tvs')
    def test_wrong_issuer_and_future_year_layout_are_rejected(self):
        with self.assertRaises(DataSourceError):parse_tvs_pages(pages(),2025,'2026-03-27','tvs')
        with self.assertRaises(DataSourceError):parse_tvs_pages(self.fixture(),2026,'2027-03-27','tvs')


class EvidenceValidationTests(unittest.TestCase):
    def bundle(self):return {'ticker':'SSI','evidence':[{'id':'M1','kind':'macro','source_ids':['official']},{'id':'F1','kind':'company','source_ids':['issuer']}], 'sources':[{'source_id':'official'},{'source_id':'issuer'}]}
    def test_one_bad_item_does_not_discard_sourced_valid_item(self):
        data={'macro':[{'text':'Xu hướng cần theo dõi cùng thanh khoản.','evidence_ids':['M1'],'source_ids':['official']},{'text':'Giá tăng 50%.','evidence_ids':['M1'],'source_ids':['official']}],'industry':[],'company_impact':[]}
        valid,rejected=checked_sections(data,self.bundle())
        self.assertEqual(len(valid['macro']),1);self.assertEqual(len(rejected),1)
        self.assertIn('số hoặc ngày',rejected[0]['reason'])
    def test_moving_average_names_are_allowed_but_numeric_claims_rejected(self):
        item={'text':'Theo dõi MA20 và MA50 cùng thanh khoản.','evidence_ids':['M1'],'source_ids':['official']}
        data={'macro':[item],'industry':[],'company_impact':[]}
        self.assertTrue(validate_commentary(data,self.bundle())['macro'])
        item['text']='MA20 tăng 30%.'
        with self.assertRaises(ValueError):validate_commentary(data,self.bundle())
    def test_source_spoofing_still_rejected(self):
        data={'macro':[{'text':'Theo dõi thanh khoản.','evidence_ids':['M1'],'source_ids':['issuer']}],'industry':[],'company_impact':[]}
        valid,rejected=checked_sections(data,self.bundle());self.assertFalse(valid['macro']);self.assertIn('không khớp',rejected[0]['reason'])
    def test_sdk_json_failure_explains_validation_without_leaking_payload(self):
        import json
        result={'request':{'use_ai':True},'industry':{'available':True,'name':'Chứng khoán','code':'8777'}}
        def fail(*args):raise json.JSONDecodeError('private response','secret content',0)
        with patch('src.analysis.ai_commentary.evidence_bundle',return_value=self.bundle()):out=generate_commentary(result,key='fake',caller=fail)
        self.assertEqual(out['failure_stage'],'validation');self.assertIn('JSON không hợp lệ',out['reason']);self.assertNotIn('secret',out['reason'])
    def test_service_failure_reports_status_without_leaking_sdk_message(self):
        result={'request':{'use_ai':True},'industry':{'available':True,'name':'Chứng khoán','code':'8777'}}
        class ServiceError(Exception):
            def __init__(self,code):
                super().__init__('secret credential URL and private response');self.code=code
        for code in (429,503,504):
            with self.subTest(code=code):
                def fail(*args):raise ServiceError(code)
                with patch('src.analysis.ai_commentary.evidence_bundle',return_value=self.bundle()):
                    out=generate_commentary(result,key='fake',caller=fail)
                self.assertEqual(out['status'],'failed');self.assertFalse(out['available'])
                self.assertEqual(out['failure_stage'],'request');self.assertEqual(out['http_code'],code)
                self.assertIn(f'HTTP {code}',out['reason']);self.assertNotIn('secret',out['reason'])
                self.assertEqual(out['sections'],{})
    def test_scope_and_period_exclusions_are_distinct(self):
        target={'year':2025,'period_end':'2025-12-31','scope':'consolidated','business_type':2}
        peer={'year':2025,'period_end':'2025-12-31','scope':'separate','business_type':2,'fields':{}}
        self.assertEqual(exclusion_detail({'periods':[peer]},target)['reason_code'],'scope_mismatch')
        reason=exclusion_detail({'periods':[]},target,['source: loại kỳ 2025, metadata 202501–202612'])
        self.assertEqual(reason['reason_code'],'invalid_period_metadata')
    def test_news_collection_limit_is_separate_from_three_card_preview(self):
        articles=[dict(title='Lạm phát',url=f'https://vnexpress.net/test-{i}.html',published_at='2026-10-10T12:00:00+07:00',period='2026-10-10',scope='macro',topics=['inflation']) for i in range(10)]
        body=b'<main class="fck_detail">'+b'public financial news '*30+b'</main>'
        with TemporaryDirectory() as folder,patch('src.data.context_news.download',return_value=body),patch('src.data.context_news.parse_feed',return_value=articles):
            out=collect_context_news('SSI',date(2026,10,11),{}, {},Path(folder),'fixture')
        self.assertEqual(len(out['articles']),8);self.assertEqual(out['candidate_counts']['macro'],10)


if __name__=='__main__':unittest.main()
