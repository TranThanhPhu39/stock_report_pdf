"""StockInsight: request → automatic acquisition → analysis → selected PDF."""
from __future__ import annotations
from datetime import date, datetime, timedelta
from pathlib import Path
import html
import json
import pandas as pd
import streamlit as st
from src.analysis.news import build_news_digest
from src.analysis.ai_commentary import resolve_key
from src.analysis.price_quality import latest_price_matches
from src.data.providers import VN_TIME, download
from src.data.research import company_news_url, parse_company_news
from src.models import SECTION_LABELS
from src.pipeline import run_analysis
from src.reporting.pdf_exporter import generate_report, formatted

ROOT=Path(__file__).resolve().parent
today=datetime.now(VN_TIME).date()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_news_preview(ticker: str, as_of: date) -> list[dict]:
    url=company_news_url(ticker)
    payload=json.loads(download(url,timeout=6))
    return parse_company_news(payload,ticker,f"KBS_news_preview_{ticker}",as_of)


st.set_page_config(page_title="StockInsight",layout="wide",initial_sidebar_state="collapsed")
st.markdown("""
<style>
:root { --ink:#173532; --ink-soft:#37544e; --jade:#087e72; --brass:#c7a96b; --paper:#eef4f1; --line:#d9e4df; }
.stApp { background-color:var(--paper); background-image:repeating-linear-gradient(0deg,transparent,transparent 39px,rgba(23,53,50,.022) 40px),repeating-linear-gradient(90deg,transparent,transparent 39px,rgba(23,53,50,.022) 40px); }
[data-testid="stHeader"] { background:transparent; }
.block-container { max-width:1320px; padding-top:1.6rem; padding-bottom:4rem; }
.masthead { position:relative; overflow:hidden; padding:23px 32px 21px; margin:0 0 26px; color:var(--ink); background:rgba(255,255,255,.64); border:1px solid rgba(255,255,255,.95); border-top:2px solid var(--brass); border-radius:4px; box-shadow:0 14px 38px rgba(34,67,61,.08); backdrop-filter:blur(18px); }
.masthead:after { content:""; position:absolute; top:0; right:0; width:29%; height:100%; opacity:.12; background:repeating-linear-gradient(135deg,transparent 0 12px,#549a8d 13px 14px); pointer-events:none; }
.masthead__eyebrow,.masthead__footer { display:flex; justify-content:space-between; align-items:center; gap:14px; position:relative; z-index:1; font-size:12px; color:#58716b; }
.masthead__eyebrow strong { color:var(--jade); font-weight:650; }
.masthead__title { position:relative; z-index:1; margin:20px 0 18px; color:var(--ink); font:500 48px/1.08 Georgia,"Times New Roman",serif; }
.masthead__footer { padding-top:13px; border-top:1px solid rgba(47,91,81,.15); }
.step-heading { display:flex; align-items:flex-start; gap:14px; margin:10px 0 18px; color:var(--ink); }
.step-heading__number { padding-top:3px; color:var(--brass); font:600 13px/1.4 "SFMono-Regular",Consolas,monospace; }
.step-heading__title { font-size:20px; line-height:1.25; font-weight:650; }
.step-heading__note { margin-top:4px; font-size:12px; color:#657873; }
.brief-panel { position:relative; overflow:hidden; padding:27px 27px 23px; color:var(--ink); background:rgba(255,255,255,.62); border:1px solid rgba(255,255,255,.96); border-radius:4px; box-shadow:0 16px 42px rgba(34,67,61,.09); backdrop-filter:blur(20px); }
.brief-kicker { display:flex; align-items:center; gap:9px; color:#58736c; font-size:11px; }
.brief-pip { width:8px; height:8px; flex:0 0 8px; border-radius:50%; background:#54b7a3; box-shadow:0 0 0 4px rgba(84,183,163,.13); }
.brief-ticker { margin:24px 0 5px; color:var(--ink); font:500 48px/1 Georgia,"Times New Roman",serif; }
.brief-company { color:#687d77; font-size:13px; }
.brief-period { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:23px 0 19px; padding:15px 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line); }
.brief-period span { display:block; color:#71847f; font-size:10px; margin-bottom:5px; }
.brief-period strong { color:var(--ink-soft); font-size:13px; font-weight:600; }
.brief-section-label { margin:20px 0 9px; color:#71847f; font-size:10px; }
.brief-row { display:flex; align-items:center; gap:10px; min-height:37px; border-bottom:1px solid rgba(215,224,220,.7); color:#34504b; font-size:13px; }
.brief-row__index { width:21px; color:#b69a5c; font:600 11px "SFMono-Regular",Consolas,monospace; }
.brief-empty { padding:14px 0; color:#71847f; font-size:13px; }
.brief-count { margin-top:18px; padding-top:14px; border-top:1px solid var(--line); color:#60756f; font-size:11px; }
.brief-count strong { color:var(--jade); font-size:15px; }
.news-digest { position:relative; overflow:hidden; margin:0 0 24px; padding:23px 26px; color:var(--ink); background:linear-gradient(135deg,rgba(255,255,255,.82),rgba(232,245,240,.56)); border:1px solid rgba(255,255,255,.94); border-radius:4px; box-shadow:0 16px 38px rgba(34,67,61,.10),inset 0 1px 0 rgba(255,255,255,.95); backdrop-filter:blur(24px) saturate(1.25); }
.news-digest:before { content:""; position:absolute; top:0; left:26px; right:26px; height:1px; background:linear-gradient(90deg,transparent,rgba(255,255,255,.95),transparent); }
.news-digest__kicker { margin:0 0 7px; color:var(--jade); font-size:11px; }
.news-digest__title { margin:0 0 8px; color:var(--ink); font-size:21px; font-weight:650; }
.news-digest__summary { margin:0 0 13px; color:#526963; font-size:14px; line-height:1.55; }
.news-digest__item { display:flex; align-items:baseline; gap:12px; padding:9px 0; border-top:1px solid rgba(217,228,223,.74); color:#34504b; font-size:14px; }
.news-digest__date { flex:0 0 82px; color:#71847f; font-size:12px; }
.news-digest__item a { color:var(--ink-soft); text-decoration:none; }
.news-digest__item a:hover { color:var(--jade); text-decoration:underline; }
.news-digest__note { margin-top:12px; color:#71847f; font-size:11px; }
.news-digest__group { margin-top:15px; }
.news-digest__day { display:flex; align-items:center; justify-content:space-between; padding:8px 0; color:var(--jade); font-size:12px; font-weight:650; border-bottom:1px solid rgba(8,126,114,.20); }
.news-digest__article { padding:11px 0 12px; border-bottom:1px solid rgba(217,228,223,.72); }
.news-digest__article a { color:var(--ink); font-size:14px; font-weight:600; text-decoration:none; }
.news-digest__article a:hover { color:var(--jade); text-decoration:underline; }
.news-digest__excerpt { margin:6px 0 0; color:#526963; font-size:13px; line-height:1.5; }
.news-digest__source { margin-top:5px; color:#82928e; font-size:10px; }
[data-testid="stMetric"] { background:rgba(255,255,255,.88); border:1px solid var(--line); border-top:2px solid var(--jade); padding:16px 18px; }
[data-testid="stMetricLabel"] { color:#536963; }
[data-testid="stMetricValue"] { color:var(--ink); }
@media(max-width:700px) { .block-container{padding:1rem 1rem 3rem}.masthead{padding:20px 19px;margin-bottom:20px}.masthead__eyebrow,.masthead__footer{align-items:flex-start;flex-direction:column;gap:6px}.masthead__title{font-size:42px}.step-heading__title{font-size:18px}.brief-panel{margin-top:10px;padding:23px 20px}.brief-ticker{font-size:42px}.news-digest{padding:19px 17px}.news-digest__item{align-items:flex-start;flex-direction:column;gap:4px}.news-digest__date{flex:auto} }
</style>
""",unsafe_allow_html=True)
st.markdown(f"""
<header class="masthead">
    <div class="masthead__eyebrow"><strong>VIETNAM EQUITY RESEARCH</strong><span>RESEARCH DESK · 01</span></div>
    <div class="masthead__title">StockInsight</div>
    <div class="masthead__footer"><span>BÁO CÁO CƠ HỘI ĐẦU TƯ CỔ PHIẾU</span><span>Ngày báo cáo · {today.strftime('%d/%m/%Y')}</span></div>
</header>
""",unsafe_allow_html=True)
request_column,brief_column=st.columns([1.25,.75],gap="large")
with request_column:
    st.markdown("<div class='step-heading'><span class='step-heading__number'>01</span><div><div class='step-heading__title'>Cổ phiếu và thời gian</div><div class='step-heading__note'>MÃ GIAO DỊCH · KHOẢNG PHÂN TÍCH</div></div></div>",unsafe_allow_html=True)
    cols=st.columns(3)
    ticker=cols[0].text_input("Mã cổ phiếu",value="HPG",help="Nhập mã niêm yết, ví dụ HPG, FPT hoặc VNM.")
    start=cols[1].date_input("Từ ngày",value=today-timedelta(days=365),max_value=today-timedelta(days=1))
    as_of=cols[2].date_input("Ngày phân tích",value=today,max_value=today)

    st.markdown("<div class='step-heading' style='margin-top:28px'><span class='step-heading__number'>02</span><div><div class='step-heading__title'>Kiểu báo cáo</div><div class='step-heading__note'>CHỌN MỨC ĐỘ CHI TIẾT VÀ NỘI DUNG XUẤT</div></div></div>",unsafe_allow_html=True)
    mode=st.radio("Độ chi tiết",["Đầy đủ","Tóm tắt"],horizontal=True,captions=["Nhiều chỉ tiêu và giải thích","Các điểm chính, ngắn gọn"])
    with st.expander("Tuỳ chỉnh nội dung PDF"):
        section_cols=st.columns(3)
        sections=[]
        for index,(section,label) in enumerate(SECTION_LABELS.items()):
            if section_cols[index%len(section_cols)].checkbox(label,value=True,key=f"pdf_section_{section}"):
                sections.append(section)
    with st.expander("Tuỳ chọn nâng cao"):
        target_pb=st.number_input("P/B cơ sở giả định",min_value=0.1,max_value=20.0,value=1.5,step=0.1,help="Dùng làm giả định cho kịch bản định giá; không phải khuyến nghị mua/bán.")
    with st.expander("Giả định định giá: P/E, Gordon và DCF"):
        vc=st.columns(3)
        target_pe=vc[0].number_input("P/E năm giả định",min_value=.1,max_value=100.,value=12.,step=.5)
        cost_of_equity=vc[1].number_input("Chi phí vốn chủ Ke (%)",min_value=.1,max_value=99.,value=11.5,step=.5)/100
        terminal_growth=vc[2].number_input("Tăng trưởng dài hạn g (%)",min_value=0.,max_value=20.,value=3.5,step=.5)/100
        vc=st.columns(3)
        wacc=vc[0].number_input("WACC cho FCFF (%)",min_value=.1,max_value=99.,value=10.,step=.5)/100
        forecast_growth=vc[1].number_input("Tăng trưởng FCFF 3 năm (%)",min_value=-50.,max_value=50.,value=7.,step=.5)/100
        tax_rate=vc[2].number_input("Thuế suất giả định (%)",min_value=0.,max_value=99.,value=20.,step=1.)/100
        st.caption("Các tỷ lệ trên là giả định do người dùng chọn. DCF chỉ áp cho doanh nghiệp phi tài chính có FCFF và đầu vào đầy đủ. EPS năm quy đổi không phải EPS công bố/TTM.")
    use_ai=st.checkbox("Gemini hỗ trợ nhận xét từ dữ liệu và nguồn",value=False,help="Cần GEMINI_API_KEY trong Streamlit Secrets hoặc environment. Gửi số liệu công khai đã thu thập cho Gemini; nếu thiếu key hoặc lỗi, vẫn tạo báo cáo bằng quy tắc.")
    submitted=st.button("Phân tích và tạo PDF",type="primary",use_container_width=True,key="run_analysis")

