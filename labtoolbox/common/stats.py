# -*- coding: utf-8 -*-
"""统计工具: ANOVA, 汇总"""
import numpy as np
import pandas as pd


def summarize(df, value_col, group_col=None, log10=False):
    """按分组汇总均值/标准差/SEM。可选 log10 转换。"""
    if group_col is None:
        df = df.assign(_g="all")
        group_col = "_g"
    out = []
    for g, sub in df.groupby(group_col):
        vals = sub[value_col].astype(float)
        if log10:
            vals = np.log10(vals)
        out.append({
            group_col: g,
            "n": len(vals),
            "mean": vals.mean(),
            "sd": vals.std(ddof=1) if len(vals) > 1 else np.nan,
            "sem": vals.sem() if len(vals) > 1 else np.nan,
        })
    return pd.DataFrame(out)


def anova_two_way(df, value_col, factor1, factor2, log10=False):
    """双因素 ANOVA (Type III)。返回结果字典。"""
    from statsmodels.formula.api import ols
    import statsmodels.api as sm

    data = df[[value_col, factor1, factor2]].dropna().copy()
    data[value_col] = data[value_col].astype(float)
    if log10:
        data[value_col] = np.log10(data[value_col])
    data[factor1] = data[factor1].astype(str)
    data[factor2] = data[factor2].astype(str)

    formula = f"{value_col} ~ C({factor1}) * C({factor2})"
    model = ols(formula, data=data).fit()
    aov = sm.stats.anova_lm(model, typ=3)
    return {
        "table": aov,
        "factor1_p": aov.loc[f"C({factor1})", "PR(>F)"] if f"C({factor1})" in aov.index else None,
        "factor2_p": aov.loc[f"C({factor2})", "PR(>F)"] if f"C({factor2})" in aov.index else None,
        "interaction_p": aov.loc[f"C({factor1}):C({factor2})", "PR(>F)"] if f"C({factor1}):C({factor2})" in aov.index else None,
        "model": model,
    }
