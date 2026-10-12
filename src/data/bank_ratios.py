"""Read issuer-reported ratios and audited loan notes from a pinned MBB PDF."""
import hashlib
import re

import pymupdf

from src.data.bank_issuer import amount_pair, label_text
from src.data.providers import DataSourceError
from src.data.shs_issuer import folded


def read_ratio_pages(path, manifest):
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['sha256']:
        raise DataSourceError('Checksum tài liệu tỷ lệ ngân hàng thay đổi.')
    with pymupdf.open(path) as doc:
        return {key: doc[spec['page']-1].get_text(sort=True, clip=pymupdf.Rect(
            doc[spec['page']-1].rect.width*spec['side']/2, 0,
            doc[spec['page']-1].rect.width*(spec['side']+1)/2,
            doc[spec['page']-1].rect.height)) for key,spec in manifest['ratio_pages'].items()}


def parse_mbb_ratios(pages, manifest, annual_fields, source_id):
    year = manifest['year']
    period = manifest['period_end']
    if manifest['period_type'] != 'annual' or period != f'{year}-12-31' or period > manifest['available_at']:
        raise DataSourceError('Kỳ hoặc thời điểm khả dụng tỷ lệ ngân hàng không hợp lệ.')
    table = ' '.join(folded(pages['table']).split())
    if not all(s in table for s in [f'nam {year-1} nam {year}', 'ty vnd', f'cua mb trong nam {year}']):
        raise DataSourceError('Chưa xác minh ngân hàng, đơn vị và thứ tự cột tỷ lệ.')
    specs = manifest['ratio_pages']
    base = dict(source_id=source_id, period=str(year), period_end=period, unit='%',
                published_at=None, available_at=manifest['available_at'],
                availability_basis=manifest['availability_basis'], statement_scope='consolidated',
                extraction_mode='embedded_text')
    # The summary table is prior/current/change; audited notes are current/prior.
    def reported(alias, key):
        rows = [s.strip() for s in pages['table'].splitlines() if label_text(s).startswith(alias+' ')]
        if len(rows) != 1:
            raise DataSourceError(f'Dòng tỷ lệ {key} thiếu hoặc trùng.')
        matches = re.findall(r'(?<![\d.,])-?\d+(?:,\d+)?\s*%', rows[0])
        if len(matches) != 3:
            raise DataSourceError(f'Dòng tỷ lệ {key} không đủ ba cột.')
        prior,current = [float(s.replace('%','').replace(',','.')) for s in matches[:2]]
        if not all(0 <= v <= 100 for v in (prior,current)):
            raise DataSourceError(f'Tỷ lệ {key} ngoài miền hợp lệ.')
        return dict(base, value=current, previous=prior, page=specs['table']['page'],
                    page_side=specs['table']['side'], source_row=rows[0], source_field='PDF: '+alias)
    # Tie the otherwise unlabelled scope of the summary to audited consolidated balances.
    for alias,key in [('von chu so huu','equity'),('tong tai san','assets')]:
        rows = [s.strip() for s in pages['table'].splitlines() if label_text(s).startswith(alias+' ')]
        pair = amount_pair(rows[0]) if len(rows)==1 else None
        field = annual_fields['balance'].get(key,{})
        if pair is None or any(abs(v*1e9-field.get(col, -1)) > .5e9 for v,col in zip(pair,('previous','value'))):
            raise DataSourceError('Bảng tỷ lệ không khớp số dư hợp nhất kiểm toán.')
    nim = reported('ty le thu nhap lai thuan nim','nim')
    car = reported('ty le an toan von car','car')
    npl_reported = reported('ty le no xau tong du no','npl')
    nim_text = ' '.join(folded(pages['nim_scope']).split())
    car_text = ' '.join(folded(pages['car_scope']).split())
    nim_match = re.search(rf'nim nam {year} dat (\d+(?:,\d+)?)%', nim_text)
    car_matches = re.findall(r'car hop nhat (?:duy tri o muc|dat) (\d+(?:,\d+)?)%', car_text)
    if 'bctc hop nhat cac ngan hang' not in nim_text or not nim_match or float(nim_match[1].replace(',','.')) != nim['value']:
        raise DataSourceError('NIM chưa khớp nhận xét có phạm vi hợp nhất.')
    if f'nam {year}' not in car_text or not car_matches or any(float(v.replace(',','.')) != car['value'] for v in car_matches):
        raise DataSourceError('CAR chưa khớp công bố CAR hợp nhất.')
    notes = ' '.join(folded(pages['loans']).split())
    if not all(s in notes for s in ['hop nhat da kiem toan',f'31/12/{year}',f'31/12/{year-1}','trieu dong','9.1 phan tich chat luong no cho vay']):
        raise DataSourceError('Thuyết minh nợ chưa xác nhận phạm vi, kỳ và đơn vị.')
    body = pages['loans'].split('9.1',1)[1]
    header = ' '.join(folded(body).split())
    if header.index(f'31/12/{year}') > header.index(f'31/12/{year-1}'):
        raise DataSourceError('Cột phân loại nợ bị đảo kỳ.')
    rows = [s.strip() for s in body.splitlines() if s.strip()]
    aliases = {'group1':'no du tieu chuan','group2':'no can chu y',
               'group3':'no duoi tieu chuan','group4':'no nghi ngo','group5':'no co kha nang mat von',
               'margin_advances':'cac khoan cho vay giao dich ky quy va'}
    loans = {}
    for key,alias in aliases.items():
        selected = [s for s in rows if label_text(s).startswith(alias)]
        pair = amount_pair(selected[0]) if len(selected)==1 else None
        if pair is None or any(v < 0 for v in pair):
            raise DataSourceError(f'Phân loại nợ thiếu hoặc không hợp lệ: {key}.')
        loans[key] = dict(base, value=pair[0]*1e6, previous=pair[1]*1e6, unit='VND',
            source_value=pair[0], unit_multiplier=1_000_000, page=specs['loans']['page'],
            page_side=specs['loans']['side'], source_row=selected[0], source_field='PDF: '+alias)
    totals = [amount_pair(s) for s in rows if re.fullmatch(r'[\d.,\s]+',s) and amount_pair(s)]
    if len(totals)!=1 or any(v <= 0 for v in totals[0]):
        raise DataSourceError('Tổng dư nợ gộp chưa xác minh.')
    gross = dict(base, value=totals[0][0]*1e6, previous=totals[0][1]*1e6, unit='VND',
        source_value=totals[0][0], unit_multiplier=1_000_000, page=specs['loans']['page'],
        page_side=specs['loans']['side'], source_field='PDF: Tổng thuyết minh 9.1')
    calculated = {}
    for col in ('value','previous'):
        if sum(v[col] for v in loans.values()) != gross[col]:
            raise DataSourceError('Các nhóm nợ và margin không cộng khớp tổng cho vay.')
        calculated[col] = sum(loans[k][col] for k in ('group3','group4','group5')) / gross[col]*100
        if abs(calculated[col]-npl_reported[col]) > .05000001:
            raise DataSourceError('NPL tính lại lệch tỷ lệ công bố ngoài sai số làm tròn.')
    nim.update(scope_evidence_pages=[specs['nim_scope']['page']], method='issuer_reported',
               limitation='NIM do ngân hàng công bố; chưa tái tính từ tài sản sinh lãi bình quân.')
    car.update(scope_evidence_pages=[specs['car_scope']['page']], method='issuer_reported',
               limitation='CAR do ngân hàng công bố; chưa tái tính từ vốn tự có và RWA.')
    npl = dict(npl_reported, **calculated, method='audited_note_calculation',
        reported_source=dict(npl_reported),
        reported_value=npl_reported['value'], reported_previous=npl_reported['previous'],
        page=specs['loans']['page'], page_side=specs['loans']['side'],
        source_field='Calculation: Thuyết minh 9.1',
        inputs=[loans[k] for k in ('group3','group4','group5')]+[gross],
        limitation='Mẫu số là tổng cho vay gộp hợp nhất thuyết minh 9.1, gồm margin/ứng trước chứng khoán. Khớp tỷ lệ công bố ở độ chính xác một chữ số; không chứng nhận cùng toàn bộ quy ước phân loại.')
    npl.pop('source_row')  # The reported row belongs to page 46, not the calculated note on 161.
    return dict(available=True, period_end=period, scope='consolidated',
                metrics={'nim':nim,'npl':npl,'car':car}, gross_loans=gross,
                checks=[dict(name='summary_balances_and_consolidated_scope',valid=True),
                        dict(name='loan_groups_sum_and_rounded_reported_npl',valid=True)])
