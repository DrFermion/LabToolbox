# -*- coding: utf-8 -*-
"""文件 IO 工具"""
import os

import numpy as np
import pandas as pd


def load_table(path, sheet=None):
    """加载 Excel/CSV 表格为 DataFrame。支持中文/Unicode 路径。"""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"文件不存在: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        df = pd.read_excel(path, sheet_name=sheet)
        # pd.read_excel 可能返回 dict (多 sheet); 取第一个
        if isinstance(df, dict):
            sheet = sheet or next(iter(df))
            df = df[sheet]
        return df
    elif ext == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    else:
        raise ValueError(f"不支持的文件格式: {ext}")


def ensure_output_dir(path):
    """确保输出目录存在。"""
    os.makedirs(path, exist_ok=True)
    return path


def save_figure(fig, path, dpi=200):
    """保存 matplotlib 图, 自动建目录。"""
    ensure_output_dir(os.path.dirname(os.path.abspath(path)))
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    return path


def save_csv(df, path):
    """保存 DataFrame 为 UTF-8 BOM CSV (Excel 兼容)。"""
    ensure_output_dir(os.path.dirname(os.path.abspath(path)))
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path
