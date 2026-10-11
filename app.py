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


def show_research_notes(result,section):
    groups={}
    for item in result.get("research_narrative",{}).get(section,[]):
        if item["title"]=="Thông tin cập nhật" or item["title"].endswith("trong nhóm so sánh"):continue
        groups.setdefault(item["title"],[]).append(item)
    for title,items in groups.items():
        with st.expander(title):
            for item in items:
                st.write(item["evidence"]);st.write(item["interpretation"])
                st.caption("Theo dõi: "+item["monitor"]+" · Kỳ/ngày nguồn "+item["period"])
    articles=[article for article in result.get("context_news",{}).get("articles",[]) if article["scope"]==section]
    if articles:
        with st.expander(f"Thông tin cập nhật từ báo chí · {len(articles)} bài"):
            st.caption(result.get("context_news",{}).get("note",""))
            # The bounded body is evidence for Gemini, not copied into the UI.
            news=[{**article,"title":" ".join(article["title"].split()[:22]),"summary":"Tin báo chí cần được đối chiếu với số liệu và công bố doanh nghiệp; mở bài gốc để đọc đầy đủ."} for article in articles]
            show_news(news,key=f"context_news_{result['acquisition']['run_id']}_{section}",title="Tin vĩ mô" if section=="macro" else "Tin ngành")


def show_ai_section(result,section):
    ai=result.get("ai_commentary",{})
    items=ai.get("sections",{}).get(section,[])
    if not items:return
    with st.container(border=True):
        st.write("**Gemini · Nhận xét từ bằng chứng đã kiểm tra**")
        for item in items:
            st.write(item["text"])
            for evidence in item["evidence"]:
                st.caption(evidence["label"]+" · Kỳ/ngày "+evidence["period"])
        st.caption("AI diễn giải kênh tác động và điều kiện theo dõi; các phép tính định giá và quy tắc khuyến nghị do chương trình thực hiện.")


def show_price_chart(result):
    frame=pd.DataFrame(result["price_rows"]).copy()
    frame["date"]=pd.to_datetime(frame["date"])
    valid=result["market"].get("history_indicators_available",True)
    for days in (20,50):frame[f"ma{days}"]=frame["close"].rolling(days).mean() if valid else float('nan')
    frame["direction"]=frame["close"].ge(frame["open"]).map({True:"Tăng",False:"Giảm"})
    period=st.radio("Khoảng xem biểu đồ",["3 tháng","6 tháng","Toàn kỳ"],index=2,horizontal=True,key="chart_period")
    if period!="Toàn kỳ":frame=frame[frame["date"]>=frame["date"].max()-pd.Timedelta(days=90 if period=="3 tháng" else 180)]
    color={"field":"direction","type":"nominal","scale":{"domain":["Tăng","Giảm"],"range":["#087e72","#cf5757"]},"legend":None}
    tooltip=[{"field":"date","type":"temporal","title":"Ngày","format":"%d/%m/%Y"}]+[{"field":key,"type":"quantitative","title":label,"format":",.0f"} for key,label in [("open","Mở cửa"),("high","Cao nhất"),("low","Thấp nhất"),("close","Đóng cửa"),("volume","Khối lượng")]]
    x={"field":"date","type":"temporal","axis":{"title":None,"format":"%d/%m","labelAngle":0,"tickCount":8}}
    layers=[{"mark":"rule","encoding":{"y":{"field":"low","type":"quantitative","scale":{"zero":False},"axis":{"title":"Giá (VND/CP)","format":",.0f"}},"y2":{"field":"high"}}},
            {"mark":{"type":"bar","size":4},"encoding":{"y":{"field":"open","type":"quantitative","scale":{"zero":False}},"y2":{"field":"close"}}}]
    if valid:
        layers.extend({"mark":{"type":"line","color":color_value,"strokeWidth":1.5},"encoding":{"y":{"field":key,"type":"quantitative","scale":{"zero":False}},"color":{"value":color_value}}} for key,color_value in [("ma20","#c49325"),("ma50","#5e6fa8")])
    spec={"vconcat":[{"height":330,"encoding":{"x":x,"color":color,"tooltip":tooltip},"layer":layers},
                     {"height":100,"mark":"bar","encoding":{"x":x,"y":{"field":"volume","type":"quantitative","axis":{"title":"Khối lượng (CP)","format":".2s"}},"color":color,"tooltip":tooltip}}],"resolve":{"scale":{"x":"shared"}},"config":{"view":{"stroke":None},"axis":{"gridOpacity":.12}}}
    st.vega_lite_chart(frame,spec,width="stretch")
    st.caption("Nến xanh: đóng cửa ≥ mở cửa; nến đỏ: đóng cửa < mở cửa. Đường vàng: MA20; tím: MA50." if valid else "Nến dùng OHLC từ nguồn. MA tạm ẩn vì mẫu giá lịch sử chưa đủ điều kiện.")


