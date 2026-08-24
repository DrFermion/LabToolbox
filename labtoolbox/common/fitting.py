# -*- coding: utf-8 -*-
"""拟合工具: 常用生长/衰减模型"""
import numpy as np
from scipy.optimize import curve_fit


def linear_func(x, a, b):
    return a * x + b


def quadratic_func(x, a, b, c):
    return a * x**2 + b * x + c


def exponential_func(x, a, b, c):
    return a * np.exp(b * x) + c


def power_func(x, a, b):
    return a * x**b


def gompertz_func(x, A, mu, lag):
    """Gompertz 生长模型 (修正版)"""
    return A * np.exp(-np.exp(mu * np.exp(1) / A * (lag - x) + 1))


def logistic_func(x, A, k, x0):
    """Logistic 生长模型"""
    return A / (1 + np.exp(-k * (x - x0)))


model_dict = {
    "Linear": linear_func,
    "Quadratic": quadratic_func,
    "Exponential": exponential_func,
    "Power": power_func,
    "Gompertz": gompertz_func,
    "Logistic": logistic_func,
}


def fit_curve(x, y, model_name="Gompertz", p0=None):
    """拟合曲线, 返回 (params, pcov, r_squared)"""
    if model_name not in model_dict:
        raise ValueError(f"未知模型: {model_name}, 可选: {list(model_dict)}")
    func = model_dict[model_name]
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    # 自动初始值
    if p0 is None:
        if model_name == "Gompertz":
            p0 = [y.max() * 1.1, 0.5, x[np.argmax(y)]]
        elif model_name == "Logistic":
            p0 = [y.max() * 1.1, 0.5, x[len(x) // 2]]
        else:
            p0 = None
    try:
        params, pcov = curve_fit(func, x, y, p0=p0, maxfev=20000)
    except Exception:
        return None, None, None
    # R²
    y_pred = func(x, *params)
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    return params, pcov, r2
