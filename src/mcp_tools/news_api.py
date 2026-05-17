"""
news_api.py — akshare 新闻数据源封装
替代 Tushare 新闻接口（需高积分），提供东方财富、财联社全球财经新闻数据。
同时为基本面/估值 Agent 提供 Tushare 限流时的备选数据。

注意：akshare 采用懒加载模式，安装后（pip install akshare）即可正常使用。
未安装时所有函数返回友好错误信息，不影响其他模块导入。
"""
import pandas as pd
from datetime import datetime, timedelta

_ak = None


def _get_ak():
    """懒加载 akshare，避免未安装时阻塞其他模块导入"""
    global _ak
    if _ak is None:
        try:
            import akshare as ak
            _ak = ak
        except ImportError:
            raise ImportError("akshare 未安装，请执行: pip install akshare")
    return _ak


def _ts_code_to_symbol(ts_code: str) -> str:
    """将 Tushare 格式代码转为纯数字代码"""
    return ts_code.split(".")[0] if "." in ts_code else ts_code


def _ts_code_to_ak_symbol(ts_code: str) -> str:
    """将 Tushare 格式代码转为 akshare 格式（sz000001 / sh600519）"""
    code = ts_code.split(".")[0] if "." in ts_code else ts_code
    suffix = ts_code.split(".")[1].lower() if "." in ts_code else "sz"
    return f"{suffix}{code}"


# ============================================================
# 日线行情备选数据（akshare，Tushare 限流时使用）
# ============================================================

def get_daily_quote_ak(ts_code: str, days: int = 60) -> str:
    """
    获取个股历史日线行情（akshare，作为 Tushare 限流备选）
    参数: ts_code — 股票代码（如 "000001.SZ"）
          days — 返回最近交易天数，默认 60
    返回: OHLCV 日线数据
    """
    symbol = _ts_code_to_symbol(ts_code)
    try:
        ak = _get_ak()
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=(datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d"),
            end_date=datetime.now().strftime("%Y%m%d"),
            adjust="qfq",  # 前复权
        )
        if df is None or df.empty:
            return f"akshare 未返回 {ts_code} 的日线行情数据"

        df = df.tail(days)
        result = f"【akshare 日线行情】（{ts_code}，前复权，最近{len(df)}个交易日）\n\n"
        result += "日期       | 开盘   | 最高   | 最低   | 收盘   | 成交量(手) | 涨跌幅\n"
        result += "-" * 75 + "\n"
        for _, row in df.iterrows():
            date = str(row.get("日期", ""))
            open_ = row.get("开盘", 0)
            high = row.get("最高", 0)
            low = row.get("最低", 0)
            close = row.get("收盘", 0)
            volume = row.get("成交量", 0)
            pct = row.get("涨跌幅", 0)
            result += f"{date} | {open_:>6.2f} | {high:>6.2f} | {low:>6.2f} | {close:>6.2f} | {int(volume):>10d} | {pct:>+.2f}%\n"

        # 附统计摘要
        close_series = df["收盘"]
        result += f"\n【统计摘要】\n"
        result += f"区间最高价: {df['最高'].max():.2f}\n"
        result += f"区间最低价: {df['最低'].min():.2f}\n"
        result += f"最新收盘价: {close_series.iloc[-1]:.2f}\n"
        result += f"区间涨跌幅: {((close_series.iloc[-1] / close_series.iloc[0] - 1) * 100):+.2f}%\n"
        result += f"平均日成交量: {int(df['成交量'].mean())} 手\n"
        # MA
        if len(df) >= 5:
            result += f"5日均线: {close_series.tail(5).mean():.2f}\n"
        if len(df) >= 10:
            result += f"10日均线: {close_series.tail(10).mean():.2f}\n"
        if len(df) >= 20:
            result += f"20日均线: {close_series.tail(20).mean():.2f}\n"
        return result
    except Exception as e:
        return f"akshare 日线行情获取失败: {str(e)}"


# ============================================================
# 新闻数据
# ============================================================

def get_eastmoney_news(ts_code: str, limit: int = 15) -> str:
    """
    获取东方财富个股新闻
    参数: ts_code — 股票代码（如 "000001.SZ"），自动转为纯数字
          limit — 返回条数，默认 15
    返回: 新闻标题、发布时间、来源、链接
    """
    symbol = _ts_code_to_symbol(ts_code)
    try:
        ak = _get_ak()
        df = ak.stock_news_em(symbol=symbol)
        if df is None or df.empty:
            return f"东方财富未返回 {ts_code} 的个股新闻"

        df = df.head(limit)
        result = f"【东方财富个股新闻】（{ts_code}，{len(df)}条）\n\n"
        for i, (_, row) in enumerate(df.iterrows(), 1):
            title = row.get("新闻标题", row.get("title", ""))
            time = row.get("发布时间", row.get("pub_time", ""))
            source = row.get("文章来源", row.get("source", ""))
            url = row.get("新闻链接", row.get("url", ""))
            result += f"{i}. [{time}] {title}"
            if source:
                result += f" | 来源: {source}"
            result += "\n"
        return result
    except Exception as e:
        return f"东方财富新闻获取失败: {str(e)}"