def readable_reason(message):
    """Explain source failures without exposing transport errors in the main UI."""
    text=str(message or "")
    lowered=text.lower()
    if any(word in lowered for word in ("timeout", "timed out")):
        return "Nguồn dữ liệu phản hồi quá chậm. Có thể thử lại sau."
    if "404" in lowered:
        return "Nguồn này chưa cung cấp dữ liệu cho mã hoặc kỳ đang chọn."
    if any(word in lowered for word in ("403", "429", "rate limit")):
        return "Nguồn đang giới hạn truy cập. Có thể thử lại sau."
    if any(word in lowered for word in ("unable to retrieve", "connection", "getaddrinfo", "http error", "json", "ssl")):
        return "Chưa tải hoặc đọc được dữ liệu từ nguồn."
    return text or "Chưa đủ dữ liệu để đưa vào mẫu so sánh."


def show_news(items, *, key, title="Tin tức tài chính"):
    digest=build_news_digest(items,limit=max(3,len(items)))
    articles=[item for group in digest["groups"] for item in group["articles"]]
    expanded=st.session_state.get(key,False)
    visible=articles if expanded else articles[:3]
    st.subheader(title)
    if not articles:
        st.info("Chưa có tin phù hợp từ nguồn cho phạm vi này.")
        return
    st.caption(f"Hiển thị {len(visible)}/{len(articles)} tin · Mới nhất trước · Bấm tiêu đề để đọc bài gốc")
    rows=[]
    for item in visible:
        headline=html.escape(item["title"])
        if item.get("news_scope")=="industry_peer" and item.get("ticker"):
            headline=html.escape(item["ticker"])+" · "+headline
        url=item.get("url","")
        if url.startswith(("https://","http://")):
            headline=f'<a href="{html.escape(url,quote=True)}" target="_blank" rel="noopener noreferrer">{headline}</a>'
        day=date.fromisoformat(item["published_at"]).strftime("%d/%m/%Y")
        excerpt=html.escape(item.get("summary") or "Nguồn chỉ cung cấp tiêu đề. Mở bài gốc để đọc nội dung.")
        rows.append(f'<article class="news-digest__article"><div class="news-digest__source">{day}</div>'
                    f'<div>{headline}</div><p class="news-digest__excerpt">{excerpt}</p></article>')
    st.markdown('<section class="news-digest">'+"".join(rows)+'</section>',unsafe_allow_html=True)
    if len(articles)>3:
        label="Thu gọn còn 3 tin" if expanded else f"Xem tất cả {len(articles)} tin"
        if st.button(label,key=key+"_button"):
            st.session_state[key]=not expanded
            st.rerun()
    st.caption("Trích yếu theo nguồn tin; tiêu đề không đủ để kết luận tác động đến giá cổ phiếu.")


def show_industry_sample(industry):
    coverage=industry.get("coverage") or {}
    selected=[peer["ticker"] for peer in industry.get("peers",[])]
    excluded=industry.get("excluded") or []
    eligible=industry.get("eligible_candidates")
    cols=st.columns(3)
    cols[0].metric("Doanh nghiệp cùng nhóm",len(industry.get("members",[])))
    cols[1].metric("Đủ điều kiện xét chọn",eligible if eligible is not None else "Chưa xác định")
    cols[2].metric("Đã chọn để so sánh",len(selected))
    st.write("**Mã trong mẫu:** "+(", ".join(selected) or "Chưa có mã đủ điều kiện."))
    scope={"consolidated":"Hợp nhất","separate":"Riêng lẻ","standalone":"Riêng lẻ","parent":"Công ty mẹ"}.get(industry.get("scope"),"Chưa xác định")
    st.caption(f"Ngày cuối kỳ: {industry.get('period_end') or 'Chưa xác định'} · Báo cáo: {scope}")
    st.caption("Mẫu được chọn trong các doanh nghiệp đủ dữ liệu cùng kỳ và phạm vi báo cáo. Mã đủ điều kiện có thể không được chọn vì giới hạn tối đa 4 doanh nghiệp; không đồng nghĩa bị loại do dữ liệu lỗi.")
    if excluded:
        st.write(f"**{len(excluded)} mã chưa đủ điều kiện dữ liệu**")
        st.dataframe(pd.DataFrame([{"Mã cổ phiếu":row.get("ticker","—"),"Lý do chưa đưa vào mẫu":readable_reason(row.get("reason"))} for row in excluded]),hide_index=True,width="stretch")
    else:
        st.caption("Không ghi nhận mã bị loại do thiếu dữ liệu trong lần xét chọn này.")
    if coverage:
        complete=coverage.get("classification_complete")
        status="Đã tải đủ danh mục của nguồn" if complete else "Danh mục phân ngành tải được một phần" if complete is False else "Chưa xác định độ đầy đủ của danh mục"
        st.caption(f"Nguồn phân ngành bao phủ {coverage.get('symbols',0)} mã trong {coverage.get('groups',0)} nhóm · {status}. Đây là phạm vi của nguồn, không phải số mã trong mẫu so sánh.")


def show_valuation_table(rows):
    labels={"method":"Phương pháp","label":"Kịch bản","multiple":"Bội số (lần)",
            "target_price_vnd":"Giá trị / CP (VND)","reference_price_vnd":"Giá trị / CP (VND)",
            "difference_pct":"Chênh với giá (%)","target_pe":"P/E giả định (lần)",
            "target_pb":"P/B giả định (lần)","weight_pct":"Trọng số (%)","contribution_vnd":"Đóng góp / CP (VND)"}
    frame=pd.DataFrame(rows)
    columns=[column for column in labels if column in frame.columns]
    st.dataframe(frame[columns].rename(columns=labels),hide_index=True,width="stretch")


