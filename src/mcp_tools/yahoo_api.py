"""
yahoo_api.py — yfinance 数据源封装（主力数据源，US-friendly）
Yahoo Finance 从 Render 美国服务器可正常访问，免费、无需 API Key。
覆盖：股票基本信息、财务报表、日线行情、新闻舆情。

注意：yfinance 采用懒加载模式，未安装时返回友好错误信息。
"""
import pandas as pd
from datetime import datetime, timedelta

_yf = None


def _get_yf():
    """懒加载 yfinance，避免未安装时阻塞其他模块导入"""
    global _yf
    if _yf is None:
        try:
            import yfinance as yf
            _yf = yf
        except ImportError:
            raise ImportError("yfinance 未安装，请执行: pip install yfinance")
    return _yf


def _ts_to_yf_symbol(ts_code: str) -> str:
    """将 Tushare 格式代码转为 Yahoo Finance 格式
    Tushare .SH → Yahoo .SS（上海交易所）
    Tushare .SZ → Yahoo .SZ（深圳交易所，相同）
    """
    if "." in ts_code:
        code, exchange = ts_code.split(".")
        if exchange.upper() == "SH":
            return f"{code}.SS"
        return ts_code  # .SZ 及其他保持不变
    return ts_code


def _ts_code_to_symbol(ts_code: str) -> str:
    """将 Tushare 格式代码转为纯数字代码"""
    return ts_code.split(".")[0] if "." in ts_code else ts_code


# ============================================================
# 股票基本信息 + 估值快照
# ============================================================

def get_stock_info_yahoo(ts_code: str) -> str:
    """
    获取股票基本信息与估值指标（yfinance）
    参数: ts_code — 股票代码（如 "000001.SZ" / "600519.SH"）
    返回: 名称、行业、市值、PE/PB/PS、股息率等
    """
    symbol = _ts_to_yf_symbol(ts_code)
    try:
        yf = _get_yf()
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            # 可能是不活跃的股票，尝试用 info 中的其他字段判断
            if not info or not info.get("longName"):
                return f"Yahoo Finance 未返回 {symbol} 的基本信息（可能代码格式不对或已退市）"

        result = f"【Yahoo Finance 股票信息】（{ts_code}）\n"
        result += f"名称: {info.get('longName', info.get('shortName', 'N/A'))}\n"
        result += f"行业: {info.get('industry', 'N/A')}\n"
        result += f"板块: {info.get('sector', 'N/A')}\n"
        result += f"国家: {info.get('country', 'N/A')}\n"
        result += f"网站: {info.get('website', 'N/A')}\n\n"

        result += "【估值指标】\n"
        result += f"最新价格: {info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))}\n"
        result += f"总市值: {_fmt_value(info.get('marketCap', 'N/A'))}\n"
        result += f"流通市值: {_fmt_value(info.get('floatShares', 'N/A'))}\n"
        result += f"PE(TTM): {info.get('trailingPE', 'N/A')}\n"
        result += f"远期PE: {info.get('forwardPE', 'N/A')}\n"
        result += f"PB: {info.get('priceToBook', 'N/A')}\n"
        result += f"PS(TTM): {info.get('priceToSalesTrailing12Months', 'N/A')}\n"
        result += f"PEG: {info.get('pegRatio', 'N/A')}\n"
        result += f"股息率: {info.get('dividendYield', 'N/A')}\n"
        result += f"Beta: {info.get('beta', 'N/A')}\n"
        result += f"52周最高: {info.get('fiftyTwoWeekHigh', 'N/A')}\n"
        result += f"52周最低: {info.get('fiftyTwoWeekLow', 'N/A')}\n"
        result += f"50日均价: {info.get('fiftyDayAverage', 'N/A')}\n"
        result += f"200日均价: {info.get('twoHundredDayAverage', 'N/A')}\n"

        # 财务健康指标
        result += "\n【财务健康快照】\n"
        result += f"ROE: {_fmt_pct(info.get('returnOnEquity', 'N/A'))}\n"
        result += f"ROA: {_fmt_pct(info.get('returnOnAssets', 'N/A'))}\n"
        result += f"营收增速(YoY): {_fmt_pct(info.get('revenueGrowth', 'N/A'))}\n"
        result += f"利润增速(YoY): {_fmt_pct(info.get('earningsGrowth', 'N/A'))}\n"
        result += f"毛利率: {_fmt_pct(info.get('grossMargins', 'N/A'))}\n"
        result += f"净利率: {_fmt_pct(info.get('profitMargins', 'N/A'))}\n"
        result += f"资产负债率: {_fmt_pct(info.get('debtToEquity', 'N/A'))}\n"
        result += f"流动比率: {info.get('currentRatio', 'N/A')}\n"
        result += f"速动比率: {info.get('quickRatio', 'N/A')}\n"
        result += f"每股收益: {info.get('trailingEps', 'N/A')}\n"
        result += f"每股净资产: {info.get('bookValue', 'N/A')}\n"
        result += f"自由现金流: {_fmt_value(info.get('freeCashflow', 'N/A'))}\n"
        result += f"经营现金流: {_fmt_value(info.get('operatingCashflow', 'N/A'))}\n"

        return result
    except Exception as e:
        return f"Yahoo Finance 基本信息获取失败: {str(e)}"


