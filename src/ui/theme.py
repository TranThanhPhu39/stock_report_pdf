"""Local, self-contained sky and glass presentation inspired by the reference."""
from base64 import b64encode
from datetime import date
from pathlib import Path
import streamlit as st


def render_theme(root: Path, today: date):
    assets=root/"assets"/"ui"
    sky=b64encode((assets/"sky.svg").read_bytes()).decode("ascii")
    css=(assets/"theme.css").read_text(encoding="utf8").replace("__SKY_BACKGROUND__",f"data:image/svg+xml;base64,{sky}")
    st.markdown("<style>"+css+"</style>",unsafe_allow_html=True)
    st.markdown(f"""
    <header class="site-header" id="top">
      <a class="site-brand" href="#top" aria-label="StockInsight — đầu trang"><span class="brand-mark" aria-hidden="true">↗</span>StockInsight<span class="brand-dot">.</span></a>
      <nav class="site-nav" aria-label="Điều hướng chính"><a href="#workspace">Phân tích</a><a href="#research">Báo cáo</a><a href="#guide">Cách dùng</a></nav>
      <span class="header-date">{today.strftime('%d/%m/%Y')}<span class="header-date__dot"></span>Dữ liệu cuối ngày</span>
    </header>
    <section class="sky-hero">
      <div class="hero-eyebrow"><span></span>GÓC NHÌN ĐẦU TƯ CỔ PHIẾU VIỆT NAM</div>
      <h1>Hiểu thị trường.<br>Tự tin quyết định.</h1>
      <p>Vĩ mô, ngành và doanh nghiệp — kết nối trong một báo cáo.<br>Khám phá cơ hội đầu tư từ dữ liệu có nguồn.</p>
      <a class="hero-action" href="#workspace">Bắt đầu phân tích <span aria-hidden="true">↗</span></a>
      <div class="hero-note">Tự thu thập dữ liệu <span>·</span> Phân tích có cơ sở <span>·</span> Xuất báo cáo PDF</div>
    </section>
    """,unsafe_allow_html=True)


def workspace_heading():
    st.markdown("""
    <div class="workspace-heading" id="workspace">
      <div><span class="workspace-label">KHÔNG GIAN NGHIÊN CỨU</span><h2>Tạo báo cáo của bạn</h2></div>
      <span class="workspace-badge"><span></span>Dữ liệu tự động</span>
    </div>
    """,unsafe_allow_html=True)


def render_guide():
    st.markdown("""
    <section class="quick-guide" id="guide" aria-label="Cách tạo báo cáo">
      <div><span>01</span><strong>Chọn cổ phiếu</strong><p>Nhập mã và ngày chốt để xác định phạm vi dữ liệu.</p></div>
      <div><span>02</span><strong>Đọc phân tích</strong><p>Xem định giá, luận điểm và những điều kiện cần theo dõi.</p></div>
      <div><span>03</span><strong>Lưu báo cáo</strong><p>Tải PDF với các nội dung bạn đã chọn.</p></div>
    </section>
    """,unsafe_allow_html=True)
