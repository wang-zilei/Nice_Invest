"""
tushare_api.py — Tushare Pro 数据工具封装（MCP 风格）
提供标准化的金融数据查询接口，供各分析 Agent 通过 Function Call 调用。
"""
import os
import time
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
from config import TUSHARE_TOKEN

# 初始化 Tushare Pro
_pro = None
_last_pro_time = 0

if TUSHARE_TOKEN:
    ts.set_token(TUSHARE_TOKEN)
    _pro = ts.pro_api()
    _last_pro_time = time.time()


def _get_pro():
    """获取 Tushare Pro 实例，支持动态 token 设置"""
    global _pro, _last_pro_time
    token = os.environ.get("TUSHARE_TOKEN", TUSHARE_TOKEN)
    if not token:
        return None
    now = time.time()
    # 每分钟重新创建一次，避免频率限制缓存问题
    if _pro is None or (now - _last_pro_time) > 60:
        ts.set_token(token)
        _pro = ts.pro_api()
        _last_pro_time = now
    return _pro


def _is_rate_limit(err_msg: str) -> bool:
    """判断错误是否为 Tushare 限流"""
    msg = err_msg.lower()
    return any(k in msg for k in ["limit", "freq", "frequency", "次", "限流", "rate", "quota"])


def _check_tushare() -> bool:
    """检查 Tushare 是否可用"""
    token = os.environ.get("TUSHARE_TOKEN", TUSHARE_TOKEN)
    if not token:
        raise RuntimeError("TUSHARE_TOKEN 未配置，请编辑 config.py 填入 Token 或在前端配置中设置")
    return True


