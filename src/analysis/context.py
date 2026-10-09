"""Evidence-based links from macro conditions through industry to the company."""
import statistics

SECTOR_SIGNALS={"21":["construction_growth","industrial_growth","investment_growth"],"24":["construction_growth","investment_growth"],
 "3":["construction_growth","credit_growth"],"19":["real_retail_growth","cpi_ytd"],"7":["real_retail_growth","cpi_ytd"],
 "6":["telecom_growth","exports_growth"],"11":["credit_growth","cpi_ytd"],"5":["credit_growth","gdp_ytd"],
 "23":["exports_growth","industrial_growth"],"20":["exports_growth","cpi_ytd"],"10":["industrial_growth","exports_growth"],
 "22":["industrial_growth","gdp_ytd"],"25":["real_retail_growth","gdp_ytd"]}
ICB_SIGNALS={"1757":["construction_growth","industrial_growth","exports_growth"],"2357":["construction_growth","investment_growth"],
 "3577":["real_retail_growth","cpi_ytd"],"3533":["real_retail_growth","cpi_ytd"],"9537":["gdp_ytd","exports_growth"],
 "9533":["gdp_ytd","exports_growth"],"8355":["credit_growth","cpi_ytd"],"8777":["credit_growth","gdp_ytd"],
 "5379":["real_retail_growth","cpi_ytd"],"8633":["construction_growth","credit_growth"],"7535":["industrial_growth","gdp_ytd"],
 "1357":["industrial_growth","exports_growth"],"9500":["gdp_ytd","exports_growth"],"9530":["gdp_ytd","exports_growth"]}

