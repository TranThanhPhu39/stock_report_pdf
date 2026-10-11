"""Facts, conditional transmission channels, and observable confirmation events."""


def research_narrative(macro,industry,financial,market_context,news):
    out={"macro":[],"industry":[],"company_impact":[]}
    group=financial.get("industry_group")
    def add(section,title,evidence,interpretation,monitor,ids,period):
        out[section].append(dict(title=title,evidence=evidence,interpretation=interpretation,monitor=monitor,
                                 source_ids=ids,period=period,interpretation_type="conditional_inference"))
    for row in market_context.get("series",[]):
        change=row.get("change_20_pct")
        if change is None:continue
        fact=f"{row['label']} {row['latest_close']:,.2f} {row['unit']} ngày {row['latest_date']}; biến động 20 phiên {change:+.2f}%."
        if row["symbol"]=="VNINDEX":
            add("macro","Trạng thái thị trường",fact,row["trend"]+". "+row["trend_rule"]+" "+row["limitation"],"Theo dõi vị trí so với MA20/50, khối lượng, dòng tiền và độ rộng; chưa có dữ liệu độ rộng để kết luận đồng loạt.",[row["source_id"]],row["latest_date"])
            if group=="securities":
                add("company_impact","Thị trường và hoạt động chứng khoán",fact,
                    "Nếu đà giảm kéo dài, giá tài sản và tài sản bảo đảm có thể chịu áp lực; doanh thu môi giới còn phụ thuộc giá trị giao dịch, thị phần. Không suy lợi nhuận từ chỉ số.",
                    "Kiểm tra doanh thu môi giới, thu nhập cho vay, danh mục tự doanh và dự phòng kỳ tiếp theo.",[row["source_id"]],row["latest_date"])
        else:
            add("macro","Năng lượng và áp lực giá",fact,
                ("Giá hợp đồng gần tăng có thể gây áp lực chi phí năng lượng và CPI; mức truyền dẫn còn phụ thuộc tỷ giá, thuế và giá bán trong nước." if change>0 else "Giá hợp đồng gần giảm có thể giảm một phần áp lực năng lượng; chưa đủ kết luận CPI hoặc chi phí doanh nghiệp sẽ giảm.")+" "+row["limitation"],
                "Đối chiếu giá nhiên liệu trong nước, CPI tháng và cơ cấu chi phí; không lượng hóa tác động nếu chưa có độ nhạy.",[row["source_id"]],row["latest_date"])
    for driver in industry.get("drivers",[])[:2]:
        r=driver["indicator"]
        add("industry","Kênh vĩ mô vào ngành",f"{r['label']} {r['value']:.2f}{r['unit']} ({r['period']}).",driver["channel"],"Kiểm tra số liệu ngành và kết quả doanh nghiệp kỳ mới để xác nhận kênh tác động.",[r["source_id"]],r["period"])
    for c in industry.get("comparisons",[])[:3]:
        ids=[s["source_id"] for s in industry.get("sources",[]) if s.get("source_id")]
        add("industry",c["label"]+" trong nhóm so sánh",f"Doanh nghiệp {c['company_value']:.2f}{c['unit']}; trung vị {c['sample_size']} mã {c['sample_median']:.2f}{c['unit']} tại {c['period_end']}.",
            "Chênh lệch phản ánh vị trí trong mẫu; cần kiểm tra tăng trưởng lặp lại, đòn bẩy và khoản bất thường trước khi áp dụng mức định giá cao/thấp hơn.",
            "Cập nhật mẫu cùng kỳ và theo dõi chất lượng lợi nhuận.",ids,c["period_end"])
    channels={"oil":"Nếu biến động dầu truyền vào nhiên liệu/vận tải, chi phí và biên lợi nhuận có thể thay đổi; doanh nghiệp dầu khí có mức hưởng lợi/rủi ro khác nhau.",
              "inflation":"Áp lực giá có thể ảnh hưởng sức mua, chi phí và yêu cầu lợi suất; cần kiểm tra khả năng chuyển giá.",
              "rates":"Thay đổi lãi suất có thể ảnh hưởng chi phí vốn và định giá; ngân hàng còn phụ thuộc chênh lệch lãi suất và dự phòng.",
              "currency":"Biến động tỷ giá có tác động khác nhau với doanh nghiệp xuất khẩu, nhập khẩu và vay ngoại tệ.",
              "market":"Diễn biến dòng tiền cần đọc cùng chỉ số và giao dịch; nhận định trong báo chưa phải tín hiệu định lượng đã xác nhận.",
              "growth":"Thay đổi cầu/đầu tư có thể truyền sang đơn hàng và doanh thu; cần kiểm tra tỷ trọng thị trường của doanh nghiệp."}
    for article in news.get("articles",[]):
        # Export at most 22 words quoted from one article; full body is input evidence only.
        title=" ".join(article["title"].split()[:22])
        tags=article.get("topics",[]);channel=channels.get(next(iter(tags),""),"Thông tin ngành cần được đối chiếu với kết quả doanh nghiệp trước khi điều chỉnh dự báo.")
        add(article["scope"],"Thông tin cập nhật",f"Bài công khai ngày {article['period']}: {title}.",
            "Nguồn báo chí đang đề cập vấn đề này; đây là kênh tác động có điều kiện, không chứng nhận mọi phát biểu trong bài. "+channel,
            "Mở bài gốc, kiểm tra kỳ của số liệu và thông báo chính thức; chỉ điều chỉnh dự báo sau khi xác nhận.",[article["source_id"]],article["period"])
    return out