def _find_recent_trade_date(pro, max_lookback: int = 7) -> str:
    """回溯查找最近的交易日日期（解决周末/节假日 daily_basic 返回空的问题）"""
    for i in range(max_lookback):
        check_date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        try:
            df = pro.trade_cal(exchange="SSE", is_open="1",
                               start_date=check_date, end_date=check_date)
            if df is not None and not df.empty:
                return check_date
        except Exception:
            continue
    # 兜底：直接用前一天
    return (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")


def get_stock_basic(ts_code: str) -> str:
    """
    获取股票基本信息
    参数: ts_code — 股票代码，如 "600519.SH"
    返回: 名称、行业、市值、上市日期等
    """
    _check_tushare()
    pro = _get_pro()
    df = pro.stock_basic(ts_code=ts_code, fields='ts_code,symbol,name,area,industry,market,list_date')
    if df is None or df.empty:
        return f"未找到股票 {ts_code} 的基本信息"

    # 获取最新市值（回溯查找最近交易日，解决非交易日返回空数据的问题）
    trade_date = _find_recent_trade_date(pro)
    try:
        df_daily = pro.daily_basic(
            ts_code=ts_code,
            trade_date=trade_date,
            fields='ts_code,trade_date,total_mv,circ_mv,pe_ttm,pb,ps_ttm,dv_ratio'
        )
    except Exception as e:
        err_msg = str(e).lower()
        if "limit" in err_msg or "freq" in err_msg or "frequency" in err_msg or "次" in err_msg or "限流" in err_msg:
            return result + "\n\n【估值指标】Tushare Pro 调用频次超限（限流），请使用 akshare 备选数据源获取 PE/PB/PS 等估值指标。"
        return result + f"\n\n【估值指标】Tushare 查询异常: {str(e)[:80]}"


    result = f"【股票基本信息】\n"
    for _, row in df.iterrows():
        result += f"代码: {row['ts_code']}\n"
        result += f"名称: {row['name']}\n"
        result += f"地区: {row.get('area', 'N/A')}\n"
        result += f"行业: {row.get('industry', 'N/A')}\n"
        result += f"市场: {row.get('market', 'N/A')}\n"
        result += f"上市日期: {row.get('list_date', 'N/A')}\n"

    if df_daily is not None and not df_daily.empty:
        latest = df_daily.iloc[0]
        result += f"\n【最新估值指标】（{latest.get('trade_date', 'N/A')}）\n"
        result += f"总市值: {latest.get('total_mv', 'N/A')} 万元\n"
        result += f"流通市值: {latest.get('circ_mv', 'N/A')} 万元\n"
        result += f"PE(TTM): {latest.get('pe_ttm', 'N/A')}\n"
        result += f"PB: {latest.get('pb', 'N/A')}\n"
        result += f"PS(TTM): {latest.get('ps_ttm', 'N/A')}\n"
        result += f"股息率: {latest.get('dv_ratio', 'N/A')}%\n"

    return result


def get_financial_report(ts_code: str, period: str = "") -> str:
    """
    获取财务报表核心指标
    参数:
        ts_code — 股票代码
        period — 报告期，如 "20240331"，默认最近一期
    返回: ROE、净利润、营收、资产负债率等
    """
    _check_tushare()
    pro = _get_pro()

    try:
        # 利润表
        df_income = pro.income(
            ts_code=ts_code,
            period=period if period else None,
            fields='ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,revenue,operate_profit,total_profit,n_income,int_exp'
        )
    except Exception as e:
        if _is_rate_limit(str(e)):
            return f"【财务报表核心指标】Tushare Pro 调用频次超限（限流），请使用 akshare 备选数据源获取财务数据。"
        df_income = None

    try:
        # 资产负债表
        df_balance = pro.balancesheet(
            ts_code=ts_code,
            period=period if period else None,
            fields='ts_code,ann_date,f_ann_date,end_date,report_type,comp_type,total_share,cap_rese,undistr_porfit,total_assets,total_liab'
        )
    except Exception:
        df_balance = None

    try:
        # 财务指标
        df_indicator = pro.fina_indicator(
            ts_code=ts_code,
            period=period if period else None,
            fields='ts_code,ann_date,end_date,eps,dt_eps,roe,roa,profit_to_gr,revenue_to_gr,debt_to_assets,assets_to_eq,current_ratio'
        )
    except Exception:
        df_indicator = None

    result = f"【财务报表核心指标】（股票: {ts_code}）\n\n"

    if df_indicator is not None and not df_indicator.empty:
        result += "【财务指标】\n"
        for _, row in df_indicator.head(4).iterrows():
            result += f"报告期: {row.get('end_date', 'N/A')}\n"
            result += f"  EPS: {row.get('eps', 'N/A')}\n"
            result += f"  ROE: {row.get('roe', 'N/A')}%\n"
            result += f"  ROA: {row.get('roa', 'N/A')}%\n"
            result += f"  营收增速: {row.get('revenue_to_gr', 'N/A')}%\n"
            result += f"  净利润增速: {row.get('profit_to_gr', 'N/A')}%\n"
            result += f"  资产负债率: {row.get('debt_to_assets', 'N/A')}%\n"
            result += f"  流动比率: {row.get('current_ratio', 'N/A')}\n"
            result += "\n"

    if df_income is not None and not df_income.empty:
        result += "【利润表摘要】\n"
        for _, row in df_income.head(4).iterrows():
            result += f"报告期: {row.get('end_date', 'N/A')}\n"
            result += f"  营业收入: {row.get('revenue', 'N/A')} 元\n"
            result += f"  营业利润: {row.get('operate_profit', 'N/A')} 元\n"
            result += f"  净利润: {row.get('n_income', 'N/A')} 元\n"
            result += "\n"

    if result == f"【财务报表核心指标】（股票: {ts_code}）\n\n":
        result += "未查询到相关财务数据，请检查股票代码或报告期。"

    return result


def get_daily_quote(ts_code: str, start_date: str = "", end_date: str = "", limit: int = 60) -> str:
    """
    获取日线行情数据
    参数:
        ts_code — 股票代码
        start_date — 开始日期，如 "20240101"
        end_date — 结束日期，如 "20241231"
        limit — 返回条数，默认60（约3个月交易日）
    返回: OHLCV 数据（开高低收量）
    """
    _check_tushare()
    pro = _get_pro()

    # 默认取最近 N 个交易日
    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    if not start_date:
        start = datetime.now() - timedelta(days=limit * 2)
        start_date = start.strftime("%Y%m%d")

    try:
        df = pro.daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields='ts_code,trade_date,open,high,low,close,vol,amount,pct_chg'
        )
    except Exception as e:
        if _is_rate_limit(str(e)):
            return f"【日线行情】Tushare Pro 调用频次超限（限流），请使用 akshare 或其他数据源获取行情数据。"
        return f"【日线行情】Tushare 查询异常: {str(e)[:80]}"

    if df is None or df.empty:
        return f"未找到股票 {ts_code} 在 {start_date}~{end_date} 的行情数据"

    df = df.head(limit)

    result = f"【日线行情】（股票: {ts_code}，{len(df)}个交易日）\n\n"
    result += f"统计区间: {df['trade_date'].iloc[-1]} ~ {df['trade_date'].iloc[0]}\n"
    result += f"最高价: {df['high'].max():.2f}\n"
    result += f"最低价: {df['low'].min():.2f}\n"
    result += f"最新收盘: {df.iloc[0]['close']:.2f}\n"
    result += f"区间涨跌幅: {df.iloc[0]['pct_chg']:.2f}%\n"
    result += f"日均成交量: {df['vol'].mean():.0f} 手\n"
    result += f"日均成交额: {df['amount'].mean():.0f} 元\n"

    return result


