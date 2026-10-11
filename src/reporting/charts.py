"""Price charts show Close; historical risk calculations retain their own basis."""
from __future__ import annotations
from pathlib import Path

def market_chart(result, folder: Path):
    if not result.get("market"):return None
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    frame=pd.DataFrame(result["price_rows"]);dates=pd.to_datetime(frame["date"])
    values=pd.Series(result["market"]["chart_prices"])
    plt.rcParams['font.size']=10
    fig,axes=plt.subplots(2,1,figsize=(3.5,3.8),sharex=True,gridspec_kw={"height_ratios":[3,1]})
    axes[0].plot(dates,values,color="#14566e",label="Giá đóng cửa")
    for days,color in [(20,"#d99d32"),(50,"#5a927b")]:
        if result["market"].get("history_indicators_available",True):
            axes[0].plot(dates,values.rolling(days).mean(),color=color,label=f"MA{days}",linewidth=1)
    axes[0].set_ylabel("VND / CP");axes[0].legend(fontsize=9,loc="upper left")
    axes[1].bar(dates,frame["volume"]/1e6,color="#94b2bc",width=1.8);axes[1].set_ylabel("Triệu CP")
    for ax in axes:ax.grid(alpha=.18);ax.spines[["top","right"]].set_visible(False)
    fig.autofmt_xdate();fig.tight_layout();folder.mkdir(parents=True,exist_ok=True)
    path=folder/"market.png";fig.savefig(path,dpi=160);plt.close(fig)
    return path


