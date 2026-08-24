# -*- coding: utf-8 -*-
"""
生长曲线分析器
- 输入: 时间点 + OD600 + CFU/mL (Excel/CSV 或内嵌数据)
- 拟合: Linear / Quadratic / Exponential / Power / Gompertz / Logistic
- 输出: 拟合参数表 + 生长曲线图 (OD 与 logCFU 双面板)
整合自 OneDrive 共享文件夹 growth_curve 脚本。
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..common.fitting import fit_curve, model_dict
from ..common.io_utils import load_table, save_figure, save_csv, ensure_output_dir


class GrowthCurveAnalyzer:
    def __init__(self, time_col="time_min", od_col="od600", cfu_col="cfu_ml"):
        self.time_col = time_col
        self.od_col = od_col
        self.cfu_col = cfu_col

    def load(self, path, sheet=None):
        df = load_table(path, sheet=sheet)
        for col in (self.time_col, self.od_col, self.cfu_col):
            if col not in df.columns:
                raise ValueError(f"缺少列: {col} (可用: {list(df.columns)})")
        self.data = df[[self.time_col, self.od_col, self.cfu_col]].dropna().copy()
        self.data[self.time_col] = self.data[self.time_col].astype(float)
        self.data[self.od_col] = self.data[self.od_col].astype(float)
        self.data[self.cfu_col] = self.data[self.cfu_col].astype(float)
        return self

    def load_from_lists(self, time_min, od600, cfu_ml):
        """直接传入列表 (用于内嵌数据)"""
        self.data = pd.DataFrame({
            self.time_col: time_min,
            self.od_col: od600,
            self.cfu_col: cfu_ml,
        })
        return self

    def fit_all(self, models=("Gompertz", "Logistic", "Quadratic")):
        """对所有模型拟合 OD 曲线, 返回参数表"""
        t = self.data[self.time_col].values
        od = self.data[self.od_col].values
        rows = []
        for name in models:
            params, pcov, r2 = fit_curve(t, od, model_name=name)
            if params is None:
                continue
            rows.append({
                "model": name,
                "r_squared": r2,
                "params": ", ".join(f"{v:.4g}" for v in params),
            })
        return pd.DataFrame(rows).sort_values("r_squared", ascending=False)

    def plot(self, output_dir="output"):
        """绘制 OD 与 logCFU 双面板图"""
        t = self.data[self.time_col].values
        od = self.data[self.od_col].values
        cfu = self.data[self.cfu_col].values
        log_cfu = np.log10(cfu)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        ax1.plot(t, od, "o-", color="#1f77b4", lw=2, label="OD600")
        ax1.set_xlabel("Time (min)", fontsize=12)
        ax1.set_ylabel("OD600", fontsize=12)
        ax1.set_title("Growth Curve (OD600)", fontsize=13)
        ax1.grid(alpha=0.3)

        ax2.plot(t, log_cfu, "s-", color="#d62728", lw=2, label="log10 CFU/mL")
        ax2.set_xlabel("Time (min)", fontsize=12)
        ax2.set_ylabel("log10 CFU/mL", fontsize=12)
        ax2.set_title("Growth Curve (CFU)", fontsize=13)
        ax2.grid(alpha=0.3)

        for ax in (ax1, ax2):
            ax.legend(frameon=False)
            ax.tick_params(direction="in")

        plt.tight_layout()
        path = save_figure(fig, f"{output_dir}/growth_curve.png")
        plt.close(fig)
        return path

    def report(self, output_dir="output"):
        """生成完整报告: 拟合参数 + 图"""
        ensure_output_dir(output_dir)
        fit_df = self.fit_all()
        fig_path = self.plot(output_dir)
        fit_csv = save_csv(fit_df, f"{output_dir}/growth_fit_params.csv")
        return {"fit_params": fit_df, "figure": fig_path, "csv": fit_csv}


def run(data=None, path=None, output_dir="output", sheet=None):
    """一键运行生长曲线分析"""
    analyzer = GrowthCurveAnalyzer()
    if path:
        analyzer.load(path, sheet=sheet)
    else:
        raise ValueError("需要提供 path (Excel/CSV)")
    return analyzer.report(output_dir)