st.set_page_config(page_title="StockInsight",layout="wide",initial_sidebar_state="collapsed")
st.markdown("""
<style>
:root { --ink:#173532; --ink-soft:#37544e; --jade:#087e72; --brass:#c7a96b; --paper:#eef4f1; --line:#d9e4df; }
.stApp { background-color:var(--paper); }
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
[data-baseweb="tab-list"] { flex-wrap:wrap; gap:6px; margin:18px 0; }
[data-baseweb="tab"] { padding:10px 14px; height:auto; border-radius:6px; font-weight:600; }
[data-baseweb="tab"][aria-selected="true"] { background:#dbeee6; color:#066b60; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display:none; }
[data-testid="stExpander"] { background:rgba(255,255,255,.65); border-radius:8px; }
[data-testid="stButton"] button { min-height:42px; }
@media(max-width:700px) { .block-container{padding:1rem 1rem 3rem}.masthead{padding:20px 19px;margin-bottom:20px}.masthead__eyebrow,.masthead__footer{align-items:flex-start;flex-direction:column;gap:6px}.masthead__title{font-size:42px}.step-heading__title{font-size:18px}.brief-panel{margin-top:10px;padding:23px 20px}.brief-ticker{font-size:42px}.news-digest{padding:19px 17px}.news-digest__item{align-items:flex-start;flex-direction:column;gap:4px}.news-digest__date{flex:auto} }
</style>
""",unsafe_allow_html=True)
st.markdown(f"""
<header class="masthead">
    <div class="masthead__eyebrow"><strong>PHÂN TÍCH CỔ PHIẾU VIỆT NAM</strong><span>Dữ liệu cuối ngày · Báo cáo PDF</span></div>
    <div class="masthead__title">StockInsight</div>
    <div class="masthead__footer"><span>BÁO CÁO CƠ HỘI ĐẦU TƯ CỔ PHIẾU</span><span>Ngày báo cáo · {today.strftime('%d/%m/%Y')}</span></div>
</header>
""",unsafe_allow_html=True)
request_column,brief_column=st.columns([1.25,.75],gap="large")
with request_column:
    st.markdown("<div class='step-heading'><span class='step-heading__number'>01</span><div><div class='step-heading__title'>Cổ phiếu và thời gian</div><div class='step-heading__note'>MÃ GIAO DỊCH · KHOẢNG PHÂN TÍCH</div></div></div>",unsafe_allow_html=True)
    cols=st.columns(3)
    ticker=cols[0].text_input("Mã cổ phiếu",value="HPG",help="Nhập mã niêm yết, ví dụ HPG, FPT hoặc VNM.")
    start=cols[1].date_input("Giá giao dịch từ ngày",value=today-timedelta(days=365),max_value=today-timedelta(days=1),help="Ngày bắt đầu chuỗi giá. Không giới hạn BCTC vào khoảng này; kỳ năm mới nhất đã công bố trước ngày chốt sẽ được dùng.")
    as_of=cols[2].date_input("Ngày chốt dữ liệu",value=today,max_value=today,help="Chỉ dùng tài liệu và phiên giá đủ điều kiện đến ngày này. BCTC năm và khoảng lịch sử giá có kỳ riêng.")

    st.markdown("<div class='step-heading' style='margin-top:28px'><span class='step-heading__number'>02</span><div><div class='step-heading__title'>Kiểu báo cáo</div><div class='step-heading__note'>CHỌN MỨC ĐỘ CHI TIẾT VÀ NỘI DUNG XUẤT</div></div></div>",unsafe_allow_html=True)
    mode=st.radio("Độ chi tiết",["Đầy đủ","Tóm tắt"],horizontal=True,captions=["Nhiều chỉ tiêu và giải thích","Các điểm chính, ngắn gọn"])
    with st.expander("Tuỳ chỉnh nội dung PDF"):
        section_cols=st.columns(3)
        sections=[]
        for index,(section,label) in enumerate(SECTION_LABELS.items()):
            if section_cols[index%len(section_cols)].checkbox(label,value=True,key=f"pdf_section_{section}"):
                sections.append(section)
    with st.expander("Giả định định giá cá nhân (không bắt buộc)"):
        st.caption("Chỉ dùng để thử các kịch bản trong phụ lục. Bạn có thể giữ nguyên để dùng định giá chính từ mẫu doanh nghiệp so sánh.")
        target_pb=st.number_input("P/B cơ sở giả định",min_value=0.1,max_value=20.0,value=1.5,step=0.1,help="Chỉ dùng trong phụ lục độ nhạy; không thay đổi định giá chính hoặc khuyến nghị.")
        vc=st.columns(3)
        target_pe=vc[0].number_input("P/E năm giả định",min_value=.1,max_value=100.,value=12.,step=.5)
        cost_of_equity=vc[1].number_input("Chi phí vốn chủ Ke (%)",min_value=.1,max_value=99.,value=11.5,step=.5)/100
        terminal_growth=vc[2].number_input("Tăng trưởng dài hạn g (%)",min_value=0.,max_value=20.,value=3.5,step=.5)/100
        vc=st.columns(3)
        wacc=vc[0].number_input("WACC cho FCFF (%)",min_value=.1,max_value=99.,value=10.,step=.5)/100
        forecast_growth=vc[1].number_input("Tăng trưởng FCFF 3 năm (%)",min_value=-50.,max_value=50.,value=7.,step=.5)/100
        tax_rate=vc[2].number_input("Thuế suất giả định (%)",min_value=0.,max_value=99.,value=20.,step=1.)/100
        st.caption("Các tỷ lệ trên là giả định do người dùng chọn. DCF chỉ áp cho doanh nghiệp phi tài chính có FCFF và đầu vào đầy đủ. EPS năm quy đổi không phải EPS công bố/TTM.")
    use_ai=st.checkbox("Gemini hỗ trợ nhận xét từ dữ liệu và nguồn",value=False,help="Cần GEMINI_API_KEY trong Streamlit Secrets hoặc environment. Gửi số liệu và trích xuất bài công khai có giới hạn cho Gemini; nếu thiếu key hoặc lỗi, vẫn tạo báo cáo bằng quy tắc.")
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
    <div class="brief-kicker"><span class="brief-pip"></span>BÁO CÁO BẠN SẮP TẠO</div>
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
    for news_scope in ("company","industry"):
        st.session_state.pop(f"news_expanded_{ticker.strip().upper()}_{as_of.isoformat()}_{news_scope}",None)
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
    recommendation=result.get("recommendation",{})
    primary=result.get("valuation",{}).get("primary",{})
    with st.container(border=True):
        st.subheader(recommendation.get("stance","Kết quả phân tích"))
        st.write(recommendation.get("reason","Xem các mục bên dưới để đánh giá dữ liệu và cơ hội đầu tư."))
        summary_cols=st.columns(3)
        summary_cols[0].metric("Giá đóng cửa",formatted(result.get("market",{}).get("latest_close_vnd") if result.get("market") else None,"VND/share"))
        summary_cols[1].metric("Giá tham chiếu định giá",formatted(primary.get("target_price_vnd") if primary.get("available") else None,"VND/share"))
        summary_cols[2].metric("Chênh lệch so với giá",formatted(primary.get("upside_pct") if primary.get("available") else None,"%"))
        st.caption("Giá tham chiếu phụ thuộc phương pháp và dữ liệu đủ điều kiện; chênh lệch giá không đồng nghĩa với khuyến nghị mua.")
    ai=result.get("ai_commentary",{})
    if request.get("use_ai") and not ai.get("available"):
        st.info(ai.get("reason","Gemini chưa có nhận xét hợp lệ; báo cáo vẫn dùng phân tích từ dữ liệu."))
    elif ai.get("available"):
        count=sum(len(items) for items in ai.get("sections",{}).values())
        st.caption(f"Gemini: {count} nhận xét qua kiểm tra, hiển thị trong Vĩ mô, Ngành và Cơ hội và rủi ro.")
        if ai.get("rejected"):
            with st.expander("Nhận xét AI chưa được sử dụng"):
                for reason in dict.fromkeys(row["reason"] for row in ai["rejected"]):st.write(reason)
    issues=result.get("errors",[])
    warnings=acquisition.get("warnings",[])
    if issues or warnings:
        with st.expander(f"Tình trạng thu thập dữ liệu · {len(issues)+len(warnings)} lưu ý"):
            st.caption("Một nguồn không truy cập được có thể đã được thay bằng nguồn dự phòng. Xem điều kiện sử dụng dữ liệu trong từng mục phân tích.")
            stages={"prices":"Giá giao dịch","financial":"Tài chính","news":"Tin tức","industry_peers":"Mẫu so sánh ngành","industry_classification":"Phân ngành","macro":"Vĩ mô"}
            for error in issues:
                st.write(stages.get(error.get("stage"),"Nguồn dữ liệu")+": "+readable_reason(error.get("message")))
            for warning in warnings:st.write(warning)
    st.caption("Chọn mục để xem chi tiết. Tin tức mặc định hiển thị 3 bài; giả định cá nhân nằm trong mục Định giá.")
    tabs=st.tabs(["Tổng quan","Vĩ mô","Ngành","Tài chính","Định giá","Cơ hội và rủi ro","Tin tức","Nguồn dữ liệu"])
    with tabs[0]:
        market=result.get("market")
        if market:
            cols=st.columns(4)
            for col,label,key,unit in zip(cols,["Giá đóng cửa",market.get("return_label","Biến động khoảng chọn"),"Sụt giảm tối đa","MA20"],["latest_close_vnd","return_pct","max_drawdown_pct","ma20_vnd"],["VND/share","%","%","VND/share"]):
                display="Không tính" if key!="latest_close_vnd" and not market.get("history_indicators_available",True) else formatted(market[key],unit)
                col.metric(label,display)
                if display=="Không tính":col.caption("Lịch sử chưa khớp")
            price_check=result["quality"]["price_check"]
            if not latest_price_matches(price_check,market):st.warning("Giá đóng cửa mới nhất chưa khớp nguồn thứ hai đúng ngày; định giá bị chặn.")
            if price_check["status"]=="matched":st.caption(f"Mẫu lịch sử: khớp {len(price_check['checks'])}/{price_check.get('expected_count',len(price_check['checks']))} phiên; không xác nhận toàn bộ lịch sử điều chỉnh.")
            else:st.warning(f"Mẫu lịch sử chưa khớp đầy đủ: {price_check.get('matched_count',sum(c['match'] for c in price_check.get('checks',[])))}/{price_check.get('expected_count',20)} phiên khớp. Hạn chế MA, lợi suất, drawdown và biến động năm hóa; kiểm tra giá mới nhất được tách riêng.")
            show_price_chart(result)
            st.caption(market.get("chart_note","Biểu đồ thể hiện giá đóng cửa từ nguồn."))
            st.caption(market["return_note"])
        else:
            st.info("Chưa có chuỗi giá hợp lệ. Bạn vẫn có thể xem dữ liệu tài chính và các phần phân tích đã thu thập được.")
    with tabs[1]:
        macro=result.get("macro",{})
        rows=macro.get("indicators",[])
        if rows:
            st.dataframe(pd.DataFrame([{"Chỉ tiêu":r["label"],"Giá trị":formatted(r["value"],r["unit"]),"Kỳ":r["period"],"Công bố / cập nhật":r.get("published_at") or "Cập nhật "+r.get("source_updated_at","")} for r in rows]),hide_index=True,width="stretch")
            st.write(macro.get("assessment",""))
            st.caption("Các kỳ riêng biệt; số liệu năm WDI không thay số liệu tháng. Lãi suất/tỷ giá bình quân lịch sử không phải mức hiện tại.")
        else:st.warning("Chưa lấy được dữ liệu vĩ mô hợp lệ.")
        show_ai_section(result,"macro")
        show_research_notes(result,"macro")
        with st.expander("Phạm vi nguồn tin và thị trường"):
            st.caption(result.get("context_news",{}).get("note",""))
            context_errors=result.get("context_news",{}).get("errors",[])+result.get("market_context",{}).get("errors",[])
            if context_errors:
                for error in context_errors:st.write(readable_reason(error.get("message") if isinstance(error,dict) else error))
            else:st.caption("Không ghi nhận lỗi tải tin vĩ mô/ngành hoặc dữ liệu thị trường trong lần phân tích này.")
    with tabs[2]:
        industry=result.get("industry",{})
        if industry.get("available"):
            st.write(f"**{industry['name']}** · {industry.get('taxonomy','KBS')}")
            st.caption(f"{len(industry['members'])} thành viên · Kỳ so sánh {industry.get('period_end','chưa có')} · Mẫu: {', '.join(p['ticker'] for p in industry['peers']) or 'chưa đủ'}")
            st.caption(industry["selection"])
            comparisons=industry.get("comparisons",[])
            if comparisons:
                st.dataframe(pd.DataFrame([{"Chỉ tiêu":c["label"],"Mã phân tích":formatted(c["company_value"],c["unit"]),"Trung vị mẫu":formatted(c["sample_median"],c["unit"]),"Chênh lệch":formatted(c["difference"],"điểm %" if c["unit"]=="%" else c["unit"]),"Số mẫu":c["sample_size"]} for c in comparisons]),hide_index=True,width="stretch")
            else:st.warning("Chưa đủ chỉ tiêu đồng kỳ của ít nhất hai doanh nghiệp để tính trung vị.")
            with st.expander("Rủi ro cần theo dõi của ngành"):
                for risk in industry.get("structural_risks",[]):st.write(risk)
            with st.expander("Mẫu so sánh: mã được chọn và lý do loại"):
                show_industry_sample(industry)
            st.caption("Trung vị là giá trị ở giữa các doanh nghiệp trong mẫu; không phải bình quân của toàn bộ ngành.")
        else:st.warning("Nguồn chưa xác nhận phân ngành của mã này; không tự gán ngành.")
        show_ai_section(result,"industry")
        show_research_notes(result,"industry")
    with tabs[3]:
        diagnostics=result.get("financial_data_status",{})
        st.caption("Khoảng ngày trên đầu trang dành cho lịch sử giá. Phần này dùng BCTC năm mới nhất đủ điều kiện đến ngày chốt, cùng năm trước để tính tăng trưởng; không phải số liệu TTM.")
        for message in diagnostics.get("messages",[]):st.caption(message)
        if result["financial"]["metrics"]:
            st.caption(f"Báo cáo năm {result['financial']['metrics'][0]['period']}; không phải số liệu TTM.")
            st.dataframe(pd.DataFrame([{"Chỉ tiêu":m["label"],"Giá trị":formatted(m["value"],m["unit"])} for m in result["financial"]["metrics"]]),hide_index=True,width="stretch")
        else:st.info("Chưa có chỉ tiêu tài chính đủ điều kiện tính toán.")
        interim=result.get("interim")
        if interim and interim["valid"]:
            st.write(f"**Bán niên HPG đến {interim['period_end']}**")
            st.dataframe(pd.DataFrame([{"Chỉ tiêu":label,"Hiện tại":formatted(interim["fields"][key]["value"],"VND"),"6 tháng cùng kỳ":formatted(interim["fields"][key]["previous"],"VND"),"Trang PDF":interim["fields"][key]["page"]} for key,label in [("revenue","Doanh thu thuần"),("net_profit","LNST"),("cfo","Dòng tiền kinh doanh")]]),hide_index=True,width="stretch")
        vnf=result.get("vnfinancialdata",{})
        if vnf:
            with st.expander("Báo cáo tài chính bổ sung từ vnfinancialdata"):
                st.caption(vnf.get("reason",""))
                if vnf.get("available"):
                    st.write(f"{vnf['row_count']:,} dòng chỉ tiêu · Năm {min(vnf['years'])}–{max(vnf['years'])} · Dataset {vnf['dataset']['revision']}")
                    st.dataframe(pd.DataFrame([{"Bảng":s["statement"],"Năm mới nhất":s["latest_year"],"Số dòng":s["row_count"]} for s in vnf["statements"]]),hide_index=True,width="stretch")
                    csv_path=ROOT/vnf["csv"]
                    if csv_path.exists():
                        raw_frame=pd.read_csv(csv_path)
                        year=st.selectbox("Năm BCTC vnfinancialdata",sorted(vnf["years"],reverse=True),key="vnf_year")
                        st.dataframe(raw_frame[raw_frame.year.eq(year)][["statement","item_name","value"]].rename(columns={"statement":"Bảng báo cáo","item_name":"Chỉ tiêu","value":"Giá trị gốc"}),hide_index=True,width="stretch")
                        st.download_button("Tải toàn bộ BCTC vnfinancialdata CSV",csv_path.read_bytes(),file_name=f"{request['ticker']}_vnfinancialdata.csv",mime="text/csv")
                    checks=vnf.get("checks",[])
                    if checks:
                        latest=max(c["year"] for c in checks)
                        st.write(f"Đối chiếu giá trị năm {latest}; chưa chứng nhận cùng phạm vi hoặc độc lập nguồn gốc")
                        st.dataframe(pd.DataFrame([{"Chỉ tiêu":c["label"],"Nguồn chính (VND)":c["primary_vnd"],"vnfinancialdata (VND)":c["reference_vnd"],"Kết quả":"Khác quy ước dấu" if c.get("status")=="different_sign_convention" else "Khớp giá trị" if c["match"] else "Lệch","Ghi chú":c.get("note","")} for c in checks if c["year"]==latest]),hide_index=True,width="stretch")
                for error in vnf.get("errors",[]):st.warning(error["message"])
        reference=result.get("reference",{})
        with st.expander("Dữ liệu tham khảo và báo cáo thường niên gốc"):
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
    with tabs[4]:
        val=result["valuation"];primary=val.get("primary",{});benchmark=val.get("benchmark",{})
        st.write(f"**Bội số của {request['ticker']} từ dữ liệu đã xác minh**")
        multiples=st.columns(3)
        multiples[0].metric("P/E lợi nhuận mẹ năm",formatted(val.get("pe",{}).get("reference_pe"),"lần"))
        multiples[1].metric("P/B vốn cổ đông mẹ",formatted(val.get("reference_pb"),"lần"))
        multiples[2].metric("BVPS cổ đông mẹ",formatted(val.get("book_value_per_share"),"VND/share"))
        st.caption(f"BCTC năm {diagnostics.get('latest_valid_year','chưa xác định')} và số cổ phiếu tại ngày chốt. P/E năm quy đổi không phải EPS TTM, EPS dự phóng hoặc EPS bình quân gia quyền công bố.")
        st.subheader("Định giá chính từ dữ liệu so sánh")
        if primary.get("available"):
            st.metric("Giá tham chiếu chính",formatted(primary["target_price_vnd"],"VND/share"),formatted(primary["upside_pct"],"%"))
            st.write(primary["selected_method"]+". "+primary["selection_reason"])
            st.caption(primary["methodology"])
            st.dataframe(pd.DataFrame([{ "Chỉ tiêu":c["label"],"Hiện tại (x)":c["company_value"],"Trung vị mẫu (x)":c["sample_median"],"Cao/thấp hơn mẫu (%)":c["premium_pct"],"Số mẫu":c["sample_size"]} for c in primary["comparisons"]]),hide_index=True,width="stretch")
            for c in primary["comparisons"]:st.write(c["label"]+": "+c["interpretation"])
            st.dataframe(pd.DataFrame([{"Phương pháp":m["method"],"Bội số (x)":m.get("multiple"),"Giá / CP (VND)":m["target_price_vnd"],"Chênh với giá (%)":m.get("difference_pct"),"Số mẫu":m.get("sample_size")} for m in primary["methods"]]),hide_index=True,width="stretch")
        else:st.info(primary.get("reason","Chưa đủ dữ liệu cho định giá chính."))
        peers=benchmark.get("peers",[])
        comparisons=result.get("industry",{}).get("comparisons",[])
        if comparisons:
            st.write("**So sánh hiệu quả kinh doanh và rủi ro tài chính**")
            st.caption(f"Kỳ chung: {result['industry'].get('period_end')} · Chỉ tiêu phù hợp loại hình doanh nghiệp · Trung vị mẫu, không phải toàn ngành.")
            st.dataframe(pd.DataFrame([{"Chỉ tiêu":row["label"],request["ticker"]:formatted(row["company_value"],row["unit"]),"Trung vị mẫu":formatted(row["sample_median"],row["unit"]),"Chênh lệch":formatted(row["difference"],"điểm %" if row["unit"]=="%" else row["unit"]),"Số mẫu":row["sample_size"]} for row in comparisons]),hide_index=True,width="stretch")
        if peers:
            st.write("**Các doanh nghiệp so sánh**")
            st.dataframe(pd.DataFrame([{ "Mã":r["ticker"],"P/E năm (x)":r["pe"],"P/B (x)":r["pb"],"ROE (%)":r["roe"],"LNST YoY (%)":r.get("profit_growth"),"Nợ vay/vốn":r.get("debt_equity")} for r in peers]),hide_index=True,width="stretch")
            st.caption(f"Kỳ {benchmark.get('period_end')}; giá {benchmark.get('price_date')}. P/E theo lợi nhuận mẹ năm/CP snapshot; không phải TTM hay dự phóng. Mẫu không đại diện toàn ngành.")
        sotp=val.get("sotp",{})
        with st.expander("SOTP: định giá từng mảng",expanded=bool(sotp.get("available"))):
            st.write(sotp.get("reason","Chưa có dữ liệu từng mảng có nguồn."))
            if sotp.get("available"):
                st.caption(f"Mô hình {sotp.get('provider')}; ngày {sotp['published_at']}; CP theo báo cáo nguồn.")
                st.dataframe(pd.DataFrame([{"Mảng kinh doanh":part["label"],"Giá trị (VND)":part["value_vnd"],"Phương pháp":part["method"],"Trang nguồn":part.get("page")} for part in sotp["components"]]),hide_index=True,width="stretch")
                st.metric("Giá SOTP tính lại theo báo cáo nguồn",formatted(sotp["target_price_vnd"],"VND/share"))
                st.caption(sotp["basis"])
        with st.expander("Phụ lục: giả định cá nhân và kiểm tra độ nhạy",expanded=False):
            st.caption("P/B và P/E nhập tay chỉ để thử độ nhạy. Không tham gia định giá chính hoặc khuyến nghị; Gordon/DCF ở đây chưa phải dự báo kinh doanh được xác nhận.")
            if val["available"]:
                if val.get("price_warning"):st.warning(val["price_warning"])
                if val.get("book_value_per_share") is not None:st.caption(f"BVPS mẹ {formatted(val['book_value_per_share'],'VND/share')} · P/B tham chiếu {val['reference_pb']:.2f} lần")
                if val.get("pb_methods"):show_valuation_table(val["pb_methods"])
                if val.get("scenarios"):st.dataframe(pd.DataFrame([{"Kịch bản":s["label"],"P/B giả định":s["target_pb"],"Giá trị quy đổi":formatted(s["reference_price_vnd"],"VND/share"),"Chênh lệch":formatted(s["difference_pct"],"%")} for s in val["scenarios"]]),hide_index=True,width="stretch")
                for method,label in [("gordon","P/B Gordon"),("industry","P/B mẫu ngành"),("pe","P/E lợi nhuận năm quy đổi"),("dcf","DCF FCFF"),("weighted_average","Bình quân trọng số")]:
                    data=val.get(method,{})
                    with st.expander(label,expanded=bool(data.get("available"))):
                        if data.get("available"):
                            if data.get("scenarios"):show_valuation_table(data["scenarios"])
                            if data.get("components"):show_valuation_table(data["components"])
                            target=data.get("target_price_vnd",data.get("base_price_vnd",data.get("per_share_price_vnd")))
                            if target is not None:st.metric("Giá trị kịch bản / CP",formatted(target,"VND/share"))
                            st.caption(data.get("eps_basis") or data.get("explanation") or data.get("formula") or data.get("note", ""))
                        else:st.info(data.get("reason","Chưa đủ đầu vào."))
                st.info(val["assumption"])
            else:st.info(val["reason"])
    with tabs[5]:
        recommendation=result.get("recommendation",{})
        if recommendation:
            st.subheader("Khuyến nghị nghiên cứu: "+recommendation["stance"])
            st.write(recommendation["reason"])
            st.caption(f"Ngày {recommendation['as_of']} · {recommendation['horizon']} · Tin cậy {recommendation['confidence']}")
            if recommendation.get("target_price_vnd"):
                st.write(f"Giá tham chiếu chính: {recommendation['target_price_vnd']:,.0f} VND/CP · Chênh lệch "+formatted(recommendation.get('upside_pct'),'%'))
            for thesis in recommendation["opportunities"]:
                with st.expander(thesis["title"]):
                    st.write(thesis["evidence"]);st.write(thesis["implication"])
                    st.write("Điều kiện xác nhận: "+thesis["catalyst"])
                    st.write("Luận điểm không còn đúng khi: "+thesis["invalidation"])
                    st.caption("Kỳ "+thesis["period"]+" · Nguồn: "+", ".join(thesis["source_ids"]))
            with st.expander("Quy tắc khuyến nghị và điều kiện đánh giá lại"):
                st.write(recommendation["methodology"]);st.write(recommendation["confidence_note"])
                for condition in recommendation["conditions"]:st.write("• "+condition)
        st.write("**Luận điểm vĩ mô → ngành → doanh nghiệp**")
        for item in result["conclusion"].get("integrated_thesis",[]):st.write("• "+item)
        if not recommendation:
            st.write("**Cơ hội / điều kiện theo dõi**")
            for item in result["conclusion"]["opportunities"]:st.write("• "+item)
        st.write("**Rủi ro**")
        if result["conclusion"].get("risk_matrix"):
            st.dataframe(pd.DataFrame([{ "Bằng chứng":r["evidence"],"Tác động":r["impact"],"Theo dõi":r["monitor"]} for r in result["conclusion"]["risk_matrix"]]),hide_index=True,width="stretch")
        for item in result["conclusion"]["risks"]:st.write("• "+item)
        if ai.get("available"):
            show_ai_section(result,"company_impact")
    with tabs[6]:
        company_news=[item for item in result.get("news",[]) if item.get("news_scope","company")=="company"]
        peer_news=[item for item in result.get("news",[]) if item.get("news_scope")=="industry_peer"]
        selected_news=company_news
        scope="company"
        if peer_news:
            chosen_scope=st.radio("Bạn muốn đọc tin về",["Doanh nghiệp đang phân tích","Các doanh nghiệp trong mẫu cùng ngành"],horizontal=True,key=f"news_scope_{request['ticker']}")
            if chosen_scope=="Các doanh nghiệp trong mẫu cùng ngành":
                selected_news=peer_news
                scope="industry"
        show_news(selected_news,key=f"news_expanded_{request['ticker']}_{request['as_of']}_{scope}")
    with tabs[7]:
        st.write(result["quality"]["financial_check"]["note"])
        checks=result["quality"]["financial_check"]["checks"]
        if checks:
            metric_labels={"net_profit":"Lợi nhuận sau thuế","revenue":"Doanh thu thuần","equity":"Vốn chủ sở hữu","assets":"Tổng tài sản"}
            st.dataframe(pd.DataFrame([{"Chỉ tiêu":metric_labels.get(check["metric"],"Chỉ tiêu tài chính"),"Kỳ":check["period"],"Nguồn chính (tỷ VND)":check["actual_billion_vnd"],"Báo cáo đối chiếu (tỷ VND)":check["reference_billion_vnd"],"Kết quả":"Khớp" if check["match"] else "Chưa khớp","Vị trí trong báo cáo":check.get("locator","")} for check in checks]),hide_index=True,width="stretch")
        for warning in result["quality"]["warnings"]:st.caption(warning)
        for source in result["sources"]:
            st.markdown(f"[{source['source_id']}]({source.get('url_or_file','')})")
        with st.expander("Cách tính các chỉ tiêu tài chính"):
            for metric in result["financial"]["metrics"]:
                st.write("**"+metric["label"]+":** "+formatted(metric.get("value"),metric["unit"]))
                st.caption("Công thức: "+metric.get("formula","Chưa có")+" · Kỳ "+metric.get("period","Chưa có"))
                if metric.get("reason"):st.caption(metric["reason"])
                if metric.get("inputs"):
                    st.dataframe(pd.DataFrame([{"Đầu vào":item.get("source_label","Chỉ tiêu nguồn"),"Giá trị":formatted(item.get("value"),item.get("unit","")),"Kỳ":item.get("period",""),"Ngày công bố":item.get("published_at","")} for item in metric["inputs"]]),hide_index=True,width="stretch")
            if not result["financial"]["metrics"]:st.info("Chưa có chỉ tiêu đủ dữ liệu để trình bày công thức.")
        if acquisition["prices"]:
            st.download_button("Tải dữ liệu giá CSV",(ROOT/acquisition["prices"]["csv"]).read_bytes(),file_name=f"{request['ticker']}_prices.csv",mime="text/csv")
        for i,report in enumerate(acquisition["financial_documents"]):
            st.download_button("Tải PDF gốc: "+report["title"],(ROOT/report["file"]).read_bytes(),file_name=Path(report["file"]).name,mime="application/pdf",key=f"raw_pdf_{i}")
else:
    st.info("Nhập mã cổ phiếu và bấm Phân tích và tạo PDF. Hệ thống tự lấy dữ liệu, bạn không cần chuẩn bị CSV.")
    try:
        preview_news=fetch_news_preview(ticker.strip().upper(),as_of)
        show_news(preview_news,key=f"news_preview_expanded_{ticker.strip().upper()}_{as_of.isoformat()}",title=f"Tin mới về {ticker.strip().upper()}")
    except Exception:
        st.warning("Chưa kết nối được nguồn tin của mã này. Có thể thử lại sau hoặc tiếp tục phân tích với các nguồn dữ liệu khác.")
