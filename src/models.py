"""Validated user request and stable report-section identifiers."""
from dataclasses import dataclass, field, asdict
from datetime import date
import math

SECTION_LABELS = {"overview": "Tổng quan", "macro": "Tổng quan vĩ mô", "industry": "Phân tích ngành", "market": "Giá và giao dịch", "financial": "Tài chính",
                  "reference": "Dữ liệu và báo cáo bổ sung", "valuation": "Định giá theo giả định", "news": "Tin tức", "risks": "Cơ hội và rủi ro"}


@dataclass
class AnalysisRequest:
    ticker: str
    start: date
    as_of: date
    mode: str = "full"
    sections: list[str] = field(default_factory=lambda: list(SECTION_LABELS))
    target_pb: float = 1.5
    target_pe: float = 12.0
    cost_of_equity: float = .115
    terminal_growth: float = .035
    forecast_growth: float = .07
    wacc: float = .10
    tax_rate: float = .20
    use_ai: bool = False

    def __post_init__(self):
        if self.mode not in {"summary", "full"}:
            raise ValueError("Chế độ báo cáo không hợp lệ.")
        if not self.sections or set(self.sections) - set(SECTION_LABELS):
            raise ValueError("Chọn ít nhất một phần báo cáo hợp lệ.")
        if not math.isfinite(self.target_pb) or not 0 < self.target_pb <= 20:
            raise ValueError("P/B giả định phải lớn hơn 0 và không quá 20.")
        if not math.isfinite(self.target_pe) or not 0<self.target_pe<=100:
            raise ValueError("P/E giả định phải lớn hơn 0 và không quá 100.")
        for key in ["cost_of_equity","wacc","terminal_growth","forecast_growth","tax_rate"]:
            if not math.isfinite(getattr(self,key)):raise ValueError("Giả định phải hữu hạn.")
        if not 0<self.cost_of_equity<1 or not 0<self.wacc<1 or not 0<=self.terminal_growth<1 or not -1<self.forecast_growth<1 or not 0<=self.tax_rate<1:
            raise ValueError("Giả định lãi suất/tăng trưởng/thuế không hợp lệ.")

    def to_dict(self):
        return {**asdict(self), "start": self.start.isoformat(), "as_of": self.as_of.isoformat()}
