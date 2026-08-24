# -*- coding: utf-8 -*-
"""
LIVE/DEAD 荧光统计模块
- 输入: Excel (各样品 × 重复 × 时间点的 live/dead 计数)
- 输出: 存活率 (%), 汇总统计, 双因素 ANOVA (log10 转换可选), 柱状图
整合自共享文件夹 Live_Dead Bacteria Test 分析流程。
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..common.io_utils import load_table, save_figure, save_csv, ensure_output_dir
from ..common.stats import summarize, anova_two_way


class LiveDeadAnalyzer:
    def __init__(self, live_col="live", dead_col="dead", time_col="time",
                 group_col="group", replicate_col="repeat"):
        self.live_col = live_col
        self.dead_col = dead_col
        self.time_col = time_col
        self.group_col = group_col
        self.replicate_col = replicate_col

    def load(self, path, sheet=None):
        df = load_table(path, sheet=sheet)
        for col in (self.live_col, self.dead_col):
            if col not in df.columns:
                raise ValueError(f"缺少列: {col} (可用: {list(df.columns)})")
        self.data = df.dropna(subset=[self.live_col, self.dead_col]).copy()
        self.data[self.live_col] = self.data[self.live_col].astype(float)
        self.data[self.dead_col] = self.data[self.dead_col].astype(float)

        # ==== 计数机制校验 (2026-08-24 增强) ====
        # 1. 负值检查: 细胞计数不可能为负
        neg_live = (self.data[self.live_col] < 0).sum()
        neg_dead = (self.data[self.dead_col] < 0).sum()
        if neg_live > 0 or neg_dead > 0:
            raise ValueError(
                f"发现负计数: live 负值 {neg_live} 条, dead 负值 {neg_dead} 条。"
                "细胞计数不应为负数, 请检查数据。"
            )
        # 2. 非整数警告: 细胞计数应为整数 (允许极小浮点误差)
        nonint_live = (~np.isclose(self.data[self.live_col], np.round(self.data[self.live_col]))).sum()
        nonint_dead = (~np.isclose(self.data[self.dead_col], np.round(self.data[self.dead_col]))).sum()
        if nonint_live > 0 or nonint_dead > 0:
            import warnings
            warnings.warn(
                f"发现非整数计数: live {nonint_live} 条, dead {nonint_dead} 条。"
                "细胞计数应为整数, 请确认是否为计数数据或归一化数据。"
            )
        # 3. 存活率合理性: 0/0 保持 NaN, 全 0 行应被标记而非算作 0%
        total = self.data[self.live_col] + self.data[self.dead_col]
        self.data["total"] = total
        self.data["dead_rate"] = self.data[self.dead_col] / total.replace(0, np.nan)
        self.data["viability_pct"] = self.data[self.live_col] / total.replace(0, np.nan) * 100
        # 全 0 行: 计数无效, 标记并排除统计
        zero_rows = (self.data[self.live_col] == 0) & (self.data[self.dead_col] == 0)
        if zero_rows.sum() > 0:
            import warnings
            warnings.warn(
                f"发现 {zero_rows.sum()} 行 live=dead=0 (无细胞计数), 这些行不参与统计。"
            )
            self.data = self.data[~zero_rows].copy()
        return self

    def summary(self, group_col=None, time_col=None, log10=False):
        """按组+时间汇总存活率 (合并计数法 pooled: Σlive/Σtotal×100)"""
        g = group_col or self.group_col
        t = time_col or self.time_col
        data = self.data.copy()
        if g in data.columns and t in data.columns:
            data["_group_time"] = data[g].astype(str) + "_" + data[t].astype(str)
            summ = data.groupby("_group_time").apply(
                lambda d: pd.Series({
                    "viability_pct": d[self.live_col].sum() / d["total"].sum() * 100,
                    "n": len(d),
                    "live_sum": d[self.live_col].sum(),
                    "dead_sum": d[self.dead_col].sum(),
                }), include_groups=False)
            summ = summ.reset_index()
            summ["group"] = summ["_group_time"].str.rsplit("_", n=1).str[0]
            summ["time"] = summ["_group_time"].str.rsplit("_", n=1).str[1]
            return summ.drop(columns=["_group_time"])
        elif g in data.columns:
            return data.groupby(g).apply(
                lambda d: pd.Series({
                    "viability_pct": d[self.live_col].sum() / d["total"].sum() * 100,
                    "n": len(d),
                }), include_groups=False).reset_index()
        else:
            return pd.DataFrame({
                "viability_pct": [data[self.live_col].sum() / data["total"].sum() * 100],
                "n": [len(data)],
            })

    def anova(self, factor1="group", factor2="time", log10=False):
        """双因素 ANOVA (存活率)"""
        return anova_two_way(self.data, "viability_pct", factor1, factor2, log10=log10)

    def plot(self, output_dir="output"):
        """柱状图: 各时间点 × 各组的存活率 (均值±SEM)"""
        ensure_output_dir(output_dir)
        data = self.data
        groups = sorted(data[self.group_col].unique()) if self.group_col in data else ["all"]
        times = sorted(data[self.time_col].unique()) if self.time_col in data else [""]

        fig, ax = plt.subplots(figsize=(max(6, len(times)*1.8), 5))
        width = 0.8 / max(len(groups), 1)
        colors = plt.cm.tab10(np.linspace(0, 1, max(len(groups), 1)))

        for gi, g in enumerate(groups):
            means, sems = [], []
            for t in times:
                mask = np.ones(len(data), dtype=bool)
                if self.group_col in data:
                    mask &= (data[self.group_col] == g)
                if self.time_col in data:
                    mask &= (data[self.time_col] == t)
                sub = data.loc[mask]
                if len(sub) == 0 or sub["total"].sum() == 0:
                    means.append(np.nan)
                    sems.append(0)
                else:
                    # 合并计数法 (pooled): Σlive/Σtotal×100
                    pct = sub[self.live_col].sum() / sub["total"].sum() * 100
                    means.append(pct)
                    # 重复间 SEM (基于每行存活率)
                    row_pct = (sub[self.live_col] / sub["total"].replace(0, np.nan) * 100).dropna()
                    sems.append(row_pct.sem() if len(row_pct) > 1 else 0)
            xpos = np.arange(len(times)) + gi * width
            ax.bar(xpos, means, width=width, yerr=sems, capsize=3,
                   label=g, color=colors[gi], alpha=0.85)

        ax.set_xticks(np.arange(len(times)) + width * (len(groups) - 1) / 2)
        ax.set_xticklabels([str(t) for t in times])
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Viability (%)", fontsize=12)
        ax.set_title("LIVE/DEAD Viability by Group & Time", fontsize=13)
        ax.legend(frameon=False)
        ax.tick_params(direction="in")
        ax.set_ylim(0, 110)
        plt.tight_layout()
        path = save_figure(fig, f"{output_dir}/livedead_viability.png")
        plt.close(fig)
        return path

    def report(self, output_dir="output"):
        ensure_output_dir(output_dir)
        fig_path = self.plot(output_dir)
        try:
            aov = self.anova()
            aov_csv = save_csv(aov["table"].reset_index(), f"{output_dir}/livedead_anova.csv")
        except Exception:
            aov, aov_csv = None, None
        summ = self.summary()
        summ_csv = save_csv(summ, f"{output_dir}/livedead_summary.csv")
        return {"figure": fig_path, "anova": aov, "anova_csv": aov_csv,
                "summary": summ, "summary_csv": summ_csv}


def run(path, sheet=None, output_dir="output", **kwargs):
    """一键 LIVE/DEAD 分析"""
    analyzer = LiveDeadAnalyzer(**kwargs)
    analyzer.load(path, sheet=sheet)
    return analyzer.report(output_dir)