def analyze_context(macro,industry,financial):
    indicators={r["key"]:r for r in macro["indicators"]}
    macro["observations"]=[]
    for key in ["gdp_ytd","gdp_year","cpi_ytd","credit_growth","usd_index_yoy"]:
        row=indicators.get(key)
        if row:macro["observations"].append(f"{row['label']}: {row['value']:.2f}% ({row['period']}, công bố {row['published_at']}).")
    macro["assessment"]="Nền tăng trưởng, sức mua, giá cả và tín dụng cần được đọc cùng kỳ. GDP dương không bảo đảm mọi ngành/doanh nghiệp tăng lợi nhuận; CPI tăng có thể tác động giá đầu vào và sức mua. Chỉ số giá USD không phải tỷ giá giao ngay."
    target_metrics={m["key"]:m for m in financial["metrics"]}
    rows=[]
    for peer in industry["peers"]:
        metrics={m["key"]:m for m in peer["financial"]["metrics"]}
        rows.append({"ticker":peer["ticker"],"period_end":industry["period_end"],"values":{k:metrics.get(k,{}).get("value") for k in ["revenue_growth","net_profit_growth","roe","roa","net_margin","debt_equity","loan_deposit","cir","brokerage_share","lending_share"]}})
    industry["comparison_rows"]=rows;industry["comparisons"]=[]
    for key in ["revenue_growth","net_profit_growth","roe","roa","net_margin","debt_equity","loan_deposit","cir","brokerage_share","lending_share"]:
        own=target_metrics.get(key);sample=[row["values"][key] for row in rows if row["values"].get(key) is not None]
        if not own or own["value"] is None or len(sample)<2:continue
        middle=statistics.median(sample)
        industry["comparisons"].append({"key":key,"label":own["label"],"company_value":own["value"],"sample_median":middle,"difference":own["value"]-middle,"unit":own["unit"],"sample_size":len(sample),"period_end":industry["period_end"],"formula":"Trung vị giá trị của các doanh nghiệp mẫu, loại mã phân tích; chênh lệch = mã phân tích - trung vị"})
    industry["drivers"]=[]
    code=industry.get("code")
    signal_map=ICB_SIGNALS if industry.get("taxonomy")=="Vietcap ICB" else SECTOR_SIGNALS
    for key in signal_map.get(code,["gdp_ytd","cpi_ytd","credit_growth"]):
        row=indicators.get(key)
        if not row:continue
        channel={"construction_growth":"Nhu cầu xây dựng có thể truyền sang vật liệu/đơn hàng; cần kiểm tra doanh thu thực tế, không coi tăng trưởng xây dựng là tăng trưởng riêng của doanh nghiệp.",
         "industrial_growth":"Hoạt động sản xuất là chỉ báo nhu cầu đầu vào; tác động tùy thị phần và cơ cấu khách hàng.",
         "investment_growth":"Đầu tư theo giá hiện hành là bối cảnh nhu cầu; cần phân biệt danh nghĩa, thực và tiến độ triển khai.",
         "real_retail_growth":"Tiêu dùng loại trừ giá giúp đánh giá sức mua; không đồng nghĩa doanh thu mọi sản phẩm cùng tăng.",
         "telecom_growth":"Viễn thông là chỉ báo một phân khúc của nhóm công nghệ rộng; không đại diện trực tiếp cho xuất khẩu phần mềm.",
         "exports_growth":"Xuất khẩu hàng hóa chỉ là bối cảnh thương mại; nếu doanh nghiệp xuất khẩu dịch vụ/phần mềm thì cần dữ liệu riêng.",
         "credit_growth":"Tín dụng mở rộng ảnh hưởng cầu vốn và thanh khoản; ngân hàng cần kiểm tra chất lượng tài sản, chứng khoán cần kiểm tra thanh khoản giao dịch.",
         "cpi_ytd":"Áp lực giá có thể ảnh hưởng chi phí và sức mua; theo dõi khả năng chuyển giá và biên lợi nhuận.",
         "gdp_ytd":"Nền kinh tế tăng trưởng là bối cảnh cầu; tác động phải được xác nhận bằng kết quả của doanh nghiệp."}.get(key,"Theo dõi kênh truyền dẫn vào doanh nghiệp.")
        if financial.get("industry_group")=="bank":
            channel={"credit_growth":"Tín dụng toàn nền kinh tế mở rộng là bối cảnh cầu vay. Tác động tới ngân hàng phải đọc cùng tăng trưởng cho vay, thu nhập lãi và dự phòng; không suy ra chất lượng tín dụng từ tăng trưởng dư nợ.",
                     "cpi_ytd":"Áp lực lạm phát có thể truyền qua lãi suất huy động, chi phí vốn và khả năng trả nợ của khách hàng. Cần đối chiếu NIM, tái định giá cho vay và nợ xấu trước khi lượng hóa tác động tới lợi nhuận/P/B."}.get(key,channel)
        industry["drivers"].append({"indicator":row,"channel":channel,"interpretation_type":"conditional_inference"})
    industry["structural_risks"]=["Mẫu ưu tiên doanh nghiệp lớn theo tài sản; không đại diện mọi công ty trong nhóm. Khác biệt công ty mẹ/con, sản phẩm và thị trường khiến so sánh cần thận trọng.",
      "Nếu có nguyên liệu/nguồn vốn ngoại tệ, biến động tỷ giá có thể đổi chi phí; nếu có doanh thu ngoại tệ, tác động có thể ngược lại. Chưa lượng hóa vì thiếu cơ cấu ngoại tệ.",
      "Chu kỳ đầu vào, cạnh tranh và khả năng chuyển giá có thể khiến lợi nhuận khác xu hướng vĩ mô; kiểm tra thuyết minh và kết quả kỳ tiếp theo."]
    if financial["industry_group"]=="bank":industry["structural_risks"].append("Ngân hàng: tăng tín dụng không chứng minh chất lượng tín dụng; cần NPL, dự phòng, NIM và CAR trước khi kết luận về an toàn vốn.")
    if financial["industry_group"]=="securities":industry["structural_risks"].append("Chứng khoán: môi giới nhạy với thanh khoản thị trường; cho vay và tự doanh chịu rủi ro giá tài sản, tài sản bảo đảm và chi phí vốn.")
    return macro,industry

def integrated_thesis(macro,industry,financial):
    result=[]
    for driver in industry.get("drivers",[])[:3]:
        row=driver["indicator"]
        result.append(f"Vĩ mô → ngành {industry['name']}: {row['label']} {row['value']:.2f}% ({row['period']}). {driver['channel']}")
    for comparison in industry.get("comparisons",[])[:3]:
        result.append(f"Ngành → doanh nghiệp: {comparison['label']} của mã phân tích {comparison['company_value']:.2f} {comparison['unit']}, trung vị {comparison['sample_size']} doanh nghiệp mẫu {comparison['sample_median']:.2f} {comparison['unit']} tại {comparison['period_end']}. Chênh lệch phản ánh vị trí trong mẫu, không tự xác nhận chất lượng hay giá trị đầu tư.")
    if not result:result.append("Chưa đủ bằng chứng vĩ mô/ngành đồng kỳ để lập luận tổng hợp; chỉ dùng các phân tích doanh nghiệp đã có dữ liệu.")
    return result