with brief_column:
    selected_labels=[SECTION_LABELS[section] for section in sections]
    section_rows="".join(
        f'<div class="brief-row"><span class="brief-row__index">{index:02d}</span><span>{html.escape(label)}</span></div>'
        for index,label in enumerate(selected_labels[:5],1)
    )
    if len(selected_labels)>5:
        section_rows+=f'<div class="brief-empty">và {len(selected_labels)-5} mục khác</div>'
    if not section_rows:
        section_rows='<div class="brief-empty">Chưa chọn nội dung PDF</div>'
    mode_label="Đầy đủ" if mode=="Đầy đủ" else "Tóm tắt"
    st.markdown(f"""
    <aside class="brief-panel">
    <div class="brief-kicker"><span class="brief-pip"></span>REPORT BRIEF · PREVIEW</div>
      <div class="brief-ticker">{html.escape(ticker.strip().upper() or "—")}</div>
      <div class="brief-company">Báo cáo cơ hội đầu tư · Việt Nam</div>
      <div class="brief-period">
        <div><span>TỪ NGÀY</span><strong>{start.strftime('%d/%m/%Y')}</strong></div>
        <div><span>NGÀY PHÂN TÍCH</span><strong>{as_of.strftime('%d/%m/%Y')}</strong></div>
      </div>
      <div class="brief-section-label">NỘI DUNG ĐƯỢC CHỌN</div>
      {section_rows}
      <div class="brief-count"><strong>{len(selected_labels)}</strong> mục · Bản {mode_label}</div>
    </aside>
    """,unsafe_allow_html=True)