def get_cls_global_news(limit: int = 20) -> str:
    """
    获取财联社全球财经快讯
    参数: limit — 返回条数，默认 20
    返回: 新闻标题、内容摘要、发布时间
    """
    try:
        ak = _get_ak()
        df = ak.stock_info_global_cls(symbol="全球")
        if df is None or df.empty:
            return "财联社全球财经快讯未返回数据"

        df = df.head(limit)
        result = f"【财联社全球财经快讯】（{len(df)}条）\n\n"
        for i, (_, row) in enumerate(df.iterrows(), 1):
            title = row.get("标题", row.get("title", ""))
            content = row.get("内容", row.get("content", ""))
            time = row.get("发布时间", row.get("pub_time", ""))
            # 用标题或内容前100字
            text = title if title else (content[:100] + "..." if len(str(content)) > 100 else content)
            result += f"{i}. [{time}] {text}\n"
        return result
    except Exception as e:
        return f"财联社全球财经快讯获取失败: {str(e)}"


def get_combined_news(ts_code: str, limit: int = 10) -> str:
    """
    综合新闻获取：个股新闻 + 全球财经快讯，合并输出
    参数: ts_code — 股票代码
          limit — 各类新闻的单类条数上限
    返回: 合并新闻摘要
    """
    parts = []

    # 1. 个股新闻
    stock_news = get_eastmoney_news(ts_code, limit=limit)
    if "获取失败" not in stock_news and "未返回" not in stock_news:
        parts.append(stock_news)
    else:
        parts.append(f"### 个股新闻\n{stock_news}")

    # 2. 全球财经快讯
    global_news = get_cls_global_news(limit=limit)
    if "获取失败" not in global_news and "未返回" not in global_news:
        parts.append(global_news)

    if not parts:
        return f"所有新闻数据源均获取失败，请检查网络连接。建议使用 LLM 知识库兜底 [来源: LLM 知识库]"

    return "\n\n".join(parts)


# ============================================================
# 财务/估值备选数据（Tushare 限流时使用）
# ============================================================

def get_stock_financial_summary(ts_code: str) -> str:
    """
    获取个股财务摘要（akshare，作为 Tushare 限流备选）
    包含核心财务指标：ROE、净利润、营收、资产负债率、毛利率等
    参数: ts_code — 股票代码
    返回: 核心财务指标摘要
    """
    symbol = _ts_code_to_symbol(ts_code)
    try:
        ak = _get_ak()
        # 主力接口：同花顺财务摘要
        df = ak.stock_financial_abstract_ths(symbol=symbol, indicator="按报告期")
        if df is not None and not df.empty:
            latest = df.iloc[-1]  # 最新一期
            result = f"【akshare 财务摘要】（{ts_code}，{latest.get('报告期', 'N/A')}）\n"
            result += f"净利润: {latest.get('净利润', 'N/A')}\n"
            result += f"净利润同比增速: {latest.get('净利润同比增长率', 'N/A')}\n"
            result += f"营业收入: {latest.get('营业收入', 'N/A')}\n"
            result += f"营业收入同比增速: {latest.get('营业收入同比增长率', 'N/A')}\n"
            result += f"基本每股收益: {latest.get('基本每股收益', 'N/A')}\n"
            result += f"每股净资产: {latest.get('每股净资产', 'N/A')}\n"
            result += f"净资产收益率: {latest.get('净资产收益率', 'N/A')}\n"
            result += f"销售净利率: {latest.get('销售净利率', 'N/A')}\n"
            result += f"销售毛利率: {latest.get('营业利润率', 'N/A')}\n"
            result += f"资产负债率: {latest.get('资产负债率', 'N/A')}\n"
            result += f"流动比率: {latest.get('流动比率', 'N/A')}\n"
            result += f"速动比率: {latest.get('速动比率', 'N/A')}\n"
            result += f"权益乘数: {latest.get('权益乘数', 'N/A')}\n"
            return result
        return f"akshare 未返回 {ts_code} 的财务摘要数据"
    except Exception as e:
        return f"akshare 财务摘要获取失败: {str(e)}"


def get_stock_valuation_snapshot(ts_code: str) -> str:
    """
    获取个股估值相关指标（akshare，作为 Tushare 限流备选）
    通过财务分析指标接口获取每股净资产、ROE 等估值相关数据
    参数: ts_code — 股票代码
    返回: 估值相关指标快照
    """
    symbol = _ts_code_to_symbol(ts_code)
    try:
        ak = _get_ak()
        # 使用财务分析指标接口（含每股净资产、ROE等估值参考指标）
        df = ak.stock_financial_analysis_indicator(symbol=symbol, start_year="2023")
        if df is not None and not df.empty:
            latest = df.iloc[-1]  # 最新一期
            result = f"【akshare 估值参考】（{ts_code}，{latest.get('日期', 'N/A')}）\n"
            result += f"摊薄每股收益: {latest.get('摊薄每股收益(元)', 'N/A')} 元\n"
            result += f"每股净资产(调整后): {latest.get('每股净资产_调整后(元)', 'N/A')} 元\n"
            result += f"每股净资产(调整前): {latest.get('每股净资产_调整前(元)', 'N/A')} 元\n"
            result += f"每股经营现金流: {latest.get('每股经营现金流量(元)', 'N/A')} 元\n"
            result += f"净资产收益率: {latest.get('净资产收益率(%)', 'N/A')}%\n"
            result += f"销售净利率: {latest.get('销售净利率(%)', 'N/A')}%\n"
            result += f"资产负债率: {latest.get('资产负债率(%)', 'N/A')}%\n"
            result += f"流动比率: {latest.get('流动比率', 'N/A')}\n"
            result += f"速动比率: {latest.get('速动比率', 'N/A')}\n"
            result += f"权益乘数: {latest.get('权益乘数(%)', 'N/A')}\n"
            result += f"\n[注: PE/PB/PS 实时估值指标请优先使用 Tushare Pro，本接口提供净资产和盈利能力参考]"
            return result
        return f"akshare 未返回 {ts_code} 的财务分析指标"
    except Exception as e:
        return f"akshare 估值快照获取失败: {str(e)}"
