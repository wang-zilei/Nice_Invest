"""
calculator.py — 财务计算工具（Function Call）
提供标准化的财务比率计算函数，供各分析 Agent 通过 Function Call 调用。
"""


def calc_dupont(net_profit_margin: float, asset_turnover: float, equity_multiplier: float) -> dict:
    """
    杜邦分析：ROE = 净利率 × 资产周转率 × 权益乘数
    参数:
        net_profit_margin: 净利润率（小数，如 0.15 表示 15%）
        asset_turnover: 总资产周转率
        equity_multiplier: 权益乘数
    返回: ROE 及三因素拆解
    """
    roe = net_profit_margin * asset_turnover * equity_multiplier
    return {
        "roe": round(roe * 100, 2),
        "net_profit_margin": round(net_profit_margin * 100, 2),
        "asset_turnover": round(asset_turnover, 2),
        "equity_multiplier": round(equity_multiplier, 2),
        "formula": "ROE = 净利率 × 资产周转率 × 权益乘数",
        "interpretation": _interpret_dupont(net_profit_margin, asset_turnover, equity_multiplier)
    }


def _interpret_dupont(npm: float, at: float, em: float) -> str:
    """杜邦分析结果解读"""
    factors = []
    if npm >= 0.2:
        factors.append("盈利能力较强（高净利率驱动）")
    elif npm < 0.05:
        factors.append("盈利能力偏弱（净利率较低）")
    if at > 1.0:
        factors.append("资产运营效率高")
    elif at < 0.5:
        factors.append("资产周转较慢")
    if em > 3.0:
        factors.append("财务杠杆较高（需关注偿债风险）")
    elif em < 1.5:
        factors.append("财务杠杆较低（财务结构稳健）")
    return "；".join(factors) if factors else "各项指标处于中等水平"


def calc_pe_growth(pe: float, profit_growth_rate: float) -> dict:
    """
    PEG 计算：PEG = PE / 净利润增速
    参数:
        pe: 市盈率
        profit_growth_rate: 净利润增长率（百分比，如 20 表示 20%）
    返回: PEG 值及估值判断
    """
    if profit_growth_rate <= 0:
        return {
            "peg": None,
            "pe": pe,
            "profit_growth_rate": profit_growth_rate,
            "interpretation": "净利润负增长，PEG 指标不适用，建议结合 PB/PS 等其他估值指标"
        }

    peg = pe / profit_growth_rate
    if peg < 1:
        judgment = "低估（PEG < 1，成长性未被充分定价）"
    elif peg < 1.5:
        judgment = "合理（PEG 在 1~1.5 区间，估值与成长性匹配）"
    elif peg < 2:
        judgment = "偏高（PEG 在 1.5~2 区间，存在一定溢价）"
    else:
        judgment = "高估（PEG > 2，成长性难以支撑当前估值）"

    return {
        "peg": round(peg, 2),
        "pe": pe,
        "profit_growth_rate": profit_growth_rate,
        "interpretation": judgment
    }


def calc_financial_ratio(current_assets: float, current_liabilities: float,
                         quick_assets: float = None, total_debt: float = None,
                         total_assets: float = None) -> dict:
    """
    通用财务比率计算：流动比率、速动比率、资产负债率
    参数:
        current_assets: 流动资产
        current_liabilities: 流动负债
        quick_assets: 速动资产（可选，= 流动资产 - 存货）
        total_debt: 总负债（可选）
        total_assets: 总资产（可选）
    返回: 多项财务比率
    """
    result = {}

    # 流动比率
    if current_liabilities and current_liabilities > 0:
        result["current_ratio"] = round(current_assets / current_liabilities, 2)
        result["current_ratio_note"] = "健康" if result["current_ratio"] >= 2 else "偏低" if result["current_ratio"] < 1 else "正常"

    # 速动比率
    if quick_assets and current_liabilities and current_liabilities > 0:
        result["quick_ratio"] = round(quick_assets / current_liabilities, 2)
        result["quick_ratio_note"] = "健康" if result["quick_ratio"] >= 1 else "偏低"

    # 资产负债率
    if total_debt and total_assets and total_assets > 0:
        result["debt_to_asset"] = round(total_debt / total_assets * 100, 2)
        result["debt_to_asset_note"] = "偏高" if result["debt_to_asset"] > 70 else "正常" if result["debt_to_asset"] > 40 else "偏低"

    if not result:
        return {"error": "参数不足，至少需要提供 (current_assets + current_liabilities)"}

    return result


def calc_cagr(start_value: float, end_value: float, years: int) -> dict:
    """
    复合年增长率计算：CAGR = (终值/初值)^(1/年数) - 1
    参数:
        start_value: 起始值
        end_value: 终值
        years: 年数
    返回: CAGR 及解读
    """
    if start_value <= 0:
        return {"error": "起始值必须大于 0"}

    cagr = (end_value / start_value) ** (1 / years) - 1
    if cagr >= 0.2:
        interpretation = "高增长"
    elif cagr >= 0.1:
        interpretation = "中速增长"
    elif cagr >= 0:
        interpretation = "低速增长"
    else:
        interpretation = "负增长（业务收缩）"

    return {
        "cagr": round(cagr * 100, 2),
        "start_value": start_value,
        "end_value": end_value,
        "years": years,
        "interpretation": interpretation
    }