def get_news(ts_code: str, start_date: str = "", limit: int = 10) -> str:
    """
    获取新闻资讯
    参数:
        ts_code — 股票代码
        start_date — 开始日期
        limit — 返回条数，默认10
    返回: 新闻标题、发布时间、内容摘要
    """
    _check_tushare()
    pro = _get_pro()

    if not start_date:
        start = datetime.now() - timedelta(days=30)
        start_date = start.strftime("%Y%m%d")

    # 使用新闻数据接口（需要 Tushare 积分 >= 120）
    try:
        df = pro.news(src="", start_date=start_date, fields='content,title,channels,publish_time')
        if df is not None and not df.empty:
            # 尝试匹配相关股票新闻（简单关键词匹配）
            df_stock = pro.gs_news(ts_code=ts_code, start_date=start_date,
                                   fields='title,content,publish_time')
            if df_stock is not None and not df_stock.empty:
                result = f"【相关新闻】（股票: {ts_code}，{min(limit, len(df_stock))}条）\n\n"
                for i, (_, row) in enumerate(df_stock.head(limit).iterrows()):
                    title = row.get('title', '')
                    time = row.get('publish_time', '')
                    result += f"{i+1}. [{time}] {title}\n"
                return result
    except Exception:
        pass

    return f"未查询到股票 {ts_code} 的相关新闻（可能需要更高 Tushare 积分）"


def search_stock(keyword: str) -> str:
    """
    按关键词搜索股票（模糊匹配名称）
    参数: keyword — 股票名称关键词，如 "茅台"
    返回: 匹配的股票列表
    """
    _check_tushare()
    pro = _get_pro()
    df = pro.stock_basic(
        exchange='',
        list_status='L',
        fields='ts_code,symbol,name,area,industry'
    )

    if df is None or df.empty:
        return "查询失败"

    # 模糊匹配
    matches = df[df['name'].str.contains(keyword, na=False)]
    if matches.empty:
        return f"未找到包含关键词 '{keyword}' 的A股上市公司"

    result = f"【搜索结果】（关键词: {keyword}，{len(matches)}条匹配）\n\n"
    for _, row in matches.head(10).iterrows():
        result += f"{row['ts_code']} | {row['name']} | {row.get('industry', 'N/A')}\n"

    if len(matches) > 10:
        result += f"\n... 还有 {len(matches) - 10} 条结果"

    return result