# ============================================================
# 财务报表
# ============================================================

def get_financials_yahoo(ts_code: str) -> str:
    """
    获取财务报表核心指标（yfinance 季度/年度）
    参数: ts_code — 股票代码
    返回: 利润表 + 资产负债表关键行
    """
    symbol = _ts_to_yf_symbol(ts_code)
    try:
        yf = _get_yf()
        ticker = yf.Ticker(symbol)

        result = f"【Yahoo Finance 财务报表】（{ts_code}）\n\n"

        # ---- 年度利润表 ----
        try:
            income = ticker.financials  # 年度
            if income is not None and not income.empty:
                result += "【年度利润表摘要】（最近2年）\n"
                cols = income.columns[:2] if len(income.columns) >= 2 else income.columns
                for col in cols:
                    result += f"\n报告期: {col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col)}\n"
                    for idx in ['Total Revenue', 'Operating Income', 'Net Income',
                                 'EBITDA', 'Gross Profit', 'Operating Expense']:
                        if idx in income.index:
                            val = income.loc[idx, col]
                            result += f"  {idx}: {_fmt_value(val)}\n"
        except Exception:
            result += "【年度利润表】获取失败\n"

        # ---- 年度资产负债表 ----
        try:
            balance = ticker.balance_sheet
            if balance is not None and not balance.empty:
                result += "\n【年度资产负债表摘要】（最近1期）\n"
                col = balance.columns[0]
                result += f"报告期: {col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col)}\n"
                for idx in ['Total Assets', 'Total Liabilities Net Minority Interest',
                             'Stockholders Equity', 'Total Debt', 'Current Assets',
                             'Current Liabilities', 'Cash And Cash Equivalents']:
                    if idx in balance.index:
                        val = balance.loc[idx, col]
                        result += f"  {idx}: {_fmt_value(val)}\n"
        except Exception:
            result += "\n【年度资产负债表】获取失败\n"

        # ---- 季度利润表 ----
        try:
            income_q = ticker.quarterly_financials
            if income_q is not None and not income_q.empty:
                result += "\n【季度利润表摘要】（最近1期）\n"
                col = income_q.columns[0]
                result += f"报告期: {col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col)}\n"
                for idx in ['Total Revenue', 'Operating Income', 'Net Income', 'Gross Profit']:
                    if idx in income_q.index:
                        val = income_q.loc[idx, col]
                        result += f"  {idx}: {_fmt_value(val)}\n"
        except Exception:
            pass

        if "【年度利润表】" not in result and "【年度资产负债表】" not in result:
            return result + "未能获取任何财务数据，请检查股票代码"

        return result
    except Exception as e:
        return f"Yahoo Finance 财务报表获取失败: {str(e)}"


# ============================================================
# 日线行情
# ============================================================

