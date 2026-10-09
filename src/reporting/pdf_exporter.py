"""Selectable Vietnamese PDF from the saved analysis result."""
from pathlib import Path
from urllib.parse import urlparse
import sys
from xml.sax.saxutils import escape, quoteattr
from src.models import SECTION_LABELS
from src.reporting.charts import market_chart, research_chart

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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak

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
    styles.add(ParagraphStyle(name="BodyVN",fontName="DV",fontSize=9,leading=14,spaceAfter=6,textColor=colors.HexColor("#263640")))
    styles.add(ParagraphStyle(name="SmallVN",parent=styles["BodyVN"],fontSize=8,leading=11.5,spaceAfter=3,wordWrap="CJK"))
    styles.add(ParagraphStyle(name="SourceVN",parent=styles["SmallVN"],fontSize=7.2,leading=10,spaceAfter=2))
    styles.add(ParagraphStyle(name="HeadingVN",parent=styles["BodyVN"],fontName="DV-Bold",fontSize=14,leading=19,spaceBefore=14,spaceAfter=9,keepWithNext=True,textColor=colors.HexColor("#14566e")))
    styles.add(ParagraphStyle(name="TitleVN",parent=styles["HeadingVN"],fontSize=26,leading=32,spaceBefore=0))
    story=[]
    def p(value,small=False,source=False):
        safe=str(value).translate(str.maketrans({"—":"-","–":"-","‑":"-","−":"-"}))
        return Paragraph(escape(safe).replace("\n","<br/>"),styles["SourceVN" if source else "SmallVN" if small else "BodyVN"])
    def text(value,small=False):story.append(p(value,small))
    def heading(value):story.append(Paragraph(escape(value),styles["HeadingVN"]))
    def table(headers,rows,widths=None,keep=False):
        if not rows:return
        cells=[[p(h,True) for h in headers]]+[[p(v,True) for v in row] for row in rows]
        t=Table(cells,colWidths=widths or [174*mm/len(headers)]*len(headers),repeatRows=1,hAlign="LEFT",rowSplitRange=(2,-2) if len(rows)>4 else None)
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e3eef2")),("VALIGN",(0,0),(-1,-1),"TOP"),
            ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LINEBELOW",(0,0),(-1,0),.7,colors.HexColor("#14566e")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f7f8")])]))
        if len(rows)<=4 or keep:story.append(KeepTogether([t,Spacer(1,6)]))
        else:story.extend([t,Spacer(1,6)])
    source_numbers={s["source_id"]:f"S{i+1:02}" for i,s in enumerate(result["sources"])}
    used_sources=set()
    def citations(ids, note=""):
        ids={i for i in ids if i in source_numbers};used_sources.update(ids)
        if ids:text("Nguồn: "+", ".join(sorted(source_numbers[i] for i in ids))+". "+note,True)
    def panel(kind,note):
        chart=research_chart(result,kind,path.parent/"charts")
        if chart:
            image_width,image_height=ImageReader(str(chart)).getSize()
            image=Image(str(chart),width=115*mm,height=image_height/image_width*115*mm)
            t=Table([[image,p(note,True)]],colWidths=[119*mm,55*mm])
            t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(0,0),0),("RIGHTPADDING",(0,0),(0,0),0),("BACKGROUND",(1,0),(1,0),colors.HexColor("#eef5f5")),("LEFTPADDING",(1,0),(1,0),9),("RIGHTPADDING",(1,0),(1,0),9),("TOPPADDING",(1,0),(1,0),8)]))
            story.extend([KeepTogether([t]),Spacer(1,9)])
    def ai_notes(section):
        ai=result.get("ai_commentary",{})
        for item in ai.get("sections",{}).get(section,[]):
            text("Nhận xét hỗ trợ AI: "+item["text"])
            for e in item.get("evidence",[]):
                value=e.get("value")
                caption=f"{e['label']}: "+(formatted(value,e.get("unit","")) if value is not None else f"mã {e.get('company_value')}; trung vị {e.get('sample_median')}; n={e.get('sample_size')}")
                text(caption+f" · Kỳ {e.get('period')} · Ngày chốt {ai.get('as_of')}",True)
            citations(item["source_ids"],f"AI {ai.get('model')}; tạo {ai.get('generated_at','')[:10]}; suy luận có điều kiện.")
    selected=set(request["sections"]);full=request["mode"]=="full"
    heading("STOCKINSIGHT")
    story.append(Paragraph(f"{escape(request['ticker'])} | Báo cáo phân tích",styles["TitleVN"]))
    text(f"{result['company'].get('name') or request['ticker']} · Ngày phân tích {request['as_of']}")
    text(f"Dữ liệu giá thực nhận: {result['market'].get('first_date', 'chưa xác định') if result['market'] else 'chưa có'} đến {result['market']['latest_date'] if result['market'] else 'chưa có'} · Chế độ: {'bản đầy đủ' if full else 'tóm tắt'}")
    text("Nội dung đã chọn: "+", ".join(SECTION_LABELS[k] for k in request["sections"]),True)
    text(result["conclusion"]["summary"])
    quality=result["quality"]
    labels={"matched":"Đã khớp nguồn thứ hai","unverified":"Chưa xác minh đầy đủ","matched_selected_fields":"Khớp các chỉ tiêu đã chọn","mismatch":"Có sai lệch — đã chặn","not_independently_checked":"Chưa đối chiếu độc lập","analyzed":"Đã phân tích","partial":"Thiếu một phần dữ liệu"}
    table(["Kiểm tra giá","Kiểm tra tài chính","Trạng thái"],[[labels.get(quality["price_check"]["status"],quality["price_check"]["status"]),labels.get(quality["financial_check"]["status"],quality["financial_check"]["status"]),labels.get(result["status"],result["status"])]])
    text("Các kiểm tra chỉ áp dụng cho số liệu và kỳ được nêu; không xác nhận toàn bộ lịch sử. Báo cáo dùng dữ liệu công khai và các giả định công bố bên dưới.",True)
    if "overview" in selected:
        heading(SECTION_LABELS["overview"])
        metric_map={m["key"]:m for m in result["financial"]["metrics"]}
        kpis=[]
        if result.get("market"):kpis.append(("Giá / "+result["market"]["latest_date"],formatted(result["market"]["latest_close_vnd"],"VND/share")))
        for key in ["net_profit","roe","cir" if result["financial"].get("industry_group")=="bank" else "net_profit_growth"]:
            m=metric_map.get(key)
            if m and m["value"] is not None:kpis.append((m["label"]+" / "+m["period"],formatted(m["value"],m["unit"])))
        if kpis:table([k[0] for k in kpis],[[k[1] for k in kpis]])

        text(f"Sàn: {result['company'].get('exchange') or 'chưa có'} · Website: {result['company'].get('website') or 'chưa có'}")
        business=result["company"].get("business") or "Nguồn chưa cung cấp mô tả doanh nghiệp."
        limit=300 if full else 200
        text(business if len(business)<=limit else business[:limit].rsplit(" ",1)[0]+"… (mô tả rút gọn từ nguồn)")
        thesis=result["conclusion"].get("integrated_thesis",[])
        preview=[i for i in thesis if i.startswith("Vĩ mô")][:1]+[i for i in thesis if i.startswith("Ngành")][:2]
        for item in preview[:(3 if full else 2)]:
            if (item.startswith("Vĩ mô") and "macro" in selected and "industry" in selected) or (item.startswith("Ngành") and "industry" in selected):text("• "+item)
        for item in result["conclusion"]["opportunities"][:2]:text("• "+item)
        if "macro" in selected and "industry" in selected:ai_notes("company_impact")
        citations([i["source_id"] for m in result["financial"]["metrics"] for i in m["inputs"] if i.get("source_id")]+[d["indicator"]["source_id"] for d in result.get("industry",{}).get("drivers",[])])
    if "macro" in selected:
        if full:story.append(PageBreak())
        heading(SECTION_LABELS["macro"])
        macro=result.get("macro",{})
        indicators=macro.get("indicators",[])
        chosen=indicators if full else [r for r in indicators if r["key"] in {"gdp_ytd","cpi_ytd","credit_growth","usd_index_yoy","gdp_annual","cpi_annual"}]
        table(["Chỉ tiêu","Giá trị","Kỳ tham chiếu","Công bố / cập nhật nguồn"],[[r["label"],formatted(r["value"],r["unit"]),r["period"],r.get("published_at") or "Cập nhật "+r.get("source_updated_at","")] for r in chosen],[69*mm,27*mm,38*mm,40*mm])
        panel("macro","Nền năm WDI dùng để nhìn xu hướng. Không ghép năm với chỉ tiêu lũy kế tháng thành cùng một chuỗi. Nguồn và kỳ được nêu ngay bên dưới.")
        citations([r["source_id"] for r in chosen]+[r["source_id"] for r in macro.get("annual_history",[]) if r["key"] in {"gdp_annual","cpi_annual"}])
        text(macro.get("assessment","Chưa có dữ liệu vĩ mô hợp lệ."))
        ai_notes("macro")
        text("NSO là dữ liệu báo cáo/ước tính có ngày công bố; WDI là nền năm, ngày cập nhật nguồn không phải ngày công bố lần đầu. Lãi suất cho vay lịch sử và tỷ giá bình quân năm không phải mức hiện tại. Không so trực tiếp các kỳ khác độ dài.",True)
    if "industry" in selected:
        if full:story.append(PageBreak())
        heading(SECTION_LABELS["industry"])
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
    if "market" in selected:
        if full:story.append(PageBreak())
        heading(SECTION_LABELS["market"]);market=result.get("market")
        if market:
            table(["Chỉ tiêu","Giá trị"],[["Đóng cửa / ngày",formatted(market["latest_close_vnd"],"VND/share")+" / "+market["latest_date"]],
                ["Biến động trong khoảng chọn",formatted(market["return_pct"],"%")],["Sụt giảm tối đa",formatted(market["max_drawdown_pct"],"%")],
                ["Biến động năm hóa",formatted(market["annualized_volatility_pct"],"%")],["MA20 / MA50",formatted(market["ma20_vnd"],"VND/share")+" / "+formatted(market["ma50_vnd"],"VND/share")],
                ["Khối lượng bình quân 20 phiên",formatted(market["average_volume_20"],"CP")]], [70*mm,104*mm])
            chart=market_chart(result,path.parent/"charts")
            if chart:story.append(Image(str(chart),width=174*mm,height=87*mm))
            citations([r["source_id"] for r in result["price_rows"] if r.get("source_id")]+[quality["price_check"].get("source_id")])
            text(market["return_note"],True);text(quality["price_check"].get("note","Không có đối chiếu giá."),True)
            differences=[c for c in quality["price_check"].get("checks",[]) if not c["match"]]
            if differences:table(["Ngày lệch nguồn","Yahoo (VND)","KBS (VND)","Sai lệch"],[[c["date"],formatted(c["yahoo_close"]),formatted(c["kbs_close"]),formatted(c["relative_difference"]*100,"%")] for c in differences])
        else:text("Chưa có chuỗi giá hợp lệ; không tính các chỉ tiêu thị trường.")
    if "financial" in selected:
        if full:story.append(PageBreak())
        heading(SECTION_LABELS["financial"]);metrics=result["financial"]["metrics"]
        if metrics:
            caption=p(f"Báo cáo năm {metrics[0]['period']}; tăng trưởng so với năm trước cùng phạm vi. Tiền quy đổi: tỷ VND.")
            caption.keepWithNext=True
            story.append(caption)
            panel("financial","Các cột thể hiện số liệu năm đã công bố, cùng phạm vi. "+("CFO ngân hàng phản ánh biến động tài sản/nợ hoạt động; không áp CFO/LNST của doanh nghiệp sản xuất." if result["financial"].get("industry_group")=="bank" else "So sánh lợi nhuận với CFO để theo dõi chuyển đổi thành tiền; cần đọc thay đổi vốn lưu động."))
            citations([r["source_id"] for m in metrics for r in m["inputs"] if r.get("source_id")])
            chosen=metrics if full else [m for m in metrics if m["key"] in {"revenue","net_profit","revenue_growth","net_profit_growth","roe","cash_conversion","net_interest_income","cir","roa"}]
            table(["Chỉ tiêu","Giá trị"],[[m["label"],formatted(m["value"],m["unit"])] for m in chosen],[100*mm,74*mm])
            if full:
                bank=result["financial"].get("industry_group")=="bank"
                income="net_interest_income" if bank else "revenue"
                table(["Năm","Thu nhập lãi thuần (tỷ)" if bank else "Doanh thu thuần (tỷ)","LNST hợp nhất (tỷ)","CFO (tỷ)"],[[str(year["year"])]+[formatted(year["fields"].get(k,{}).get("value"),"VND").replace(" tỷ VND","") for k in [income,"net_profit","cfo"]] for year in result["financial"]["periods"]])
        else:text("Chưa đủ dữ liệu tài chính có kỳ và phạm vi hợp lệ.")
        interim=result.get("interim")
        if interim and interim["valid"]:
            text(f"Cập nhật bán niên kết thúc {interim['period_end']} — OCR báo cáo hợp nhất soát xét HPG.")
            table(["Chỉ tiêu","6 tháng hiện tại (tỷ)","6 tháng cùng kỳ (tỷ)","Trang PDF"],[[label,formatted(interim["fields"][k]["value"],"VND").replace(" tỷ VND",""),formatted(interim["fields"][k]["previous"],"VND").replace(" tỷ VND",""),str(interim["fields"][k]["page"])] for k,label in [("revenue","Doanh thu thuần"),("net_profit","LNST hợp nhất"),("cfo","Dòng tiền kinh doanh")] if k in interim["fields"]])
            text(interim["note"],True)
        if full:
            names={"revenue":"Doanh thu thuần","net_profit":"LNST","assets":"Tài sản","equity":"Vốn chủ","liabilities":"Nợ phải trả"}
            table(["Đối chiếu / kỳ","Nguồn API (tỷ)","Tài liệu gốc (tỷ)","Kết quả"],[[names.get(c["metric"],c["metric"])+" / "+c["period"],formatted(c["actual_billion_vnd"]),formatted(c["reference_billion_vnd"]),"Khớp" if c["match"] else "Sai lệch"] for c in quality["financial_check"].get("checks",[])],keep=True)
    if "reference" in selected:
        if full:story.append(PageBreak())
        heading(SECTION_LABELS["reference"])
        reference=result.get("reference",{})
        text("Nguồn vn-annual-report-miner cung cấp lịch sử năm và danh mục BCTN. Parquet chưa có metadata chứng nhận đơn vị, phạm vi và ngày công bố; không dùng để thay tài chính/định giá chính.",True)
        citations([s["source_id"] for s in reference.get("sources",[])])
        grouped={}
        for record in reference.get("records",[]):grouped.setdefault(record["year"],{}).update(record["fields"])
        years=sorted(grouped,reverse=True)[:(5 if full else 2)]
        if years:
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
    if "valuation" in selected:
        if full:story.append(PageBreak())
        heading(SECTION_LABELS["valuation"]);val=result["valuation"]
        if val["available"]:
            text(val["assumption"])
            text(f"Kỳ tài chính {val['equity_period']}; số CP snapshot {val['shares_snapshot']}: {val['shares']:,.0f}.",True)
            a=val.get("assumptions",{})
            if a:text(f"Giả định: P/B {a['target_pb']:.2f}x; P/E {a['target_pe']:.2f}x; Ke {a['cost_of_equity']*100:.2f}%; WACC {a['wacc']*100:.2f}%; g dài hạn {a['terminal_growth']*100:.2f}%; tăng FCFF {a['forecast_growth']*100:.2f}%; thuế {a['tax_rate']*100:.2f}%.",True)
            if val.get("book_value_per_share") is not None:text(f"BVPS mẹ: {formatted(val['book_value_per_share'],'VND/share')} · P/B tham chiếu: {val['reference_pb']:.2f} lần.")
            panel("valuation","Giá trị kịch bản dùng giả định người dùng. Đường dọc là giá đóng cửa đã đối chiếu. Chênh lệch dương không tự tạo khuyến nghị mua.")
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
            for key,label in [("gordon","Gordon"),("industry","P/B ngành"),("pe","P/E"),("dcf","DCF"),("weighted_average","Bình quân")]:
                method=val.get(key,{})
                if not method.get("available"):text(label+": "+method.get("reason","Chưa đủ đầu vào."),True)
                elif method.get("explanation"):text(label+": "+method["explanation"],True)
                citations([r["source_id"] for r in method.get("inputs",[]) if r.get("source_id")])
            citations([r["source_id"] for r in val.get("inputs",[]) if r.get("source_id")])
            text(val["pe_status"],True)

        else:text(val["reason"])
    if "news" in selected:
        heading(SECTION_LABELS["news"])
        if not result["news"]:text("Nguồn chưa cung cấp tin phù hợp trước ngày phân tích.")
        for item in result["news"][:(12 if full else 3)]:text(item["published_at"]+" | "+item["title"]);text(item["url"],True)
        text("Danh sách công bố/sự kiện dùng để tra cứu. Chưa đọc toàn văn nên không suy diễn tác động đầu tư.",True)
    if "risks" in selected:
        risk_start=len(story)
        heading(SECTION_LABELS["risks"])
        matrix=result["conclusion"].get("risk_matrix",[])
        if matrix:
            table(["Bằng chứng / giới hạn","Tác động cần theo dõi","Điều kiện kiểm tra"],[[r["evidence"],r["impact"],r["monitor"]] for r in matrix],[60*mm,54*mm,60*mm])
            citations([sid for r in matrix for sid in r["source_ids"]])
        if "overview" not in selected:
            for item in result["conclusion"]["opportunities"]:text("• "+item)
        for item in result["conclusion"]["risks"]:text("• "+item)
        story[risk_start:]=[KeepTogether(story[risk_start:])]
    if full:story.append(PageBreak())
    heading("Phương pháp và giới hạn dữ liệu")
    if "market" in selected:text("Giá dùng phiên trước ngày hiện tại để tránh phiên chưa kết thúc. Biến động = (Adj Close cuối / đầu − 1) × 100; MA dùng chuỗi điều chỉnh chuẩn hóa về giá đóng cửa cuối. Drawdown = mức giảm lớn nhất từ đỉnh trước đó; biến động năm hóa = độ lệch chuẩn lợi suất log ngày × √252 × 100.",True)
    if "macro" in selected:text("Trích vĩ mô theo câu so sánh cụ thể (GDP lũy kế, CPI bình quân, tín dụng so với cuối năm, chỉ số USD cùng tháng); giữ khác biệt giữa YoY, YTD, danh nghĩa và thực. Dữ liệu WDI có null được bỏ, không lấy năm chưa kết thúc.",True)
    if "industry" in selected:text("Mẫu so sánh cùng phân ngành, ngày cuối kỳ, phạm vi và loại hình; ưu tiên 4 mã khác lớn nhất theo tổng tài sản trong kỳ. Trung vị tính riêng cho mỗi chỉ tiêu có ít nhất 2 giá trị hợp lệ, không gồm mã phân tích. Chênh lệch tỷ lệ là điểm phần trăm, không phải tăng trưởng tương đối. Chưa đối chiếu độc lập toàn bộ số liệu mẫu.",True)
    if "financial" in selected:
        for metric in result["financial"]["metrics"]:
            if metric["key"] not in {"revenue","net_profit","parent_profit","assets","equity","cfo"}:text(metric["label"]+": "+metric["formula"]+(". "+metric["reason"] if metric["reason"] else ""),True)
    if "valuation" in selected and result["valuation"]["available"]:text(result["valuation"]["formula"],True)
    for warning in quality["warnings"]:text("• "+warning,True)
    for error in result["errors"]:text(f"Thiếu dữ liệu ({error['stage']}): {error['message']}",True)
    if full:story.append(PageBreak())
    heading("Nguồn và khả năng truy vết")
    text("Bấm tên nguồn để mở URL gốc. Mã Sxx nối với nguồn tại từng bảng/biểu đồ. Hồ sơ phân tích lưu URL đầy đủ, giá trị, kỳ, công thức và metadata.",True)
    source_rows=[]
    for source in result["sources"]:
        sid=source["source_id"]
        if sid not in used_sources and used_sources:continue
        url=source.get("url_or_file") or source.get("url") or ""
        label=urlparse(url).netloc or Path(url).name
        link=Paragraph(f'<a href={quoteattr(url)} color="#14566e">{escape(label)}</a>',styles["SourceVN"]) if url.startswith("https://") else p(label,source=True)
        source_rows.append([p(source_numbers[sid]+" · "+sid.replace("_"+run_id,""),source=True),[link,p("Truy xuất "+source.get("retrieved_at","")[:10]+" · "+source.get("page_or_table",""),source=True)]])
    if source_rows:
        sources_table=Table(source_rows,colWidths=[64*mm,110*mm],hAlign="LEFT")
        sources_table.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,-1),.3,colors.HexColor("#cedde3")),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
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
    document=SimpleDocTemplate(str(path),pagesize=(210*mm,297*mm),leftMargin=18*mm,rightMargin=18*mm,topMargin=18*mm,bottomMargin=23*mm,title=f"{request['ticker']} - Báo cáo phân tích",author="StockInsight")
    document.build(story,onFirstPage=footer,onLaterPages=footer)
    return path