current_signature=(ticker.strip().upper(),start.isoformat(),as_of.isoformat(),mode,tuple(sections),target_pb,target_pe,cost_of_equity,terminal_growth,wacc,forecast_growth,tax_rate,use_ai)
if submitted:
    st.session_state.pop("analysis_result",None)
    st.session_state.pop("report_path",None)
    if not sections:
        st.error("Hãy chọn ít nhất một nội dung cho báo cáo PDF.")
    else:
        try:
            with st.spinner("Đang lấy dữ liệu, đối chiếu nguồn, phân tích và tạo PDF… Lần đầu đọc PDF scan có thể mất vài phút."):
                key=resolve_key(secrets=st.secrets) if use_ai else None
                result=run_analysis(ticker,start,as_of,mode="full" if mode=="Đầy đủ" else "summary",sections=sections,target_pb=target_pb,target_pe=target_pe,cost_of_equity=cost_of_equity,terminal_growth=terminal_growth,wacc=wacc,forecast_growth=forecast_growth,tax_rate=tax_rate,use_ai=use_ai,ai_key=key)
                if not result["market"] and not result["financial"]["metrics"]:
                    st.error("Không lấy được dữ liệu hợp lệ. Kiểm tra mã cổ phiếu hoặc thử lại khi nguồn truy cập được.")
                    for error in result["errors"]:st.warning(error["message"])
                else:
                    st.session_state["analysis_result"]=result
                    st.session_state["report_path"]=str(generate_report(result))
                    st.session_state["analysis_input_signature"]=current_signature
        except (ValueError,OSError,RuntimeError) as exc:
            st.error(f"Không thể hoàn tất yêu cầu: {exc}")
