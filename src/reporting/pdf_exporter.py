"""Selectable Vietnamese PDF from the saved analysis result."""
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse
import sys
from xml.sax.saxutils import escape, quoteattr
from src.models import SECTION_LABELS
from src.reporting.charts import market_chart, research_chart
from src.analysis.price_quality import latest_price_matches

ROOT=Path(__file__).resolve().parents[2]
try:
    import reportlab
except ImportError:
    sys.path.insert(0,str(ROOT/".vendor"))
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, NextPageTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak

def formatted(value, unit=""):
    if value is None:return "Chưa đủ dữ liệu"
    if unit=="VND":return f"{value/1e9:,.2f} tỷ VND"
    if unit=="VND/share":return f"{value:,.0f} VND"
    return f"{value:,.2f}"+(f" {unit}" if unit else "")

def generate_report(result: dict, path: Path | None=None) -> Path:
    request=result["request"];run_id=result["acquisition"]["run_id"]
    path=Path(path) if path else ROOT/"outputs/runs"/run_id/f"{request['ticker']}_report.pdf"
    path.parent.mkdir(parents=True,exist_ok=True)
    for name,file in [("DV","DejaVuSans.ttf"),("DV-Bold","DejaVuSans-Bold.ttf")]:
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(ROOT/"assets/fonts"/file)))
    pdfmetrics.registerFontFamily("DV",normal="DV",bold="DV-Bold",italic="DV",boldItalic="DV-Bold")
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="BodyVN",fontName="DV",fontSize=9,leading=14,spaceAfter=6,allowWidows=0,allowOrphans=0,textColor=colors.HexColor("#263640")))
    styles.add(ParagraphStyle(name="SmallVN",parent=styles["BodyVN"],fontSize=8,leading=11.5,spaceAfter=3,wordWrap="CJK"))
    styles.add(ParagraphStyle(name="SourceVN",parent=styles["SmallVN"],fontSize=7.2,leading=9,spaceAfter=2))
    styles.add(ParagraphStyle(name="MethodVN",parent=styles["SmallVN"],leading=10,spaceAfter=2))
    styles.add(ParagraphStyle(name="HeadingVN",parent=styles["BodyVN"],fontName="DV-Bold",fontSize=14,leading=19,spaceBefore=14,spaceAfter=9,keepWithNext=True,textColor=colors.HexColor("#14566e")))
    styles.add(ParagraphStyle(name="EvidenceHeadingVN",parent=styles["HeadingVN"],fontSize=11,leading=15,spaceBefore=8,spaceAfter=5))
    styles.add(ParagraphStyle(name="TitleVN",parent=styles["HeadingVN"],fontSize=22,leading=28,spaceBefore=0))
    story=[];left_panels={};left_cards={};current_section="overview"
    full_width={"methods","sources","valuation_appendix"};right_width=112*mm;left_width=56*mm
    def p(value,small=False,source=False):
        safe=str(value).translate(str.maketrans({"—":"-","–":"-","‑":"-","−":"-"}))
        return Paragraph(escape(safe).replace("\n","<br/>"),styles["SourceVN" if source else "MethodVN" if small and current_section=="methods" else "SmallVN" if small else "BodyVN"])
    def text(value,small=False):story.append(p(value,small))
    def heading(value):story.append(Paragraph(escape(value),styles["HeadingVN"]))
    def start_section(key,title):
        nonlocal current_section
        current_section=key
        left_panels.setdefault(key,[])
        story.extend([NextPageTemplate(key),PageBreak()])
        heading(title)
    def table(headers,rows,widths=None,keep=False,sidebar=False):
        if not rows:return
        cells=[[p(h,True) for h in headers]]+[[p(v,True) for v in row] for row in rows]
        available_width=left_width if sidebar else 174*mm if current_section in full_width else right_width
        specified=widths or [174*mm/len(headers)]*len(headers)
        t=Table(cells,colWidths=[w*available_width/sum(specified) for w in specified],repeatRows=1,hAlign="LEFT",rowSplitRange=(2,-2) if len(rows)>4 else None)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e3eef2")),("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
            ("LINEBELOW",(0,0),(-1,0),.7,colors.HexColor("#14566e")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f7f8")])]))
        if sidebar:left_cards.setdefault(current_section,[]).extend([t,Spacer(1,9)])
        elif len(rows)<=4 or keep:story.append(KeepTogether([t,Spacer(1,6)]))
        else:story.extend([t,Spacer(1,6)])
    source_by_id={s["source_id"]:s for s in result["sources"]}
    def source_label(source):
        sid=source['source_id'];url=source.get('url_or_file','');host=urlparse(url).hostname or ''
        if sid.startswith('BANK_'):
            ticker=sid.split('_')[1]
            suffix=' (kho công bố)' if 'archive' in source.get('notes','') else ''
            return ticker+' - BCTC gốc'+suffix
        if sid.startswith('SSI_'):return 'SSI - BCTC kiểm toán' if 'AUDITED' in sid else 'SSI - công bố thông tin'
        if sid.startswith('TVS_AUDITED'):return 'TVS - BCTC kiểm toán'
        if sid.startswith('SHS_'):return 'SHS - báo cáo công bố'
        if 'PEER_' in sid:return 'KBS - BCTC mẫu ngành'
        if sid.startswith(('KBS_balance','KBS_income','KBS_cashflow')):return 'KBS - BCTC'
        if sid.startswith('NSO'):return 'Cục Thống kê'
        if sid.startswith('WDI'):return 'World Bank'
        if sid.startswith('SECTOR'):return 'Vietcap - phân ngành'
        if sid.startswith('CTX_VNINDEX'):return 'Vietcap - VN-Index'
        if sid.startswith('CTX_BRENT'):return 'Yahoo Finance - Brent futures'
        if sid.startswith('CTX_NEWS'):return 'VnExpress' if 'vnexpress' in host else 'VnEconomy'
        if sid.startswith(('MINER','ZENODO')):return 'vn-annual-report-miner'
        if sid.startswith('VNF'):return 'vnfinancialdata'
        if 'YAHOO' in sid.upper():return 'Yahoo Finance'
        if 'KBS' in sid:return 'KBS'
        if 'VCI' in sid or 'VIETCAP' in sid:return 'Vietcap'
        if host.endswith('kbsec.com.vn'):return 'KBS'
        if host.endswith('ssi.com.vn'):return 'SSI Research'
        return host or 'Tài liệu công khai'
    used_sources=set()
    def citations(ids, note=""):
        ids={i for i in ids if i in source_by_id};used_sources.update(ids)
        if ids:
            if story and isinstance(story[-1],Paragraph):story[-1].keepWithNext=True
            names=sorted({source_label(source_by_id[i]) for i in ids})
            text("Nguồn: "+", ".join(names)+(". "+note if note else ""),True)
    def panel(kind,note):
        chart=market_chart(result,path.parent/"charts") if kind=="market" else research_chart(result,kind,path.parent/"charts")
        if chart:
            if current_section in full_width:
                iw,ih=ImageReader(str(chart)).getSize();story.append(Image(str(chart),width=50*mm,height=ih/iw*50*mm));text(note,True)
            else:left_panels.setdefault(current_section,[]).append((chart,note))
    def narrative_notes(section):
        news=[]
        for item in result.get("research_narrative",{}).get(section,[]):
            if item["title"]=="Thông tin cập nhật":news.append(item);continue
            # These values and channels are already printed in the industry tables
            # and driver paragraphs immediately above; avoid repeating them.
            if section=="industry" and (item["title"]=="Kênh vĩ mô vào ngành" or item["title"].endswith("trong nhóm so sánh")):continue
            note_start=len(story)
            story.append(Paragraph(escape(item["title"]),styles["EvidenceHeadingVN"]))
            interpretation=item["interpretation"].replace("Nguồn báo chí đang đề cập vấn đề này; đây là kênh tác động có điều kiện, không chứng nhận mọi phát biểu trong bài. ","Suy luận có điều kiện từ tin báo chí: ")
            text(item["evidence"],True);text(interpretation,True)
            text("Theo dõi: "+item["monitor"],True);citations(item["source_ids"],"Kỳ/ngày nguồn: "+item["period"])
            story[note_start:]=[KeepTogether(story[note_start:])]
        if news:
            story.append(Paragraph("Thông tin cập nhật từ báo chí",styles["EvidenceHeadingVN"]))
            for item in news[:(8 if full else 3)]:
                source=source_by_id.get(next(iter(item['source_ids']),''),{})
                url=source.get('url_or_file','')
                safe=escape(item['evidence'])
                story.append(Paragraph(f'<a href={quoteattr(url)} color="#14566e">{safe}</a>' if url.startswith('https://') else safe,styles['SmallVN']))
                used_sources.update(item['source_ids'])
            text("Các tin trên là mẫu theo ngày, không thay dữ liệu định lượng. Cần kiểm tra kỳ số liệu và công bố chính thức trước khi điều chỉnh dự báo; Gemini chỉ diễn giải phần qua kiểm tra.",True)
    def ai_notes(section):
        ai=result.get("ai_commentary",{})
        for item in ai.get("sections",{}).get(section,[]):
            text("Nhận xét hỗ trợ AI: "+item["text"])
            for e in item.get("evidence",[]):
                value=e.get("value")
                caption=(e['label']+": bằng chứng bài công khai, cần kiểm tra kỳ của số liệu." if e.get("evidence_type")=="news_article" else
                         f"{e['label']}: "+(formatted(value,e.get("unit","")) if value is not None else f"mã {e.get('company_value')}; trung vị {e.get('sample_median')}; n={e.get('sample_size')}"))
                text(caption+f" · Kỳ {e.get('period')} · Ngày chốt {ai.get('as_of')}",True)
            citations(item["source_ids"],f"AI {ai.get('model')}; tạo {ai.get('generated_at','')[:10]}; suy luận có điều kiện.")
    selected=set(request["sections"]);full=request["mode"]=="full"
    story.append(Paragraph(f"{escape(request['ticker'])} | Báo cáo phân tích",styles["TitleVN"]))
    text(f"{result['company'].get('name') or request['ticker']} · Ngày phân tích {request['as_of']}")
    text(f"Dữ liệu giá thực nhận: {result['market'].get('first_date', 'chưa xác định') if result['market'] else 'chưa có'} đến {result['market']['latest_date'] if result['market'] else 'chưa có'} · Chế độ: {'bản đầy đủ' if full else 'tóm tắt'}")
    text("Nội dung đã chọn: "+", ".join(SECTION_LABELS[k] for k in request["sections"]),True)
    text(result["conclusion"]["summary"])
    ai=result.get('ai_commentary',{})
    if request.get('use_ai'):
        if ai.get('available'):
            text(f"Gemini: {sum(len(v) for v in ai.get('sections',{}).values())} nhận xét đã qua kiểm tra ở phần vĩ mô, ngành và tác động doanh nghiệp. AI hỗ trợ diễn giải; định giá/khuyến nghị do công thức và quy tắc của chương trình thực hiện.",True)
        else:text("Gemini chưa có nội dung được sử dụng: "+ai.get('reason','Không có phản hồi hợp lệ.'),True)
    quality=result["quality"]
    labels={"matched":"Đã khớp nguồn thứ hai","unverified":"Chưa xác minh đầy đủ","matched_selected_fields":"Khớp các chỉ tiêu đã chọn","mismatch":"Có sai lệch — đã chặn","not_independently_checked":"Chưa đối chiếu độc lập","analyzed":"Đã phân tích","partial":"Thiếu một phần dữ liệu"}
    quote=quality["price_check"]
    sample_count=quote.get("expected_count",len(quote.get("checks",[])))
    matched_count=quote.get("matched_count",sum(c["match"] for c in quote.get("checks",[])))
    table(["Kiểm tra","Kết quả"],[["Giá mới nhất","Đã khớp đúng ngày" if latest_price_matches(quote,result.get("market")) else "Chưa khớp đúng ngày"],["Mẫu giá lịch sử",f"Khớp {matched_count}/{sample_count} phiên" if sample_count else "Chưa đối chiếu"],["Kiểm tra tài chính",labels.get(quality["financial_check"]["status"],quality["financial_check"]["status"])],["Trạng thái",labels.get(result["status"],result["status"])]],sidebar=True)
    text("Các kiểm tra chỉ áp dụng cho số liệu và kỳ được nêu; không xác nhận toàn bộ lịch sử. Báo cáo dùng dữ liệu công khai và các giả định công bố bên dưới.",True)
    if "overview" in selected:
        heading(SECTION_LABELS["overview"])
        metric_map={m["key"]:m for m in result["financial"]["metrics"]}
        kpis=[]
        if result.get("market"):kpis.append(("Giá / "+result["market"]["latest_date"],formatted(result["market"]["latest_close_vnd"],"VND/share")))
        for key in ["net_profit","roe","cir" if result["financial"].get("industry_group")=="bank" else "net_profit_growth"]:
            m=metric_map.get(key)
            if m and m["value"] is not None:kpis.append((m["label"]+" / "+m["period"],formatted(m["value"],m["unit"])))
        if kpis:table(["Chỉ tiêu chính","Giá trị"],[[k[0],k[1]] for k in kpis],sidebar=True)
        # Keep the detailed price figure in its own section rather than repeat it
        # beside the overview's quality and KPI cards.
        recommendation=result.get("recommendation",{})
        if recommendation:
            heading("Khuyến nghị nghiên cứu")
            text(recommendation["stance"]);text(recommendation["reason"])
            text(recommendation["horizon"]+f" · Tin cậy: {recommendation['confidence']}",True)
            if recommendation.get("target_price_vnd"):
                text(f"Định giá chính: {recommendation['target_price_vnd']:,.0f} VND/CP; chênh lệch "+formatted(recommendation.get("upside_pct"),"%")+". Không phải lợi suất dự báo.",True)
            citations(recommendation["source_ids"])

        text(f"Sàn: {result['company'].get('exchange') or 'chưa có'} · Website: {result['company'].get('website') or 'chưa có'}")
        business=result["company"].get("business") or "Nguồn chưa cung cấp mô tả doanh nghiệp."
        limit=300 if full else 200
        text(business if len(business)<=limit else business[:limit].rsplit(" ",1)[0]+"… (mô tả rút gọn từ nguồn)")
        thesis=result["conclusion"].get("integrated_thesis",[])
        preview=[i for i in thesis if i.startswith("Vĩ mô")][:1]+[i for i in thesis if i.startswith("Ngành")][:2]
        for item in preview[:2]:
            if (item.startswith("Vĩ mô") and "macro" in selected and "industry" in selected) or (item.startswith("Ngành") and "industry" in selected):text("• "+item)
        if not recommendation:
            for item in result["conclusion"]["opportunities"][:2]:text("• "+item)
        if "macro" in selected and "industry" in selected:ai_notes("company_impact")
        citations([i["source_id"] for m in result["financial"]["metrics"] for i in m["inputs"] if i.get("source_id")]+[d["indicator"]["source_id"] for d in result.get("industry",{}).get("drivers",[])])
    if "macro" in selected:
        start_section("macro",SECTION_LABELS["macro"])
        macro=result.get("macro",{})
        indicators=macro.get("indicators",[])
        chosen=[r for r in indicators if r["key"] not in {"gdp_current_usd","lending_annual","fx_annual"}] if full else [r for r in indicators if r["key"] in {"gdp_ytd","cpi_ytd","credit_growth","usd_index_yoy","gdp_annual","cpi_annual"}]
        table(["Chỉ tiêu","Giá trị","Kỳ tham chiếu","Công bố / cập nhật nguồn"],[[r["label"],formatted(r["value"],r["unit"]),r["period"],r.get("published_at") or "Cập nhật "+r.get("source_updated_at","")] for r in chosen],[69*mm,27*mm,38*mm,40*mm])
        panel("macro","Chuỗi VN-Index (điểm) và Brent futures (USD/thùng) nếu lấy được; chỉ dùng phiên đã kết thúc. Hợp đồng dầu có chuyển kỳ; không phải dầu giao ngay. Khi thiếu, hiển thị nền năm WDI và ghi nguồn.")
        citations([r["source_id"] for r in chosen]+[r["source_id"] for r in macro.get("annual_history",[]) if r["key"] in {"gdp_annual","cpi_annual"}])
        text(macro.get("assessment","Chưa có dữ liệu vĩ mô hợp lệ."))
        narrative_notes("macro")
        for source_block in [result.get("context_news",{}),result.get("market_context",{})]:
            for error in source_block.get("errors",[]):text("Nguồn nhận xét chưa lấy được: "+error["message"],True)
        for item in result["conclusion"].get("integrated_thesis",[]):
            if item.startswith("Vĩ mô"):text(item)
        ai_notes("macro")
        text("NSO: báo cáo/ước tính theo ngày công bố. WDI: ngày cập nhật không phải ngày công bố lần đầu. Không so các kỳ khác độ dài; lãi suất/tỷ giá lịch sử ở phụ lục.",True)
    if "industry" in selected:
        start_section("industry",SECTION_LABELS["industry"])
        industry=result.get("industry",{})
        if industry.get("available"):
            text(f"{industry['name']} · Phân loại {industry.get('taxonomy','KBS')} · {len(industry['members'])} thành viên trong nguồn.")
            text(industry["selection"],True)
            text(f"Mẫu đủ điều kiện: {industry.get('eligible_candidates',0)}; đã chọn {len(industry['peers'])} doanh nghiệp. Ngày cuối kỳ {industry.get('period_end','chưa có')}; phạm vi {industry.get('scope','chưa có')}. Phân ngành chụp tại {industry['classification_snapshot'][:10]}.",True)
            comparisons=industry.get("comparisons",[])
            table(["Chỉ tiêu","Mã phân tích","Trung vị mẫu","Chênh lệch","n"],[[c["label"],formatted(c["company_value"],c["unit"]),formatted(c["sample_median"],c["unit"]),formatted(c["difference"],"điểm %" if c["unit"]=="%" else c["unit"]),str(c["sample_size"])] for c in comparisons],[62*mm,32*mm,32*mm,33*mm,15*mm])
            table(["Doanh nghiệp mẫu","LNST YoY (%)","ROE (%)","ROA (%)"],[[r["ticker"]]+[formatted(r["values"].get(k)) for k in ["net_profit_growth","roe","roa"]] for r in industry.get("comparison_rows",[])])
            if not comparisons:text("Chưa đủ hai doanh nghiệp có chỉ tiêu hợp lệ cùng kỳ để tính trung vị; không tự tạo số so sánh.")
            for driver in industry.get("drivers",[])[:2]:
                r=driver["indicator"];text(f"{r['label']}: {r['value']:.2f}% ({r['period']}). "+driver["channel"])
            for risk in industry.get("structural_risks",[])[:2]:text("• "+risk,True)
            if full and industry.get("excluded"):
                text(f"Có {len(industry['excluded'])} mã bị loại do kỳ/phạm vi/dữ liệu; danh sách và lý do được lưu cùng kết quả phân tích.",True)
        else:text("Chưa có phân ngành được nguồn xác nhận; không tự gán ngành hoặc tạo mẫu so sánh.")
        if industry.get("available"):
            panel("industry","So sánh mẫu cùng kỳ/phạm vi; trung vị loại mã đang phân tích. Số mẫu được ghi cho từng chỉ tiêu, không đại diện toàn ngành.")
            citations([r["source_id"] for r in industry.get("sources",[])]+[d["indicator"]["source_id"] for d in industry.get("drivers",[])])
            ai_notes("industry")
            narrative_notes("industry")
    if "market" in selected:
        start_section("market",SECTION_LABELS["market"]);market=result.get("market")
        if market:
            history_blocked=not market.get("history_indicators_available",True)
            history_label="Không tính: lịch sử chưa khớp"
            table(["Chỉ tiêu","Giá trị"],[["Đóng cửa / ngày",formatted(market["latest_close_vnd"],"VND/share")+" / "+market["latest_date"]],
                [market.get("return_label","Biến động trong khoảng chọn"),history_label if history_blocked else formatted(market["return_pct"],"%")],["Sụt giảm tối đa",history_label if history_blocked else formatted(market["max_drawdown_pct"],"%")],
                ["Biến động năm hóa",history_label if history_blocked else formatted(market["annualized_volatility_pct"],"%")],["MA20 / MA50",history_label if history_blocked else formatted(market["ma20_vnd"],"VND/share")+" / "+formatted(market["ma50_vnd"],"VND/share")],
                ["Khối lượng bình quân 20 phiên",formatted(market["average_volume_20"],"CP")]], [70*mm,104*mm])
            panel("market","Biểu đồ và MA20/MA50 dùng giá đóng cửa (Close) của nguồn. MA chỉ hiển thị khi mẫu đối chiếu lịch sử khớp. Giá đóng cửa mới nhất được kiểm tra riêng để định giá.")
            citations([r["source_id"] for r in result["price_rows"] if r.get("source_id")]+[quality["price_check"].get("source_id")])
            text(market["return_note"],True);text(quality["price_check"].get("note","Không có đối chiếu giá."),True)
            differences=[c for c in quality["price_check"].get("checks",[]) if not c["match"]]
            if differences:
                differences_start=len(story)
                heading("Đối chiếu lịch sử: các phiên lệch")
                table(["Ngày lệch nguồn",quote.get("primary_provider","Yahoo")+" (VND)",quote.get("reference_provider","KBS")+" (VND)","Sai lệch"],[[c["date"],formatted(c.get("primary_close",c["yahoo_close"])),formatted(c.get("reference_close",c["kbs_close"])),formatted(c["relative_difference"]*100,"%")] for c in differences],keep=True)
                story[differences_start:]=[KeepTogether(story[differences_start:])]
        else:text("Chưa có chuỗi giá hợp lệ; không tính các chỉ tiêu thị trường.")
    if "financial" in selected:
        start_section("financial",SECTION_LABELS["financial"]);metrics=result["financial"]["metrics"]
        for message in result.get("financial_data_status",{}).get("messages",[]):text(message,True)
        if metrics:
            caption=p(f"Báo cáo năm {metrics[0]['period']}; tăng trưởng so với năm trước cùng phạm vi. Tiền quy đổi: tỷ VND.")
            caption.keepWithNext=True
            story.append(caption)
            issuer=result.get("issuer_financials",{})
            if issuer.get("available"):
                scope='hợp nhất' if issuer.get('scope')=='consolidated' or request['ticker']=='SSI' else 'riêng lẻ'
                if issuer.get('availability_note'):
                    text(f"BCTC kiểm toán {request['ticker']} {issuer['year']}, phạm vi {scope}; đơn vị gốc triệu VND, quy đổi VND. {issuer['availability_note']} PDF kiểm tra checksum, kỳ, thứ tự cột và các chỉ tiêu liệt kê; không chứng nhận toàn bộ BCTC.",True)
                else:
                    text(f"Bảng kiểm toán {request['ticker']} {issuer['year']}; phạm vi {scope}, đơn vị gốc VND. Ngày công bố {issuer['published_at']}. PDF được kiểm tra checksum, kỳ và từng hàng; đối chiếu chỉ các chỉ tiêu liệt kê.",True)
                citations([s["source_id"] for s in issuer["sources"]])
            group=result["financial"].get("industry_group")
            panel("financial","Các cột thể hiện số liệu năm đã công bố, cùng phạm vi. "+("CFO ngân hàng phản ánh biến động tài sản/nợ hoạt động; không áp CFO/LNST của doanh nghiệp sản xuất." if group=="bank" else "CFO chứng khoán chịu ảnh hưởng danh mục đầu tư và cho vay; không áp CFO/LNST của doanh nghiệp sản xuất." if group=="securities" else "So sánh lợi nhuận với CFO để theo dõi chuyển đổi thành tiền; cần đọc thay đổi vốn lưu động."))
            citations([r["source_id"] for m in metrics for r in m["inputs"] if r.get("source_id")])
            for item in result["conclusion"]["opportunities"]+result["conclusion"]["risks"]:
                if any(word in item for word in ["CFO","LNST","doanh thu","ROE","CIR"]):text(item)
            chosen=metrics if full else [m for m in metrics if m["key"] in {"revenue","net_profit","revenue_growth","net_profit_growth","roe","cash_conversion","net_interest_income","cir","roa"}]
            table(["Chỉ tiêu","Giá trị"],[[m["label"],formatted(m["value"],m["unit"])] for m in chosen],[100*mm,74*mm])
            if full:
                bank=result["financial"].get("industry_group")=="bank"
                income="net_interest_income" if bank else "revenue"
                table(["Năm","Thu nhập lãi thuần (tỷ)" if bank else "Doanh thu (tỷ)","LNST cùng phạm vi (tỷ)","CFO (tỷ)"],[[str(year["year"])]+[formatted(year["fields"].get(k,{}).get("value"),"VND").replace(" tỷ VND","") for k in [income,"net_profit","cfo"]] for year in result["financial"]["periods"]])
        else:text("Chưa đủ dữ liệu tài chính có kỳ và phạm vi hợp lệ.")
        interim=result.get("interim")
        if interim and interim["valid"]:
            text(f"Cập nhật bán niên {request['ticker']} kết thúc {interim['period_end']} — BCTC hợp nhất gốc đã kiểm tra.")
            table(["Chỉ tiêu","6 tháng hiện tại (tỷ)","6 tháng cùng kỳ (tỷ)","Trang PDF"],[[label,formatted(interim["fields"][k]["value"],"VND").replace(" tỷ VND",""),formatted(interim["fields"][k]["previous"],"VND").replace(" tỷ VND",""),str(interim["fields"][k]["page"])] for k,label in [("revenue","Doanh thu thuần"),("net_interest_income","Thu nhập lãi thuần"),("net_profit","LNST hợp nhất"),("parent_profit","LNST cổ đông mẹ"),("cfo","Dòng tiền kinh doanh")] if k in interim["fields"]])
            if interim.get('ticker'):
                table(['Chỉ tiêu số dư','Cuối kỳ (tỷ)','Đầu năm (tỷ)'],[[label,formatted(interim['fields'][k]['value'],'VND').replace(' tỷ VND',''),formatted(interim['fields'][k]['previous'],'VND').replace(' tỷ VND','')] for k,label in [('assets','Tổng tài sản'),('equity','Vốn chủ sở hữu'),('non_controlling_equity','Vốn cổ đông không kiểm soát')] if k in interim['fields']])
                citations([interim['source_id']])
            text(interim["note"],True)
        if full:
            names={m['key']:m['label'] for m in metrics}
            names.update(revenue='Doanh thu hoạt động' if result['financial'].get('industry_group')=='securities' else 'Doanh thu thuần',net_profit='LNST',assets='Tài sản',equity='Vốn chủ',liabilities='Nợ phải trả',
                non_controlling_equity='Vốn cổ đông không kiểm soát',lending_revenue='Lãi cho vay và phải thu',brokerage_revenue='Doanh thu môi giới',pretax_profit='LN trước thuế',parent_profit='LNST cổ đông mẹ',cfo='Dòng tiền kinh doanh',financial_loans='Các khoản cho vay')
            table(["Đối chiếu / kỳ","Phân tích (tỷ)","Nguồn đối chiếu (tỷ)","Kết quả"],[[names.get(c["metric"],c["metric"])+" / "+c["period"],formatted(c["actual_billion_vnd"]),formatted(c["reference_billion_vnd"]),"Khớp" if c["match"] else "Sai lệch"] for c in quality["financial_check"].get("checks",[])],keep=True)
    if "reference" in selected:
        start_section("reference",SECTION_LABELS["reference"])
        panel("reference","Số trang PDF đã tải và kiểm tra khả năng đọc. Năm báo cáo không phải ngày công bố; số trang không chứng nhận số liệu tài chính.")
        reference=result.get("reference",{})
        text("Nguồn vn-annual-report-miner cung cấp lịch sử năm và danh mục BCTN. Parquet chưa có metadata chứng nhận đơn vị, phạm vi và ngày công bố; không dùng để thay tài chính/định giá chính.",True)
        citations([s["source_id"] for s in reference.get("sources",[])])
        vnf=result.get("vnfinancialdata",{})
        if vnf:
            heading("BCTC bổ sung: vnfinancialdata")
            text(vnf.get("reason",""),True)
            if vnf.get("available"):
                text(f"Dataset {vnf['dataset']['revision']}; {vnf['row_count']:,} dòng gốc, năm {min(vnf['years'])}–{max(vnf['years'])}. Từ điển khai báo VND cho các dòng tiền được ánh xạ; chưa xác nhận phạm vi/ngày công bố từng kỳ. Không tự thay đầu vào định giá.",True)
                table(["Bảng tài chính","Năm mới nhất","Số dòng"],[[s["statement"],str(s["latest_year"] or "Chưa có"),str(s["row_count"])] for s in vnf["statements"]])
                values={}
                for record in vnf["records"]:values.setdefault(record["year"],{}).update(record["fields"])
                years=sorted(values,reverse=True)[:(3 if full else 1)]
                if years:
                    table(["Năm","Doanh thu (tỷ)","LNST (tỷ)","Tài sản (tỷ)","CFO (tỷ)"],[[str(y)]+[formatted(values[y].get(k,{}).get("value")/1e9) if values[y].get(k,{}).get("value") is not None else "Chưa có" for k in ["revenue","net_profit","assets","cfo"]] for y in years])
                checks=vnf.get("checks",[])
                if checks:
                    latest=max(c["year"] for c in checks);chosen=[c for c in checks if c["year"]==latest]
                    text(f"Đối chiếu năm {latest}: {sum(c['match'] for c in chosen)}/{len(chosen)} giá trị khớp trong 0,1%. Khớp giá trị không xác nhận độc lập nguồn gốc hoặc phạm vi báo cáo.",True)
                    for check in chosen:
                        if not check["match"]:text(f"{check['label']}: nguồn chính {check['primary_vnd']/1e9:,.3f} tỷ VND; vnfinancialdata {check['reference_vnd']/1e9:,.3f} tỷ VND. "+(check.get("note") or "Giá trị lệch; giữ nguyên hai nguồn để kiểm tra."),True)
            for error in vnf.get("errors",[]):text("vnfinancialdata: "+error["message"],True)
            citations([s["source_id"] for s in vnf.get("sources",[])])
        grouped={}
        for record in reference.get("records",[]):grouped.setdefault(record["year"],{}).update(record["fields"])
        years=sorted(grouped,reverse=True)[:(5 if full else 2)]
        if years:
            heading("Bảng bổ sung: vn-annual-report-miner")
            text("Bảng dưới chỉ chia giá trị gốc cho 10^9 để dễ đọc; không tự xác nhận đơn vị tỷ VND.",True)
            table(["Năm","Doanh thu / 10^9","LNST / 10^9","Tài sản / 10^9","CFO / 10^9"],[[str(year)]+[formatted(grouped[year].get(k,{}).get("value")/1e9) if grouped[year].get(k,{}).get("value") is not None else "Chưa có" for k in ["revenue","net_profit","assets","cfo"]] for year in years])
        checks=reference.get("checks",[])
        if checks:
            latest=max(c["year"] for c in checks)
            chosen=[c for c in checks if c["year"]==latest]
            text(f"Đối chiếu giá trị với nguồn chính, năm {latest}; khớp số không chứng nhận phạm vi hoặc nguồn độc lập.",True)
            table(["Chỉ tiêu","Nguồn chính / 10^9","Parquet / 10^9","Sai lệch"],[[c["label"],formatted(c["primary_vnd"]/1e9),formatted(c["reference_raw"]/1e9),formatted(c["relative_difference"]*100,"%")+(" - Lệch" if not c["match"] else " - Khớp")] for c in chosen])
        for report in reference.get("reports",[])[:(3 if full else 1)]:
            inspection=report.get("inspection",{})
            text(f"BCTN {report['year']}: {report['file_name']}. "+(f"Đã tải; SHA256 khớp danh mục; {inspection.get('pages',0)} trang, {inspection.get('text_pages',0)} trang có text." if report.get("file") else "Có trong danh mục; chưa tải."),True)
            if report.get("file") and inspection.get("status")!="text_available":text("Báo cáo có nhiều trang scan; cần OCR thêm trước khi tự trích/kiểm chứng số liệu.",True)
        for error in reference.get("errors",[]):text("Nguồn bổ sung chưa đủ: "+error["message"],True)
        if not reference.get("available"):text("Chưa có dữ liệu bổ sung phù hợp ngày phân tích/sàn/phiên bản nguồn.")
        if reference.get("commit"):text("Phiên bản dữ liệu: "+reference["commit"]+"; ghi nhận tại "+reference["version_available_at"]+". Năm báo cáo không phải ngày công bố.",True)
    def valuation_appendix():
        start_section("valuation_appendix","Phụ lục: giả định và kiểm tra độ nhạy");val=result["valuation"]
        if val["available"]:
            text(val["assumption"])
            if val.get("price_warning"):text(val["price_warning"],True)
            text(f"Kỳ tài chính {val['equity_period']}; số CP snapshot {val['shares_snapshot']}: {val['shares']:,.0f}.",True)
            a=val.get("assumptions",{})
            if a:text(f"Giả định: P/B {a['target_pb']:.2f}x; P/E {a['target_pe']:.2f}x; Ke {a['cost_of_equity']*100:.2f}%; WACC {a['wacc']*100:.2f}%; g dài hạn {a['terminal_growth']*100:.2f}%; tăng FCFF {a['forecast_growth']*100:.2f}%; thuế {a['tax_rate']*100:.2f}%.",True)
            if val.get("book_value_per_share") is not None:text(f"BVPS mẹ: {formatted(val['book_value_per_share'],'VND/share')} · P/B tham chiếu: {val['reference_pb']:.2f} lần.")
            text("P/B/P/E nhập tay, Gordon và DCF dưới đây là giả định thử độ nhạy; không quyết định định giá hoặc khuyến nghị chính.")
            citations([s["source_id"] for s in val.get("industry",{}).get("sources",[])]+[r["source_id"] for peer in val.get("industry",{}).get("peers",[]) for r in peer.get("inputs",[]) if r.get("source_id")])
            if val.get("pb_methods"):table(["Phương pháp P/B","Bội số","Giá trị / CP","Chênh lệch"],[[m["method"],formatted(m["multiple"],"x"),formatted(m["target_price_vnd"],"VND/share"),formatted(m["difference_pct"],"%")] for m in val["pb_methods"]])
            if val.get("scenarios"):table(["Kịch bản P/B","P/B giả định","Giá trị / CP","Chênh lệch"],[[m["label"],formatted(m["target_pb"]),formatted(m["reference_price_vnd"],"VND/share"),formatted(m["difference_pct"],"%")] for m in val["scenarios"]])
            pe=val.get("pe",{})
            if pe.get("available"):
                text(pe["eps_basis"],True)
                table(["Kịch bản P/E năm","P/E giả định","Giá trị / CP","Chênh lệch"],[[m["label"],formatted(m["target_pe"]),formatted(m["reference_price_vnd"],"VND/share"),formatted(m["difference_pct"],"%")] for m in pe["scenarios"]])
                panel("sensitivity","Độ nhạy P/E × lợi nhuận: thay lợi nhuận giả định ±10% và bội số ±20%. Đây là giả định kiểm tra độ nhạy, không phải dự báo tăng trưởng.")
            dcf=val.get("dcf",{})
            if dcf.get("available"):
                text(dcf["formula"],True)
                table(["DCF FCFF","Giá trị"],[["FCFF năm gốc",formatted(dcf["cash_flow_base"],"VND")],["Giá trị doanh nghiệp",formatted(dcf["enterprise_value"],"VND")],["Tiền / Nợ vay / NCI"," / ".join(formatted(dcf[k],"VND") for k in ["cash","debt","nci"])],["Giá trị vốn",formatted(dcf["equity_value"],"VND")],["WACC / g dài hạn",f"{dcf['discount_rate_pct']:.2f}% / {dcf['perpetual_growth_pct']:.2f}%"]],keep=True)
            weighted=val.get("weighted_average",{})
            if weighted.get("available"):
                table(["Phương pháp tổng hợp","Tỷ trọng","Giá trị / CP","Đóng góp"],[[c["method"],formatted(c["weight_pct"],"%"),formatted(c["target_price_vnd"],"VND/share"),formatted(c["contribution_vnd"],"VND/share")] for c in weighted["components"]])
                text("Bình quân kịch bản: "+formatted(weighted["target_price_vnd"],"VND/share"));text(weighted["note"],True)
            method_sources=[]
            blocked_notes={}
            for key,label in [("gordon","Gordon"),("industry","P/B ngành"),("pe","P/E"),("dcf","DCF"),("weighted_average","Bình quân")]:
                method=val.get(key,{})
                if not method.get("available"):blocked_notes.setdefault(method.get("reason","Chưa đủ đầu vào."),[]).append(label)
                elif method.get("explanation") and key!="industry":text(label+": "+method["explanation"],True)
                method_sources.extend([r["source_id"] for r in method.get("inputs",[]) if r.get("source_id")])
            for reason,names in blocked_notes.items():left_cards.setdefault("valuation",[]).append(p(" / ".join(names)+": "+reason,True))
            citations(method_sources+[r["source_id"] for r in val.get("inputs",[]) if r.get("source_id")])

        else:text(val["reason"])
    if "valuation" in selected:
        start_section("valuation","Định giá và so sánh P/E - P/B")
        val=result["valuation"];primary=val.get("primary",{});benchmark=val.get("benchmark",{})
        if val.get("price_warning"):text(val["price_warning"],True)
        text("P/B hiện tại = giá / BVPS mẹ; P/E năm = giá / EPS mẹ năm quy đổi. Bội số mục tiêu lấy từ trung vị mẫu cùng kỳ/phạm vi và ngày giá; không dùng mức 1,5x/12x nhập tay như dữ liệu ngành.",True)
        if primary.get("available"):
            text(f"Phương pháp chính: {primary['selected_method']}. Giá tham chiếu {primary['target_price_vnd']:,.0f} VND/CP; chênh {primary['upside_pct']:+.2f}% so với đóng cửa.")
            text(primary["selection_reason"]);text(primary["methodology"],True)
            table(["Chỉ tiêu","Hiện tại","Trung vị","Chênh bội số","n"],[[c["label"],formatted(c["company_value"],"x"),formatted(c["sample_median"],"x"),formatted(c["premium_pct"],"%"),str(c["sample_size"])] for c in primary["comparisons"]])
            for c in primary["comparisons"]:text(c["label"]+": "+c["interpretation"],True)
            table(["Phương pháp","Bội số","Giá / CP","Chênh giá"],[[m["method"],formatted(m.get("multiple"),"x"),formatted(m["target_price_vnd"],"VND/share"),formatted(m.get("difference_pct"),"%")] for m in primary["methods"]])
            panel("valuation","Chỉ hiển thị các phương pháp định giá chính có đầu vào từ mẫu đồng kỳ. Giá tham chiếu không phải cam kết lợi suất.")
        else:text(primary.get("reason","Chưa đủ dữ liệu định giá chính có nguồn."))
        peers=benchmark.get("peers",[])
        if peers:
            heading("Doanh nghiệp so sánh")
            table(["Mã","P/E năm","P/B","ROE (%)","LNST YoY (%)"],[[r["ticker"]]+[formatted(r.get(k)) for k in ["pe","pb","roe","profit_growth"]] for r in peers])
            text(f"Kỳ {benchmark.get('period_end')}; ngày giá {benchmark.get('price_date')}; P/E n={benchmark.get('pe_sample_size',0)}, P/B n={benchmark.get('pb_sample_size',0)}. Mẫu không phải toàn ngành; P/E âm không được tính trung vị. Không trộn P/E năm với TTM hoặc dự phóng.",True)
        citations(primary.get("source_ids",[])+[i["source_id"] for r in peers for i in r.get("inputs",[]) if i.get("source_id")]+[i["source_id"] for i in val.get("inputs",[]) if i.get("source_id")])
        sotp=val.get("sotp",{})
        heading("SOTP: định giá từng mảng")
        text(sotp.get("reason","Chưa có dữ liệu từng mảng và điều chỉnh vốn có nguồn."),True)
        if sotp.get("available"):
            text(f"Nguồn mô hình: {sotp.get('provider')}; ngày {sotp['published_at']}. Bảng tham khảo lịch sử; không ghép giá mục tiêu cũ vào khuyến nghị hiện tại.",True)
            table(["Mảng","Giá trị (tỷ VND)","Cơ sở"],[[r["label"],formatted(r["value_vnd"]/1e9),r["method"]] for r in sotp["components"]])
            table(["Tính lại SOTP","Giá trị"],[["Tổng các mảng",formatted(sotp["enterprise_value"],"VND")],["Vốn sau điều chỉnh",formatted(sotp["equity_value"],"VND")],["Chiết khấu nguồn",formatted(sotp["discount_pct"],"%")],["CP của báo cáo",formatted(sotp["shares"],"CP")],["Giá tính lại / giá nguồn",formatted(sotp["target_price_vnd"],"VND/share")+" / "+formatted(sotp["reported_target"],"VND/share")]])
            text(sotp["basis"],True);citations(sotp["source_ids"])
        if full:text("Các giả định nhập tay và kiểm tra độ nhạy được đặt ở phụ lục sau phần Cơ hội và rủi ro.",True)
    if "news" in selected:
        start_section("news",SECTION_LABELS["news"])
        panel("news","Số mục trong mẫu tin đã lấy, không phải tổng số tin thị trường. Tin doanh nghiệp và tin mã cùng ngành được gắn nhãn; chưa đọc toàn văn để xác nhận tác động.")
        if not result["news"]:text("Nguồn chưa cung cấp tin phù hợp trước ngày phân tích.")
        selected_news=result["news"][:(8 if full else 3)]
        for item in selected_news:
            scope="Mã cùng ngành" if item.get("news_scope")=="industry_peer" else "Doanh nghiệp"
            label=f"{item['published_at']} | {item.get('ticker',request['ticker'])} | {scope}: {item['title']}"
            story.append(Paragraph(f'<a href={quoteattr(item["url"])} color="#14566e">{escape(label)}</a>',styles["BodyVN"]))
            if item.get("summary"):text(item["summary"][:200]+("…" if len(item["summary"])>200 else ""),True)
        citations([item.get("source_id") for item in selected_news])
        text("Danh sách công bố/sự kiện dùng để tra cứu. Chưa đọc toàn văn nên không suy diễn tác động đầu tư.",True)
    if "risks" in selected:
        start_section("risks",SECTION_LABELS["risks"])
        risk_start=len(story)
        recommendation=result.get("recommendation",{})
        if recommendation:
            heading("Khuyến nghị và luận điểm đầu tư")
            text(recommendation["stance"]);text(recommendation["reason"])
            text(f"Ngày chốt {recommendation['as_of']} · {recommendation['horizon']}",True)
            text(recommendation["confidence_note"],True)
            if recommendation.get("entry_ceiling_vnd"):
                text(f"Giá trần tham chiếu có điều kiện: {recommendation['entry_ceiling_vnd']:,.0f} VND/CP. Tính min(giá chính/1,15; giá thấp nhất của mô hình).")
            for item in recommendation["opportunities"]:
                story.append(Paragraph(escape(item["title"]),styles["EvidenceHeadingVN"]))
                text(item["evidence"]);text(item["implication"])
                text("Điều kiện xác nhận: "+item["catalyst"])
                text("Luận điểm không còn đúng khi: "+item["invalidation"],True)
                citations(item["source_ids"],"Kỳ "+item["period"])
            if not recommendation["opportunities"]:text("Chưa có luận điểm cơ hội đạt điều kiện dữ liệu. Ưu tiên bổ sung và kiểm chứng đầu vào.")
            citations(recommendation["source_ids"])
            if "valuation" in selected:panel("valuation","Định giá chính từ mẫu là đầu vào khuyến nghị nghiên cứu; cần đọc cả điều kiện xác nhận và các luận điểm bị bác bỏ bên phải.")
        matrix=result["conclusion"].get("risk_matrix",[])
        if matrix:
            table(["Rủi ro chính","Theo dõi"],[[r["evidence"],r["impact"]+". "+r["monitor"]] for r in matrix[:2]],sidebar=True)
            if matrix[2:]:table(["Bằng chứng / giới hạn","Tác động cần theo dõi","Điều kiện kiểm tra"],[[r["evidence"],r["impact"],r["monitor"]] for r in matrix[2:]],[60*mm,54*mm,60*mm])
            citations([sid for r in matrix for sid in r["source_ids"]])
        if "overview" not in selected:
            for item in result["conclusion"]["opportunities"]:text("• "+item)
        for item in result["conclusion"]["risks"]:
            if not recommendation or ("sụt giảm lớn" in item and "market" not in selected):text("• "+item)
    if full and "valuation" in selected:valuation_appendix()
    start_section("methods","Phương pháp và giới hạn dữ liệu")
    if "risks" in selected and result.get("recommendation"):
        text(result["recommendation"]["methodology"],True)
        for condition in result["recommendation"]["conditions"]:text("• "+condition,True)
    if "market" in selected:text("Giá dùng phiên trước ngày hiện tại để tránh phiên chưa kết thúc. Biểu đồ và MA luôn dùng Close của nguồn; giá mới nhất cho định giá là Close, không phải Adj Close. Biến động/drawdown/độ biến động dùng Adj Close nếu đầy đủ, nếu không dùng Close có nhãn chưa xác minh điều chỉnh quyền. Biến động = (giá cuối / đầu - 1) × 100; drawdown là mức giảm lớn nhất từ đỉnh trước đó; độ biến động năm hóa = độ lệch chuẩn lợi suất log ngày × √252 × 100. Đối chiếu giá không chứng nhận toàn bộ sự kiện quyền hay tổng lợi nhuận.",True)
    if "macro" in selected:text("Trích vĩ mô theo câu so sánh cụ thể (GDP lũy kế, CPI bình quân, tín dụng so với cuối năm, chỉ số USD cùng tháng); giữ khác biệt giữa YoY, YTD, danh nghĩa và thực. Dữ liệu WDI có null được bỏ, không lấy năm chưa kết thúc.",True)
    if full and "macro" in selected:
        history=[r for r in result.get("macro",{}).get("indicators",[]) if r["key"] in {"gdp_current_usd","lending_annual","fx_annual"}]
        if history:
            table(["Tham chiếu lịch sử","Giá trị","Kỳ"],[[r["label"],formatted(r["value"],r["unit"]),r["period"]] for r in history])
            citations([r["source_id"] for r in history])
    if "industry" in selected:text("Mẫu so sánh cùng phân ngành, ngày cuối kỳ, phạm vi và loại hình; ưu tiên 4 mã khác lớn nhất theo tổng tài sản trong kỳ. Trung vị tính riêng cho mỗi chỉ tiêu có ít nhất 2 giá trị hợp lệ, không gồm mã phân tích. Chênh lệch tỷ lệ là điểm phần trăm, không phải tăng trưởng tương đối. Chưa đối chiếu độc lập toàn bộ số liệu mẫu.",True)
    if "financial" in selected:
        for metric in result["financial"]["metrics"]:
            if metric["key"] not in {"revenue","net_profit","parent_profit","assets","equity","cfo","financial_loans","brokerage_revenue","lending_revenue","realized_pretax_profit","unrealized_pretax_profit"}:text(metric["label"]+": "+metric["formula"]+(". "+metric["reason"] if metric["reason"] else ""),True)
    if "valuation" in selected and result["valuation"]["available"]:text(result["valuation"]["formula"],True)
    displayed_warnings=set()
    vnf_warnings=set(result.get("vnfinancialdata",{}).get("warnings",[]))
    grouped_vnf={}
    for warning in sorted(vnf_warnings):
        period,_,issue=warning.partition("/")
        if period.isdigit() and issue:grouped_vnf.setdefault(issue,[]).append(period)
        else:grouped_vnf.setdefault(warning,[])
    for issue,periods in grouped_vnf.items():
        text("• vnfinancialdata: "+issue+(" (năm "+", ".join(periods)+")." if periods else ""),True)
    for warning in quality["warnings"]:
        if warning in vnf_warnings:continue
        if warning.startswith('KBS_') and ': loại kỳ ' in warning:
            warning='BCTC KBS: loại kỳ '+warning.split(': loại kỳ ',1)[1]
        if warning not in displayed_warnings:
            text("• "+warning,True);displayed_warnings.add(warning)
    for error in result["errors"]:text(f"Thiếu dữ liệu ({error['stage']}): {error['message']}",True)
    start_section("sources","Nguồn và khả năng truy vết")
    text("Bấm tên nguồn để mở URL gốc. Nguồn ở phần phân tích dùng tên đơn vị thay mã kỹ thuật; hồ sơ phân tích vẫn lưu đầy đủ URL, giá trị, kỳ, công thức và metadata.",True)
    source_rows=[]
    seen_sources=set()
    for source in result["sources"]:
        sid=source["source_id"]
        if sid not in used_sources and used_sources:continue
        url=source.get("url_or_file") or source.get("url") or ""
        identity=(url,source.get('page_or_table',''))
        if identity in seen_sources:continue
        seen_sources.add(identity)
        label=urlparse(url).netloc or Path(url).name
        link=Paragraph(f'<a href={quoteattr(url)} color="#14566e">{escape(label)}</a>',styles["SourceVN"]) if url.startswith("https://") else p(label,source=True)
        source_rows.append([p(source_label(source),source=True),[link,p("Truy xuất "+source.get("retrieved_at","")[:10]+" · "+source.get("page_or_table",""),source=True)]])
    if source_rows:
        sources_table=Table(source_rows,colWidths=[64*mm,110*mm],hAlign="LEFT")
        sources_table.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,-1),.3,colors.HexColor("#cedde3")),("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1)]))
        story.append(sources_table)
    seen=set()
    for check in quality["financial_check"].get("checks",[]):
        ref=check.get("url")
        if ref and ref not in seen:
            story.append(KeepTogether([p("Tài liệu đối chiếu: "+ref,source=True),p("Vị trí: "+check["locator"],source=True)]));seen.add(ref)
    text(f"Hồ sơ phân tích: {run_id}.",True)
    def footer(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor("#cedde3"));canvas.line(18*mm,17*mm,192*mm,17*mm)
        canvas.setFont("DV",7);canvas.setFillColor(colors.HexColor("#50646d"));canvas.drawString(18*mm,12*mm,f"StockInsight · {request['ticker']} · {request['as_of']}")
        canvas.drawRightString(192*mm,12*mm,f"Trang {doc.page}");canvas.restoreState()
    document=BaseDocTemplate(str(path),pagesize=(210*mm,297*mm),leftMargin=18*mm,rightMargin=18*mm,topMargin=18*mm,bottomMargin=23*mm,title=f"{request['ticker']} - Báo cáo phân tích",author="StockInsight")
    def page_renderer(section):
        def draw_page(canvas,doc):
            footer(canvas,doc)
            if section in full_width:return
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#cedde3"));canvas.line(77*mm,24*mm,77*mm,281*mm)
            canvas.setFont("DV-Bold",10);canvas.setFillColor(colors.HexColor("#14566e"))
            canvas.drawString(18*mm,279*mm,request["ticker"]+" | STOCKINSIGHT")
            top=270*mm
            notes=[p(SECTION_LABELS.get(section,"Tổng quan"),True),p("Chốt dữ liệu: "+request["as_of"],True)]
            for note in notes:
                _,height=note.wrap(left_width,500);note.drawOn(canvas,18*mm,top-height);top-=height+3
            for chart,note in left_panels.get(section,[]):
                iw,ih=ImageReader(str(chart)).getSize();height=ih/iw*left_width
                caption=p(note,True);_,caption_height=caption.wrap(left_width,500)
                if top-height-caption_height<28*mm:raise ValueError(f"Left-column figures overflow in {section}")
                canvas.drawImage(str(chart),18*mm,top-height,width=left_width,height=height,mask="auto")
                top-=height+4;caption.drawOn(canvas,18*mm,top-caption_height);top-=caption_height+12
            for card in left_cards.get(section,[]):
                _,height=card.wrapOn(canvas,left_width,top-28*mm)
                if top-height<28*mm:raise ValueError(f"Left-column cards overflow in {section}")
                card.drawOn(canvas,18*mm,top-height);top-=height
            if not left_panels.get(section) and not left_cards.get(section):
                note=p("Dữ liệu, điều kiện phân tích và giới hạn nguồn được trình bày ở cột bên phải. Không dựng biểu đồ khi chưa có số liệu phù hợp.",True)
                _,height=note.wrap(left_width,500);note.drawOn(canvas,18*mm,top-height)
            canvas.restoreState()
        return draw_page
    templates=[]
    for section in ["overview"]+[k for k in request["sections"] if k!="overview"]+(["valuation_appendix"] if full and "valuation" in selected else [])+["methods","sources"]:
        width=174*mm if section in full_width else right_width
        x=18*mm if section in full_width else 80*mm
        frame=Frame(x,23*mm,width,256*mm,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0,id=section)
        templates.append(PageTemplate(id=section,frames=[frame],onPage=page_renderer(section)))
    document.addPageTemplates(templates)
    document.build(story)
    return path