def research_chart(result, kind, folder: Path):
    """All plotted values come from the saved analysis; absent values stay absent."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams["font.family"]="DejaVu Sans"
    plt.rcParams["font.size"]=11
    fig=None
    if kind=="financial":
        periods=list(reversed(result["financial"]["periods"]))
        if not periods:return None
        bank=result["financial"].get("industry_group")=="bank"
        keys=[("net_interest_income","Thu nhập lãi thuần"),("net_profit","LNST"),("cfo","CFO")] if bank else [("revenue","Doanh thu"),("net_profit","LNST"),("cfo","CFO")]
        fig,axes=plt.subplots(3,1,figsize=(3.5,6.2))
        for ax,(key,label) in zip(axes,keys):
            values=[p["fields"].get(key,{}).get("value") for p in periods]
            pairs=[(str(p["year"]),v/1e9) for p,v in zip(periods,values) if v is not None]
            if pairs:ax.bar([p[0] for p in pairs],[p[1] for p in pairs],color="#207a78");ax.set_title(label,fontsize=12)
            else:ax.text(.5,.5,"Chưa đủ dữ liệu",ha="center",transform=ax.transAxes)
            ax.tick_params(axis="x",labelrotation=45,labelsize=10)
            ax.set_ylabel("Tỷ VND");ax.grid(axis="y",alpha=.15);ax.set_axisbelow(True)
    elif kind=="industry":
        rows=([{**c,"unit":"x"} for c in result.get("valuation",{}).get("primary",{}).get("comparisons",[])]+[c for c in result.get("industry",{}).get("comparisons",[]) if c["key"] in {"roe","roa","cir","net_margin"}])[:3]
        if not rows:return None
        fig,axes=plt.subplots(len(rows),1,figsize=(3.5,2.1*len(rows)),squeeze=False)
        for ax,c in zip(axes[:,0],rows):
            ax.bar([result["request"]["ticker"],f"Trung vị\nn={c['sample_size']}"],[c["company_value"],c["sample_median"]],color=["#14566e","#d5a144"])
            ax.tick_params(axis="x",labelsize=10)
            ax.set_title({"pe":"P/E năm", "pb":"P/B", "roe":"ROE", "roa":"ROA", "cir":"CIR", "net_margin":"Biên ròng"}.get(c["key"],c["label"]),fontsize=11);ax.set_ylabel(c["unit"]);ax.grid(axis="y",alpha=.15)
            for i,v in enumerate([c["company_value"],c["sample_median"]]):ax.annotate(f"{v:.2f}",(i,v),ha="center",va="bottom",fontsize=10)
    elif kind=="macro":
        current=result.get("market_context",{}).get("series",[])
        rows=[r for r in result.get("macro",{}).get("annual_history",[]) if r["key"] in {"gdp_annual","cpi_annual"}]
        if current:
            import pandas as pd
            fig,axes=plt.subplots(len(current),1,figsize=(3.5,2.3*len(current)),squeeze=False)
            for ax,row in zip(axes[:,0],current):
                ax.plot(pd.to_datetime([r["date"] for r in row["rows"]]),[r["close"] for r in row["rows"]],color="#207a78")
                ax.set_title("VN-Index" if row["symbol"]=="VNINDEX" else "Brent futures - hợp đồng gần");ax.set_ylabel(row["unit"]);ax.grid(alpha=.15);ax.tick_params(axis='x',labelrotation=35,labelsize=8)
        elif rows:
            fig,axes=plt.subplots(2,1,figsize=(3.5,4.4))
            for ax,key,label in zip(axes,["gdp_annual","cpi_annual"],["GDP thực tăng trưởng năm","CPI bình quân năm"]):
                selected=sorted([r for r in rows if r["key"]==key],key=lambda r:r["period"])
                ax.plot([r["period"] for r in selected],[r["value"] for r in selected],marker="o",color="#207a78");ax.set_title(label);ax.set_ylabel("% / năm");ax.grid(alpha=.15)
        else:return None
    elif kind=="valuation":
        rows=[(m["method"],m["target_price_vnd"]) for m in result["valuation"].get("primary",{}).get("methods",[])]
        if not rows:return None
        fig,ax=plt.subplots(figsize=(3.5,2.6));ax.barh([str(i+1) for i in range(len(rows))],[r[1]/1000 for r in rows],color="#207a78")
        ax.set_title("Định giá từ mẫu so sánh",fontsize=11)
        if result.get("market"):ax.axvline(result["market"]["latest_close_vnd"]/1000,color="#ca714b",ls="--",label="Giá đóng cửa");ax.legend(loc="lower right",fontsize=10)
        ax.set_xlim(left=0);ax.set_xlabel("Nghìn VND / CP");ax.grid(axis="x",alpha=.15)
    elif kind=="sensitivity":
        pe=result["valuation"].get("pe",{})
        if not pe.get("available"):return None
        multiples=[pe["target_pe"]*f for f in [.8,1,1.2]];factors=[.9,1,1.1]
        values=np.array([[pe["eps"]*f*m for m in multiples] for f in factors])
        fig,ax=plt.subplots(figsize=(3.5,3.1));ax.imshow(values,cmap="YlGnBu",aspect="auto")
        ax.set_xticks(range(3),[f"{m:.1f}x" for m in multiples]);ax.set_yticks(range(3),["-10%","Cơ sở","+10%"])
        ax.set_xlabel("P/E giả định");ax.set_ylabel("Thay đổi lợi nhuận giả định")
        for i in range(3):
            for j in range(3):ax.text(j,i,f"{values[i,j]:,.0f}",ha="center",va="center",color="white" if values[i,j]>np.mean(values) else "#163640",fontsize=11)
    elif kind=="reference":
        reports=[r for r in result.get('reference',{}).get('reports',[]) if r.get('inspection',{}).get('pages')]
        if not reports:return None
        fig,ax=plt.subplots(figsize=(3.5,2.7));ax.bar([str(r['year']) for r in reports],[r['inspection']['pages'] for r in reports],color='#207a78')
        ax.set_title('BCTN đã tải');ax.set_ylabel('Số trang PDF');ax.grid(axis='y',alpha=.15)
    elif kind=="news":
        items=result.get('news',[])[:8]
        if not items:return None
        days=sorted({r['published_at'] for r in items})
        company=[sum(r['published_at']==d and r.get('news_scope')!='industry_peer' for r in items) for d in days]
        peers=[sum(r['published_at']==d and r.get('news_scope')=='industry_peer' for r in items) for d in days]
        fig,ax=plt.subplots(figsize=(3.5,3.3));ax.barh(days,company,label='Doanh nghiệp',color='#207a78');ax.barh(days,peers,left=company,label='Mã cùng ngành',color='#d5a144')
        ax.set_title('Mẫu tin truy xuất');ax.set_xlabel('Số mục tin');ax.legend(fontsize=9)
    if fig is None:return None
    fig.tight_layout()
    folder.mkdir(parents=True,exist_ok=True);path=folder/f"{kind}.png"
    fig.savefig(path,dpi=180,bbox_inches="tight");plt.close(fig);return path
