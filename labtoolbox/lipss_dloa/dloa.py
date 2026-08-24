# -*- coding: utf-8 -*-
"""
LIPSS/DLOA 分析器 (spot-based DLOA, 验证版)
- 输入: SEM 灰度图 (bmp/png/tif)
- 输出: 周期 (spacing_nm), FFT 角 (theta_fft_deg), 实空间条纹角 (lipss_angle_deg), FWHM
整合自 sem-fft-analysis 技能的验证脚本 (6 samples, spacing 449-482 nm)。
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..common.io_utils import save_figure, save_csv, ensure_output_dir


class DLOAAnalyzer:
    def __init__(self, pixel_size_um=1.0 / 32.0, exclude_radius=40, n_top=20, min_radius=45):
        """pixel_size_um: 每个像素对应的微米数 (31.25 nm/px = 1/32)"""
        self.pixel_size_um = pixel_size_um
        self.freq_max = 1.0 / (2 * pixel_size_um)
        self.exclude_radius = exclude_radius
        self.n_top = n_top
        self.min_radius = min_radius

    def _read_gray(self, path):
        """读取灰度图 (支持中文路径)"""
        import cv2
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise ValueError(f"无法读取图像: {path}")
        return img

    def _detect_black_border(self, img, threshold=30):
        """裁掉底部黑色边框 (SEM 比例尺区域)"""
        h, w = img.shape
        row_means = img.mean(axis=1)
        bs = h
        for i in range(h - 1, 0, -1):
            if row_means[i] < threshold:
                bs = i
            else:
                break
        return img[:bs, :] if bs < h else img

    def _log_power(self, img):
        h, w = img.shape
        win = np.outer(np.hanning(h), np.hanning(w))
        fft = np.fft.fftshift(np.fft.fft2(img * win))
        from scipy.ndimage import gaussian_filter
        return np.log1p(gaussian_filter(np.abs(fft) ** 2, sigma=1.5))

    def _find_spots(self, lp):
        """找衍射斑局部极大值 (top-N, 排除中心盘)"""
        h, w = lp.shape
        cy, cx = h // 2, w // 2
        maxima = []
        for i in range(2, h - 2):
            for j in range(2, w - 2):
                if (i - cy) ** 2 + (j - cx) ** 2 < self.exclude_radius ** 2:
                    continue
                v = lp[i, j]
                if (v > lp[i-1, j-1] and v > lp[i-1, j] and v > lp[i-1, j+1] and
                    v > lp[i, j-1] and v > lp[i, j+1] and
                    v > lp[i+1, j-1] and v > lp[i+1, j] and v > lp[i+1, j+1]):
                    maxima.append((i, j, v))
        maxima.sort(key=lambda x: x[2], reverse=True)
        spots = []
        for (i, j, v) in maxima[:self.n_top]:
            dx, dy = j - cx, i - cy
            rad = np.hypot(dx, dy)
            if rad < self.min_radius:
                continue
            spots.append((np.degrees(np.arctan2(dy, dx)) % 180, rad, v))
        return spots

    def _distribution(self, spots, sigma=2.0, bins=181):
        from scipy.ndimage import gaussian_filter
        angs = np.array([s[0] for s in spots])
        wts = np.array([s[2] for s in spots])
        hist, be = np.histogram(angs, bins=bins, range=(0, 180), weights=wts)
        hist = gaussian_filter(hist, sigma=sigma)
        hist = hist - hist.min()
        mx = hist.max()
        if mx > 0:
            hist = hist / mx
        return (be[:-1] + be[1:]) / 2, hist

    @staticmethod
    def _fwhm(x, y):
        pk = int(np.argmax(y))
        idx = np.where(y >= 0.5 * y[pk])[0]
        return x[idx[-1]] - x[idx[0]] if len(idx) else np.nan

    def analyze_image(self, path, output_dir=None):
        """分析单张 SEM 图, 返回结果 dict"""
        img = self._read_gray(path)
        img = self._detect_black_border(img)
        if img.size == 0 or min(img.shape) < 200:
            return None
        h, w = img.shape
        lp = self._log_power(img.astype(np.float32))
        spots = self._find_spots(lp)
        if len(spots) < 2:
            return None

        xa, dist = self._distribution(spots)
        theta_fft = xa[int(np.argmax(dist))]
        lipss_angle = (theta_fft + 90.0) % 180.0
        fwhm = self._fwhm(xa, dist)

        ang, rad, v = max(spots, key=lambda s: s[2])
        k = rad * (self.freq_max / (w / 2))
        spacing = 1000.0 / k if k > 0 else np.nan

        name = os.path.splitext(os.path.basename(path))[0]
        result = {
            "file": name,
            "theta_fft_deg": theta_fft,
            "lipss_angle_deg": lipss_angle,
            "fwhm_2dtheta_deg": fwhm,
            "spacing_nm": spacing,
        }

        if output_dir:
            fig, ax = plt.subplots(figsize=(7, 5))
            ax.plot(xa, dist, color="#FF00FF", lw=2)
            ax.axvline(theta_fft, color="red", ls="--", lw=1.2,
                       label=f"theta_fft = {theta_fft:.1f} deg")
            ax.set_xlim(-5, 185)
            ax.set_ylim(-0.05, 1.2)
            ax.set_xlabel("Orientation in Degree", fontsize=13, fontweight="bold")
            ax.set_ylabel("Distribution of Orientation (a.u.)", fontsize=13, fontweight="bold")
            ax.legend(loc="upper right", frameon=False)
            plt.tight_layout()
            result["figure"] = save_figure(fig, f"{output_dir}/dloa_{name}.png")
            plt.close(fig)

        return result

    def analyze_folder(self, folder, output_dir="output"):
        """分析文件夹内所有 SEM 图"""
        ensure_output_dir(output_dir)
        imgs = [f for f in sorted(os.listdir(folder))
                if f.lower().endswith((".bmp", ".png", ".jpg", ".jpeg", ".tif", ".tiff"))
                and not any(x in f.lower() for x in ["_fft", "_annotated", "_spectrum", "result_"])]
        results = []
        for f in imgs:
            r = self.analyze_image(os.path.join(folder, f), output_dir=output_dir)
            if r:
                results.append(r)
        csv_path = save_csv(
            __import__("pandas").DataFrame(results),
            f"{output_dir}/LIPSS_orientation_angles.csv",
        )
        return {"results": results, "csv": csv_path}


def run(folder, output_dir="output", pixel_size_um=1.0 / 32.0):
    """一键运行 LIPSS/DLOA 分析"""
    analyzer = DLOAAnalyzer(pixel_size_um=pixel_size_um)
    return analyzer.analyze_folder(folder, output_dir)
