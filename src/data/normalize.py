"""Strict annual KBS parser. Currency values requested in thousands of VND."""
from __future__ import annotations
import calendar
from datetime import date
import math

from src.data.providers import DataSourceError

FIELD_IDS = {
    "income": {2216: "revenue", 2217: "gross_profit", 2207: "cost_of_sales", 2212: "net_profit",
               2214: "parent_profit", 2215: "eps", 2232: "pretax_profit", 2223: "interest_expense"},
    "balance": {2996: "assets", 2997: "liabilities", 2998: "equity", 5320: "non_controlling_equity",
                3077: "short_debt", 3078: "long_debt", 3003: "cash", 3000: "current_assets", 3012: "current_liabilities"},
    "cashflow": {2234: "cfo"},
}
FIELD_IDS["income"].update({4378:"net_profit",4380:"parent_profit",4381:"eps",4385:"net_interest_income",4391:"operating_cost",4376:"pre_provision_profit",4392:"credit_provision",4377:"pretax_profit",
    4590:"revenue",4585:"net_profit",4587:"parent_profit",4588:"eps",4599:"brokerage_revenue",5436:"lending_revenue",4584:"pretax_profit"})
FIELD_IDS["balance"].update({4375:"assets",4304:"liabilities",4325:"equity",5699:"non_controlling_equity",4348:"customer_loans",4320:"customer_deposits",
    4476:"assets",4477:"liabilities",4478:"equity",4482:"non_controlling_equity",5373:"financial_loans"})


def parse_annual_financials(payload: dict, kind: str, as_of: date, source_id: str, issues: list | None=None) -> list[dict]:
    heads = payload.get("Head", [])
    if not heads:
        raise DataSourceError("Nguồn không có metadata kỳ tài chính")
    # Live source probes show pageSize 1/2 mislabels old values as recent years.
    # Fetch exactly four annual periods and reject any ambiguous head/value layout.
    if [h.get("ID") for h in heads] != [1, 2, 3, 4]:
        raise DataSourceError("Ánh xạ kỳ/Value không rõ ràng; không sử dụng số liệu")
    if len({h.get("YearPeriod") for h in heads}) != 4:
        raise DataSourceError("Kỳ tài chính bị trùng")
    rows = [r for group in payload.get("Content", {}).values() for r in group]
    parsed = []
    for head in heads:
        if head.get("TermCode") != "N":
            raise DataSourceError("Chỉ nhận báo cáo năm; không tự coi quý lũy kế là quý độc lập")
        published = head.get("DatePubDepartment")
        if not published or date.fromisoformat(published[:10]) > as_of:
            continue
        updated = head.get("LastUpdate")
        if updated and date.fromisoformat(updated[:10]) > as_of:
            continue  # Do not use a later source revision for an earlier analysis date.
        year = int(head["YearPeriod"])
        end = str(head.get("PeriodEnd") or f"{year}12")
        begin = str(head.get("PeriodBegin") or f"{year}01")
        if not end.isdigit() or not begin.isdigit() or len(end)!=6 or len(begin)!=6:
            raise DataSourceError("Metadata ngày đầu/cuối kỳ không hợp lệ")
        end_year,end_month=int(end[:4]),int(end[4:])
        if not 1<=end_month<=12:
            raise DataSourceError("Tháng cuối kỳ không hợp lệ")
        period_end=date(end_year,end_month,calendar.monthrange(end_year,end_month)[1]).isoformat()
        months=(end_year-int(begin[:4]))*12+end_month-int(begin[4:])+1
        if months!=12 or date.fromisoformat(period_end)>min(as_of,date.fromisoformat(published[:10])):
            if issues is not None:issues.append(f"{source_id}: loại kỳ {year}, metadata {begin}–{end} không phải 12 tháng đã kết thúc trước công bố")
            continue
        scope = {"HN": "consolidated", "CTM": "parent", "ĐL": "separate"}.get(head.get("United"), "unknown")
        fields = {}
        raw_fields = []
        for row in rows:
            value = row.get(f"Value{head['ID']}")
            key = FIELD_IDS[kind].get(row.get("ReportNormID"))
            if value is None:
                continue
            try:
                value = float(value)
                if not math.isfinite(value):
                    continue
            except (ValueError, TypeError):
                continue
            unit = "VND_per_share" if row.get("ReportNormID") in {2215,4381,4588,5480} else "VND"
            normalized = value if unit == "VND_per_share" else value * 1000
            provenance = {"value": normalized, "unit": unit, "source_id": source_id,
                          "source_field": row.get("ReportNormID"), "source_label": row.get("Name"),
                          "source_value": value, "unit_multiplier": 1 if unit == "VND_per_share" else 1000,
                          "period": str(year), "published_at": published[:10], "statement_scope": scope}
            raw_fields.append(provenance)
            if key:
                fields[key] = provenance
        parsed.append({"year": year, "period_end": period_end, "period_begin": begin, "published_at": published[:10],
                       "scope": scope, "business_type": head.get("BusinessType"), "audit": head.get("AuditedStatus"),
                       "fields": fields, "raw_fields": raw_fields, "source_id": source_id})
    return parsed