def get_daily_quote_yahoo(ts_code: str, days: int = 60) -> str:
    """
    获取个股历史日线行情（yfinance）
    参数: ts_code — 股票代码
          days — 返回最近交易天数，默认 60
    返回: OHLCV 日线数据 + MA 统计
    """
    symbol = _ts_to_yf_symbol(ts_code)
    try:
        yf = _get_yf()
        ticker = yf.Ticker(symbol)

        # 取最近 2 × days 日历日，确保覆盖足够交易日
        start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y-%m-%d")
        end = datetime.now().strftime("%Y-%m-%d")
        df = ticker.history(start=start, end=end, auto_adjust=False)

        if df is None or df.empty:
            return f"Yahoo Finance 未返回 {symbol} 的日线行情数据"

        df = df.tail(days)
        result = f"【Yahoo Finance 日线行情】（{ts_code}，最近{len(df)}个交易日）\n\n"
        result += "日期       | 开盘   | 最高   | 最低   | 收盘   | 成交量     | 涨跌幅\n"
        result += "-" * 80 + "\n"

        prev_close = None
        for idx, row in df.iterrows():
            date = idx.strftime("%Y-%m-%d") if hasattr(idx, 'strftime') else str(idx)[:10]
            open_ = row.get("Open", 0)
            high = row.get("High", 0)
            low = row.get("Low", 0)
            close = row.get("Close", 0)
            volume = row.get("Volume", 0)
            pct = ((close / prev_close - 1) * 100) if prev_close else 0
            prev_close = close
            result += f"{date} | {open_:>6.2f} | {high:>6.2f} | {low:>6.2f} | {close:>6.2f} | {int(volume):>10d} | {pct:>+.2f}%\n"

        # 统计摘要
        close_series = df["Close"]
        result += f"\n【统计摘要】\n"
        result += f"区间最高价: {df['High'].max():.2f}\n"
        result += f"区间最低价: {df['Low'].min():.2f}\n"
        result += f"最新收盘价: {close_series.iloc[-1]:.2f}\n"
        if len(close_series) > 1:
            result += f"区间涨跌幅: {((close_series.iloc[-1] / close_series.iloc[0] - 1) * 100):+.2f}%\n"
        result += f"平均日成交量: {int(df['Volume'].mean())} 股\n"

        # MA 均线
        if len(df) >= 5:
            result += f"5日均线: {close_series.tail(5).mean():.2f}\n"
        if len(df) >= 10:
            result += f"10日均线: {close_series.tail(10).mean():.2f}\n"
        if len(df) >= 20:
            result += f"20日均线: {close_series.tail(20).mean():.2f}\n"
        if len(df) >= 60:
            result += f"60日均线: {close_series.tail(60).mean():.2f}\n"

        # 波动率
        if len(df) >= 20:
            daily_returns = close_series.pct_change().dropna()
            if len(daily_returns) > 0:
                volatility = daily_returns.tail(20).std() * (252 ** 0.5) * 100
                result += f"20日年化波动率: {volatility:.2f}%\n"

        return result
    except Exception as e:
        return f"Yahoo Finance 日线行情获取失败: {str(e)}"


# ============================================================
# 新闻舆情
# ============================================================

def get_news_yahoo(ts_code: str, limit: int = 15) -> str:
    """
    获取个股相关新闻（yfinance）
    参数: ts_code — 股票代码
          limit — 返回条数
    返回: 新闻标题、来源、发布时间
    """
    symbol = _ts_to_yf_symbol(ts_code)
    try:
        yf = _get_yf()
        ticker = yf.Ticker(symbol)
        news = ticker.news

        if not news:
            return f"Yahoo Finance 未返回 {symbol} 的相关新闻"

        result = f"【Yahoo Finance 个股新闻】（{ts_code}，{min(limit, len(news))}条）\n\n"
        for i, item in enumerate(news[:limit]):
            title = item.get("title", item.get("content", {}).get("title", ""))
            source = item.get("source", item.get("content", {}).get("source", ""))
            pub_time = ""
            try:
                pub_ts = item.get("providerPublishTime", 0)
                if pub_ts:
                    pub_time = datetime.fromtimestamp(pub_ts).strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass
            link = item.get("link", "")
            result += f"{i+1}. [{pub_time}] {title}"
            if source:
                result += f" | 来源: {source}"
            result += "\n"

        return result
    except Exception as e:
        return f"Yahoo Finance 新闻获取失败: {str(e)}"


# ============================================================
# 综合数据获取（一次返回所有信息）
# ============================================================

def get_comprehensive_yahoo(ts_code: str) -> str:
    """
    综合获取 Yahoo Finance 所有数据：基本信息 + 估值 + 财务 + 行情摘要
    用于快速预览，减少 Agent tool call 次数
    """
    parts = []

    info = get_stock_info_yahoo(ts_code)
    if "获取失败" not in info and "未返回" not in info:
        parts.append(info)
    else:
        parts.append(f"基本信息: {info.split(chr(10))[0] if info else 'N/A'}")

    quote = get_daily_quote_yahoo(ts_code, days=10)
    if "获取失败" not in quote and "未返回" not in quote:
        # 只取统计摘要部分
        summary_start = quote.find("【统计摘要】")
        if summary_start >= 0:
            parts.append(quote[summary_start:])
        else:
            parts.append(quote[:500])
    else:
        parts.append(f"行情数据: {quote[:100] if quote else 'N/A'}")

    return "\n\n".join(parts)


# ============================================================
# 辅助函数
# ============================================================

def _fmt_value(val) -> str:
    """格式化数值（自动转换大数）"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        v = float(val)
        if abs(v) >= 1e11:
            return f"{v/1e8:.2f} 亿"
        elif abs(v) >= 1e8:
            return f"{v/1e8:.2f} 亿"
        elif abs(v) >= 1e4:
            return f"{v/1e4:.2f} 万"
        return f"{v:.2f}"
    except (ValueError, TypeError):
        return str(val)


def _fmt_pct(val) -> str:
    """格式化百分比"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    try:
        return f"{float(val) * 100:.2f}%"
    except (ValueError, TypeError):
        return str(val)
