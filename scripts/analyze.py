"""Automatically fetch, analyze and export without pre-existing data files."""
import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.data.providers import VN_TIME
from src.models import SECTION_LABELS
from src.pipeline import run_analysis
from src.reporting.pdf_exporter import generate_report

def main():
    if hasattr(sys.stdout,"reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    today=datetime.now(VN_TIME).date()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker")
    parser.add_argument("--start",type=date.fromisoformat,default=today-timedelta(days=365))
    parser.add_argument("--as-of",type=date.fromisoformat,default=today)
    parser.add_argument("--mode",choices=["summary","full"],default="full")
    parser.add_argument("--sections",nargs="+",choices=list(SECTION_LABELS),default=list(SECTION_LABELS))
    parser.add_argument("--target-pb",type=float,default=1.5)
    parser.add_argument("--target-pe",type=float,default=12.)
    parser.add_argument("--cost-of-equity",type=float,default=.115)
    parser.add_argument("--wacc",type=float,default=.10)
    parser.add_argument("--terminal-growth",type=float,default=.035)
    parser.add_argument("--forecast-growth",type=float,default=.07)
    parser.add_argument("--tax-rate",type=float,default=.20)
    parser.add_argument("--use-ai",action="store_true")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=run_analysis(args.ticker,args.start,args.as_of,mode=args.mode,sections=args.sections,target_pb=args.target_pb,
                        target_pe=args.target_pe,cost_of_equity=args.cost_of_equity,wacc=args.wacc,terminal_growth=args.terminal_growth,
                        forecast_growth=args.forecast_growth,tax_rate=args.tax_rate,use_ai=args.use_ai)
    if not result["market"] and not result["financial"]["metrics"]:
        print("Không lấy được dữ liệu phân tích:",result["errors"]);return 1
    path=generate_report(result,args.output)
    print("PDF:",path);print("Trạng thái:",result["status"])
    return 0

if __name__=="__main__":raise SystemExit(main())