result=st.session_state.get("analysis_result")
if result and st.session_state.get("analysis_input_signature") != current_signature:
    st.session_state.pop("analysis_result",None)
    st.session_state.pop("report_path",None)
    result=None
if result:
    request=result["request"];acquisition=result["acquisition"]
    st.subheader(f"Kết quả {request['ticker']}")
    st.caption(f"Ngày phân tích {request['as_of']} · Dữ liệu giá đến {result['market']['latest_date'] if result['market'] else 'chưa có'}")
    if st.session_state.get("report_path"):
        path=Path(st.session_state["report_path"])
        st.download_button("Tải báo cáo phân tích PDF",path.read_bytes(),file_name=path.name,mime="application/pdf",type="primary")
    news_items=result.get("news",[])
    company_news=[item for item in news_items if item.get("news_scope","company")=="company"]
    peer_news=[item for item in news_items if item.get("news_scope")=="industry_peer"]
    selected_news=company_news
    if peer_news:
        company_label=f"Mã {request['ticker']} ({len(company_news)})"
        sector_name=result.get("industry",{}).get("name") or "cùng ngành"
        peer_label=f"Mẫu {sector_name} ({len(peer_news)})"
        news_scope=st.radio("Phạm vi tin",[company_label,peer_label],horizontal=True,
                            key=f"news_scope_{request['ticker']}",label_visibility="collapsed")
        if news_scope==peer_label:
            selected_news=peer_news
    digest=build_news_digest(selected_news)
    news_groups=[]
    for group in digest["groups"]:
        article_rows=[]
        for item in group["articles"]:
            title=html.escape(item["title"])
            if item.get("news_scope")=="industry_peer" and item.get("ticker"):
                title=f"{html.escape(item['ticker'])} · {title}"
            url=item.get("url","")
            if url.startswith(("https://","http://")):
                title_markup=f'<a href="{html.escape(url,quote=True)}" target="_blank" rel="noopener noreferrer">{title}</a>'
            else:
                title_markup=title
            excerpt=html.escape(item.get("summary") or "Feed chưa cung cấp trích yếu cho tin này.")
            source_label="TRÍCH YẾU KBS" if item.get("summary") else "CHỈ CÓ TIÊU ĐỀ"
            if item.get("news_scope")=="industry_peer":
                source_label=f"TIN PEER · {source_label}"
            article_rows.append(
                f'<article class="news-digest__article"><div>{title_markup}</div>'
                f'<p class="news-digest__excerpt">{excerpt}</p>'
                f'<div class="news-digest__source">{source_label}</div></article>'
            )
        group_date=html.escape(group["date"])
        news_groups.append(
            f'<div class="news-digest__group"><div class="news-digest__day">'
            f'<span>{group_date}</span><span>{len(group["articles"])} tin</span></div>'
            f'{"".join(article_rows)}</div>'
        )
    news_markup="".join(news_groups) or '<div class="news-digest__item">Chưa có tin phù hợp trong dữ liệu nguồn.</div>'
    st.markdown(f"""
    <section class="news-digest">
    <div class="news-digest__kicker">TIN TỨC DOANH NGHIỆP · NHÓM THEO NGÀY</div>
      <h3 class="news-digest__title">Tổng hợp tin tức tài chính</h3>
      <p class="news-digest__summary">{html.escape(digest["summary"])}</p>
      {news_markup}
    <div class="news-digest__note">Trích yếu lấy từ feed KBS khi có; mở tiêu đề để đọc bài gốc. Đây không phải đánh giá tác động giá.</div>
    </section>
    """,unsafe_allow_html=True)
    for error in result["errors"]:st.warning(f"Dữ liệu chưa đủ ({error['stage']}): {error['message']}")
    for warning in acquisition.get("warnings",[]):st.warning(warning)
    ai=result.get("ai_commentary",{})
    if request.get("use_ai") and not ai.get("available"):st.info(ai.get("reason","AI chưa có nhận xét hợp lệ."))
    market=result.get("market")
    if market:
        cols=st.columns(4)
        for col,label,key,unit in zip(cols,["Giá đóng cửa","Biến động khoảng chọn","Sụt giảm tối đa","MA20"],["latest_close_vnd","return_pct","max_drawdown_pct","ma20_vnd"],["VND/share","%","%","VND/share"]):
            display="Không tính" if key!="latest_close_vnd" and not market.get("history_indicators_available",True) else formatted(market[key],unit)
            col.metric(label,display)
            if display=="Không tính":col.caption("Lịch sử chưa khớp")
        price_check=result["quality"]["price_check"]
        if latest_price_matches(price_check,market):st.success(f"Giá đóng cửa mới nhất {market['latest_close_vnd']:,.0f} VND ngày {market['latest_date']} đã khớp hai nguồn để đối chiếu định giá.")
        else:st.warning("Giá đóng cửa mới nhất chưa khớp nguồn thứ hai đúng ngày; định giá bị chặn.")
        if price_check["status"]=="matched":st.caption(f"Mẫu lịch sử: khớp {len(price_check['checks'])}/{price_check.get('expected_count',len(price_check['checks']))} phiên; không xác nhận toàn bộ lịch sử điều chỉnh.")
        else:st.warning(f"Mẫu lịch sử chưa khớp đầy đủ: {price_check.get('matched_count',sum(c['match'] for c in price_check.get('checks',[])))}/{price_check.get('expected_count',20)} phiên khớp. Hạn chế MA, lợi suất, drawdown và biến động năm hóa; kiểm tra giá mới nhất được tách riêng.")
        prices=pd.DataFrame(result["price_rows"])
        chart=pd.DataFrame({"Ngày":pd.to_datetime(prices["date"]),market["series_basis"]:market["chart_prices"]}).set_index("Ngày")
        st.line_chart(chart)
        st.caption(market["return_note"])
    context_tabs=st.tabs(["Tổng quan vĩ mô","Phân tích ngành"])
    with context_tabs[0]:
        macro=result.get("macro",{})
        rows=macro.get("indicators",[])
        if rows:
            st.dataframe(pd.DataFrame([{"Chỉ tiêu":r["label"],"Giá trị":formatted(r["value"],r["unit"]),"Kỳ":r["period"],"Công bố / cập nhật":r.get("published_at") or "Cập nhật "+r.get("source_updated_at","")} for r in rows]),hide_index=True,width="stretch")
            st.write(macro.get("assessment",""))
            st.caption("Các kỳ riêng biệt; số liệu năm WDI không thay số liệu tháng. Lãi suất/tỷ giá bình quân lịch sử không phải mức hiện tại.")
        else:st.warning("Chưa lấy được dữ liệu vĩ mô hợp lệ.")
    with context_tabs[1]:
        industry=result.get("industry",{})
        if industry.get("available"):
            st.write(f"**{industry['name']}** · {industry.get('taxonomy','KBS')}")
            st.caption(f"{len(industry['members'])} thành viên · Kỳ so sánh {industry.get('period_end','chưa có')} · Mẫu: {', '.join(p['ticker'] for p in industry['peers']) or 'chưa đủ'}")
            st.caption(industry["selection"])
            comparisons=industry.get("comparisons",[])
            if comparisons:
                st.dataframe(pd.DataFrame([{"Chỉ tiêu":c["label"],"Mã phân tích":formatted(c["company_value"],c["unit"]),"Trung vị mẫu":formatted(c["sample_median"],c["unit"]),"Chênh lệch":formatted(c["difference"],"điểm %" if c["unit"]=="%" else c["unit"]),"Số mẫu":c["sample_size"]} for c in comparisons]),hide_index=True,width="stretch")
            else:st.warning("Chưa đủ chỉ tiêu đồng kỳ của ít nhất hai doanh nghiệp để tính trung vị.")
            for driver in industry.get("drivers",[]):
                row=driver["indicator"];st.write(f"• {row['label']}: {row['value']:.2f}% ({row['period']}). "+driver["channel"])
            for risk in industry.get("structural_risks",[]):st.caption(risk)
            with st.expander("Phạm vi mẫu và mã bị loại"):
                st.json({"coverage":industry.get("coverage"),"excluded":industry.get("excluded"),"eligible_candidates":industry.get("eligible_candidates")})
        else:st.warning("Nguồn chưa xác nhận phân ngành của mã này; không tự gán ngành.")
    tabs=st.tabs(["Tài chính","Định giá đa phương pháp","Cơ hội và rủi ro","Tin tức","Nguồn dữ liệu"])
    with tabs[0]:
        if result["financial"]["metrics"]:
            st.caption(f"Báo cáo năm {result['financial']['metrics'][0]['period']}; không phải số liệu TTM.")
            st.dataframe(pd.DataFrame([{"Chỉ tiêu":m["label"],"Giá trị":formatted(m["value"],m["unit"])} for m in result["financial"]["metrics"]]),hide_index=True,width="stretch")
        else:st.info("Chưa có chỉ tiêu tài chính đủ điều kiện tính toán.")
        interim=result.get("interim")
        if interim and interim["valid"]:
            st.write(f"**Bán niên HPG đến {interim['period_end']}**")
            st.dataframe(pd.DataFrame([{"Chỉ tiêu":label,"Hiện tại":formatted(interim["fields"][key]["value"],"VND"),"6 tháng cùng kỳ":formatted(interim["fields"][key]["previous"],"VND"),"Trang PDF":interim["fields"][key]["page"]} for key,label in [("revenue","Doanh thu thuần"),("net_profit","LNST"),("cfo","Dòng tiền kinh doanh")]]),hide_index=True,width="stretch")
        reference=result.get("reference",{})
        with st.expander("Nguồn bổ sung: Parquet và báo cáo thường niên",expanded=True):
            st.caption("Giá trị Parquet là giá trị gốc; đơn vị, phạm vi và ngày công bố chưa được chứng nhận. Không dùng để tự thay tài chính/định giá chính.")
            reference_rows=[{"Năm":record["year"],"Chỉ tiêu":field["source_label"],"Giá trị gốc":field["value"],"Đơn vị":"Chưa xác minh","Phạm vi":record["scope"],"Nguồn":field["source_id"],"Mã chỉ tiêu":field["source_field"],"File gốc":field["source_file"],"Sheet gốc":field["source_sheet"]} for record in reference.get("records",[]) for field in record["fields"].values()]
            if reference_rows:
                ref_frame=pd.DataFrame(reference_rows)
                st.dataframe(ref_frame,hide_index=True,width="stretch")
                st.download_button("Tải dữ liệu tài chính bổ sung CSV",ref_frame.to_csv(index=False).encode("utf-8-sig"),file_name=f"{request['ticker']}_reference_financials.csv",mime="text/csv")
            checks=reference.get("checks",[])
            if checks:
                st.write("Đối chiếu giá trị cùng năm — chưa chứng nhận phạm vi hay nguồn độc lập")
                st.dataframe(pd.DataFrame([{"Năm":c["year"],"Chỉ tiêu":c["label"],"Nguồn chính (VND)":c["primary_vnd"],"Parquet (gốc)":c["reference_raw"],"Sai lệch (%)":c["relative_difference"]*100,"Kết quả":"Khớp giá trị" if c["match"] else "Lệch"} for c in checks]),hide_index=True,width="stretch")
            for report in reference.get("reports",[]):
                st.caption(f"BCTN {report['year']} · {report['file_name']} · SHA256 {report['sha256'][:12]}…")
                if report.get("file"):
                    original=ROOT/report["file"]
                    st.download_button(f"Tải BCTN gốc {report['year']}",original.read_bytes(),file_name=report["file_name"],mime="application/pdf",key=f"reference_pdf_{report['record_id']}")
                    st.caption(f"{report['inspection']['pages']} trang; {report['inspection']['text_pages']} trang đọc được text. Checksum đã khớp danh mục.")
                    if report["inspection"]["status"]!="text_available":st.caption("Báo cáo chứa nhiều trang scan; cần OCR thêm trước khi tự trích/kiểm chứng số liệu.")
            for error in reference.get("errors",[]):st.warning(error["message"])
            if not reference.get("available"):st.info("Chưa có dữ liệu bổ sung đủ điều kiện theo phiên bản nguồn/ngày phân tích/sàn.")
    with tabs[1]:
        val=result["valuation"]
        if val["available"]:
            if val.get("price_warning"):st.warning(val["price_warning"])
            if val.get("book_value_per_share") is not None:st.caption(f"BVPS mẹ {formatted(val['book_value_per_share'],'VND/share')} · P/B tham chiếu {val['reference_pb']:.2f} lần")
            if val.get("pb_methods"):st.dataframe(pd.DataFrame(val["pb_methods"]),hide_index=True,width="stretch")
            if val.get("scenarios"):st.dataframe(pd.DataFrame([{"Kịch bản":s["label"],"P/B giả định":s["target_pb"],"Giá trị quy đổi":formatted(s["reference_price_vnd"],"VND/share"),"Chênh lệch":formatted(s["difference_pct"],"%")} for s in val["scenarios"]]),hide_index=True,width="stretch")
            for method,label in [("gordon","P/B Gordon"),("industry","P/B mẫu ngành"),("pe","P/E lợi nhuận năm quy đổi"),("dcf","DCF FCFF"),("weighted_average","Bình quân trọng số")]:
                data=val.get(method,{})
                with st.expander(label,expanded=bool(data.get("available"))):
                    if data.get("available"):
                        if data.get("scenarios"):st.dataframe(pd.DataFrame(data["scenarios"]),hide_index=True,width="stretch")
                        if data.get("components"):st.dataframe(pd.DataFrame(data["components"]),hide_index=True,width="stretch")
                        target=data.get("target_price_vnd",data.get("base_price_vnd",data.get("per_share_price_vnd")))
                        if target is not None:st.metric("Giá trị kịch bản / CP",formatted(target,"VND/share"))
                        st.caption(data.get("eps_basis") or data.get("explanation") or data.get("formula") or data.get("note", ""))
                    else:st.info(data.get("reason","Chưa đủ đầu vào."))
            st.info(val["assumption"])
        else:st.info(val["reason"])
    with tabs[2]:
        st.write("**Luận điểm vĩ mô → ngành → doanh nghiệp**")
        for item in result["conclusion"].get("integrated_thesis",[]):st.write("• "+item)
        st.write("**Cơ hội / điều kiện theo dõi**")
        for item in result["conclusion"]["opportunities"]:st.write("• "+item)
        st.write("**Rủi ro**")
        if result["conclusion"].get("risk_matrix"):
            st.dataframe(pd.DataFrame([{ "Bằng chứng":r["evidence"],"Tác động":r["impact"],"Theo dõi":r["monitor"]} for r in result["conclusion"]["risk_matrix"]]),hide_index=True,width="stretch")
        for item in result["conclusion"]["risks"]:st.write("• "+item)
        if ai.get("available"):
            st.write("**Nhận xét Gemini có bằng chứng**")
            for section,items in ai["sections"].items():
                for item in items:
                    st.write(item["text"])
                    for e in item["evidence"]:st.caption(f"{e['label']} · Kỳ {e['period']} · {e.get('value',e.get('company_value'))} {e.get('unit','')}")
                    st.caption("Nguồn: "+", ".join(item["source_ids"])+f" · Chốt {ai['as_of']} · {ai['model']}")
    with tabs[3]:
        for item in result["news"]:st.markdown(f"{item['published_at']} · [{item['title']}]({item['url']})")
        if not result["news"]:st.info("Chưa có tin phù hợp từ nguồn.")
        st.caption("Danh sách công bố/sự kiện để tra cứu. Chưa suy diễn tác động từ tiêu đề tin.")
    with tabs[4]:
        st.write(result["quality"]["financial_check"]["note"])
        checks=result["quality"]["financial_check"]["checks"]
        if checks:st.dataframe(pd.DataFrame(checks),hide_index=True,width="stretch")
        for warning in result["quality"]["warnings"]:st.caption(warning)
        for source in result["sources"]:
            st.markdown(f"[{source['source_id']}]({source.get('url_or_file','')})")
        with st.expander("Công thức và đầu vào chỉ tiêu"):
            st.json(result["financial"]["metrics"])
        if acquisition["prices"]:
            st.download_button("Tải dữ liệu giá CSV",(ROOT/acquisition["prices"]["csv"]).read_bytes(),file_name=f"{request['ticker']}_prices.csv",mime="text/csv")
        for i,report in enumerate(acquisition["financial_documents"]):
            st.download_button("Tải PDF gốc: "+report["title"],(ROOT/report["file"]).read_bytes(),file_name=Path(report["file"]).name,mime="application/pdf",key=f"raw_pdf_{i}")
