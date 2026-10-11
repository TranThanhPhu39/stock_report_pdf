"""Reconcile non-overlapping segment values and an explicit equity bridge."""
from datetime import date
from src.analysis.valuation import number


def analyze_sotp(snapshot,as_of,current_shares=None):
    out={"available":False,"usable_in_primary":False,"components":[],"source_ids":[],
         "reason":"Chưa có dữ liệu định giá từng mảng và điều chỉnh vốn có nguồn; không dùng tỷ trọng doanh thu thay giá trị."}
    if not snapshot:return out
    try:
        published=date.fromisoformat(snapshot["published_at"])
        if published>as_of:raise ValueError("Nguồn SOTP sau ngày chốt")
        parts=snapshot["components"];ids=[p["id"] for p in parts]
        if len(parts)<2 or len(set(ids))!=len(ids) or not snapshot.get("non_overlapping"):raise ValueError("Mảng trùng hoặc chưa xác nhận không cộng trùng")
        if any(not number(p.get("value_vnd")) or p["value_vnd"]<0 or not p.get("source_id") for p in parts):raise ValueError("Giá trị mảng hoặc nguồn không hợp lệ")
        shares=snapshot["shares"];discount=snapshot["discount"]
        if not number(shares,True) or not number(discount) or not 0<=discount<1:raise ValueError("Số CP/chiết khấu không hợp lệ")
        if snapshot.get("bridge_basis") not in {"broker_report_declared","verified_attributable_equity"}:raise ValueError("Chưa rõ cơ sở EV/vốn và tỷ lệ sở hữu")
        adjustments=snapshot["adjustments"]
        if any(not number(a.get("value_vnd")) or not a.get("source_id") for a in adjustments):raise ValueError("Thiếu điều chỉnh vốn có nguồn")
        total=sum(p["value_vnd"] for p in parts)
        if not number(snapshot.get("reported_enterprise_value"),True) or abs(total-snapshot["reported_enterprise_value"])>max(3e9,total*.001):raise ValueError("Tổng mảng không khớp bảng nguồn")
        equity=total+sum(a["value_vnd"] for a in adjustments)
        if equity<=0:raise ValueError("Vốn sau điều chỉnh không dương")
        if not number(snapshot.get("reported_equity_value"),True) or abs(equity-snapshot["reported_equity_value"])>max(3e9,equity*.001):raise ValueError("Điều chỉnh EV-vốn không khớp")
        fair=equity*(1-discount);target=fair/shares
        if not number(snapshot.get("reported_target"),True) or abs(target/snapshot["reported_target"]-1)>.002:raise ValueError("Giá/CP tính lại không khớp sau làm tròn")
        age=(as_of-published).days;shares_ok=number(current_shares,True) and abs(current_shares/shares-1)<=.001
        primary=snapshot["bridge_basis"]=="verified_attributable_equity" and snapshot.get("scope_verified") and age<=120 and shares_ok
        out.update(available=True,usable_in_primary=bool(primary),components=parts,adjustments=adjustments,
                   enterprise_value=total,equity_value=equity,discount_pct=discount*100,fair_equity_value=fair,
                   shares=shares,target_price_vnd=target,reported_target=snapshot["reported_target"],published_at=published.isoformat(),age_days=age,
                   source_ids=sorted({p["source_id"] for p in parts+adjustments}),provider=snapshot.get("provider"),
                   basis="Cộng các mảng không trùng, cộng/trừ điều chỉnh được nguồn nêu rõ, áp chiết khấu và chia CP của cùng báo cáo. Không trừ nợ/NCI lần nữa.",
                   reason="Đủ metadata để dùng định giá từng mảng." if primary else "SOTP tham khảo theo mô hình của công ty chứng khoán; chưa xác minh đầu vào từng tài sản/phạm vi. "+("Nguồn quá 120 ngày. " if age>120 else "")+("Số CP nguồn khác/chưa khớp snapshot hiện tại. " if not shares_ok else "")+"Không dùng cho khuyến nghị chính.")
    except (KeyError,TypeError,ValueError,ZeroDivisionError) as exc:out["reason"]=str(exc)
    return out