else:
    st.info("Không cần chuẩn bị CSV hoặc nhập số liệu tài chính. Bấm Phân tích để hệ thống tự lấy dữ liệu.")
    try:
        preview_news=fetch_news_preview(ticker.strip().upper(),as_of)
        preview_digest=build_news_digest(preview_news)
        preview_rows=[]
        for item in preview_digest["headlines"]:
            title=html.escape(item["title"])
            url=item.get("url","")
            if url.startswith(("https://","http://")):
                title=f'<a href="{html.escape(url,quote=True)}" target="_blank" rel="noopener noreferrer">{title}</a>'
            excerpt=html.escape(item.get("summary") or "Nguồn chỉ cung cấp tiêu đề cho tin này.")
            preview_rows.append(
                f'<article class="news-digest__article"><div><span class="news-digest__date">{html.escape(item["published_at"])}</span> {title}</div>'
                f'<p class="news-digest__excerpt">{excerpt}</p></article>'
            )
        preview_markup="".join(preview_rows) or '<div class="news-digest__item">KBS hiện chưa trả tin phù hợp cho mã này.</div>'
        st.markdown(f"""
        <section class="news-digest">
          <div class="news-digest__kicker">KBS · TIN CỦA MÃ {html.escape(ticker.strip().upper())}</div>
          <h3 class="news-digest__title">Tổng hợp tin tức tài chính</h3>
          <p class="news-digest__summary">{html.escape(preview_digest["summary"])}</p>
          {preview_markup}
          <div class="news-digest__note">Tin được tải trực tiếp từ feed KBS và cache tối đa 5 phút. Sau khi phân tích, có thể chuyển sang tin từ mẫu peer cùng ngành.</div>
        </section>
        """,unsafe_allow_html=True)
    except Exception:
        st.warning("Chưa kết nối được feed tin của mã này. Thử lại sau hoặc bấm Phân tích để kiểm tra nguồn và lưu trạng thái.")
