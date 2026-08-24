# -*- coding: utf-8 -*-
"""
实验室工具箱 GUI 界面 (tkinter)
- 5 个模块, 每个都有独立配置面板
- 统一入口: python -m labtoolbox.gui
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from labtoolbox.growth_curve import run as gc_run
from labtoolbox.lipss_dloa import run as dloa_run
from labtoolbox.xdlvo import run as xdlvo_run
from labtoolbox.livedead import run as ld_run
from labtoolbox.contact_angle import run as ca_run


class LabToolboxApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("实验室工具箱 LabToolbox")
        self.root.geometry("760x560")
        self.root.configure(bg="#1e1e2e")
        self.root.attributes("-topmost", False)

        # 样式
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#1e1e2e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4",
                        padding=(16, 8), font=("Microsoft YaHei UI", 10))
        style.map("TNotebook.Tab", background=[("selected", "#89b4fa")],
                  foreground=[("selected", "#11111b")])
        style.configure("TFrame", background="#1e1e2e")
        style.configure("TLabelframe", background="#181825", foreground="#cdd6f4")
        style.configure("TLabelframe.Label", background="#181825", foreground="#89b4fa",
                        font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("TLabel", background="#181825", foreground="#cdd6f4",
                        font=("Microsoft YaHei UI", 10))
        style.configure("TButton", background="#45475a", foreground="#cdd6f4",
                        font=("Microsoft YaHei UI", 10), padding=(10, 6))
        style.map("TButton", background=[("active", "#585b70")])

        # 标题
        title = tk.Label(self.root, text="🧪 实验室工具箱 LabToolbox",
                         bg="#1e1e2e", fg="#89b4fa",
                         font=("Microsoft YaHei UI", 16, "bold"), pady=10)
        title.pack(fill="x")

        # 标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self._build_growth_tab()
        self._build_dloa_tab()
        self._build_xdlvo_tab()
        self._build_livedead_tab()
        self._build_contact_tab()

        # 底部状态栏
        self.status_var = tk.StringVar(value="就绪 - 选择一个模块配置并运行")
        status = tk.Label(self.root, textvariable=self.status_var, bg="#1e1e2e",
                          fg="#a6e3a1", font=("Microsoft YaHei UI", 9), pady=6)
        status.pack(fill="x")

    # ---------- 通用组件 ----------
    def _file_row(self, parent, label, var, filetypes):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=label, width=16).pack(side="left")
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(row, text="浏览...", command=lambda: var.set(
            filedialog.askopenfilename(filetypes=filetypes)
        )).pack(side="left")
        return row

    def _folder_row(self, parent, label, var):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text=label, width=16).pack(side="left")
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(row, text="浏览...", command=lambda: var.set(
            filedialog.askdirectory()
        )).pack(side="left")
        return row

    def _output_row(self, parent, var):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="输出目录", width=16).pack(side="left")
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(row, text="浏览...", command=lambda: var.set(
            filedialog.askdirectory()
        )).pack(side="left")
        return row

    def _run_button(self, parent, text, callback):
        btn = ttk.Button(parent, text=text, command=callback)
        btn.pack(pady=10)
        return btn

    def _run_async(self, fn, *args):
        """后台线程运行, 完成后更新状态"""
        self.status_var.set("⏳ 运行中...")
        def worker():
            try:
                result = fn(*args)
                self.root.after(0, lambda: self.status_var.set("✅ 完成! 输出见输出目录"))
                if isinstance(result, dict) and "figure" in result:
                    self.root.after(0, lambda: messagebox.showinfo(
                        "完成", f"分析完成!\n图表: {result['figure']}"))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"❌ 错误: {e}"))
                self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
        threading.Thread(target=worker, daemon=True).start()

    # ---------- 生长曲线 ----------
    def _build_growth_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="📈 生长曲线")
        inner = ttk.LabelFrame(tab, text="细菌生长曲线拟合 (OD600 / CFU)")
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        self.gc_file = tk.StringVar()
        self._file_row(inner, "数据文件", self.gc_file,
                       [("Excel/CSV", "*.xlsx *.xls *.csv")])
        self.gc_out = tk.StringVar(value="output")
        self._output_row(inner, self.gc_out)
        self._run_button(inner, "🚀 运行生长曲线分析",
                         lambda: self._run_async(gc_run, path=self.gc_file.get(),
                                                 output_dir=self.gc_out.get()))

    # ---------- LIPSS/DLOA ----------
    def _build_dloa_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🔬 LIPSS/DLOA")
        inner = ttk.LabelFrame(tab, text="SEM 图像 LIPSS 周期与取向角分析")
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        self.dloa_folder = tk.StringVar()
        self._folder_row(inner, "SEM 图像文件夹", self.dloa_folder)
        row = ttk.Frame(inner)
        row.pack(fill="x", pady=4)
        ttk.Label(row, text="每微米像素数", width=16).pack(side="left")
        self.dloa_ppm = tk.StringVar(value="32.0")
        ttk.Entry(row, textvariable=self.dloa_ppm, width=12).pack(side="left", padx=4)
        ttk.Label(row, text="(31.25 nm/px = 32)", foreground="#a6adc8").pack(side="left")
        self.dloa_out = tk.StringVar(value="output")
        self._output_row(inner, self.dloa_out)
        self._run_button(inner, "🚀 运行 DLOA 分析",
                         lambda: self._run_async(
                             dloa_run, folder=self.dloa_folder.get(),
                             output_dir=self.dloa_out.get(),
                             pixel_size_um=1.0 / float(self.dloa_ppm.get())))

    # ---------- XDLVO ----------
    def _build_xdlvo_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🧫 XDLVO")
        inner = ttk.LabelFrame(tab, text="XDLVO 细菌粘附预测")
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        ttk.Label(row, text="θ 二碘甲烷 (°)", width=16).pack(side="left")
        self.xd_t1 = tk.StringVar(value="48.2")
        ttk.Entry(row, textvariable=self.xd_t1, width=10).pack(side="left")

        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        ttk.Label(row, text="θ 水 (°)", width=16).pack(side="left")
        self.xd_t2 = tk.StringVar(value="72.3")
        ttk.Entry(row, textvariable=self.xd_t2, width=10).pack(side="left")

        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        ttk.Label(row, text="θ 甲酰胺 (°)", width=16).pack(side="left")
        self.xd_t3 = tk.StringVar(value="61.5")
        ttk.Entry(row, textvariable=self.xd_t3, width=10).pack(side="left")

        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        ttk.Label(row, text="细菌半径 (nm)", width=16).pack(side="left")
        self.xd_r = tk.StringVar(value="500")
        ttk.Entry(row, textvariable=self.xd_r, width=10).pack(side="left")
        ttk.Label(row, text="  离子强度 (M)", foreground="#a6adc8").pack(side="left", padx=(12, 0))
        self.xd_i = tk.StringVar(value="0.01")
        ttk.Entry(row, textvariable=self.xd_i, width=10).pack(side="left")

        self.xd_out = tk.StringVar(value="output")
        self._output_row(inner, self.xd_out)
        self._run_button(inner, "🚀 运行 XDLVO 分析",
                         lambda: self._run_async(
                             xdlvo_run,
                             contact_angles=(float(self.xd_t1.get()),
                                             float(self.xd_t2.get()),
                                             float(self.xd_t3.get())),
                             radius_nm=float(self.xd_r.get()),
                             I_M=float(self.xd_i.get()),
                             output_dir=self.xd_out.get()))

    # ---------- LIVE/DEAD ----------
    def _build_livedead_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="🦠 LIVE/DEAD")
        inner = ttk.LabelFrame(tab, text="LIVE/DEAD 存活率统计 + 双因素 ANOVA")
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        self.ld_file = tk.StringVar()
        self._file_row(inner, "数据文件", self.ld_file,
                       [("Excel/CSV", "*.xlsx *.xls *.csv")])
        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        ttk.Label(row, text="工作表名 (可选)", width=16).pack(side="left")
        self.ld_sheet = tk.StringVar()
        ttk.Entry(row, textvariable=self.ld_sheet, width=20).pack(side="left", padx=4)
        self.ld_out = tk.StringVar(value="output")
        self._output_row(inner, self.ld_out)
        self._run_button(inner, "🚀 运行 LIVE/DEAD 分析",
                         lambda: self._run_async(
                             ld_run, path=self.ld_file.get(),
                             sheet=self.ld_sheet.get() or None,
                             output_dir=self.ld_out.get()))

    # ---------- 接触角 ----------
    def _build_contact_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="💧 接触角/表面能")
        inner = ttk.LabelFrame(tab, text="OWRK 表面自由能计算")
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        ttk.Label(row, text="液体1 接触角 (°)", width=16).pack(side="left")
        self.ca_t1 = tk.StringVar(value="72.3")
        ttk.Entry(row, textvariable=self.ca_t1, width=10).pack(side="left")
        ttk.Label(row, text="液体1", foreground="#a6adc8").pack(side="left", padx=(12, 0))
        self.ca_l1 = tk.StringVar(value="water")
        ttk.Combobox(row, textvariable=self.ca_l1, width=14,
                     values=["water", "diiodomethane", "formamide", "glycerol", "ethylene_glycol"]).pack(side="left")

        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        ttk.Label(row, text="液体2 接触角 (°)", width=16).pack(side="left")
        self.ca_t2 = tk.StringVar(value="48.2")
        ttk.Entry(row, textvariable=self.ca_t2, width=10).pack(side="left")
        ttk.Label(row, text="液体2", foreground="#a6adc8").pack(side="left", padx=(12, 0))
        self.ca_l2 = tk.StringVar(value="diiodomethane")
        ttk.Combobox(row, textvariable=self.ca_l2, width=14,
                     values=["water", "diiodomethane", "formamide", "glycerol", "ethylene_glycol"]).pack(side="left")

        self._run_button(inner, "🚀 计算表面能",
                         lambda: self._run_async(
                             ca_run, theta1=float(self.ca_t1.get()),
                             theta2=float(self.ca_t2.get()),
                             liquid1=self.ca_l1.get(), liquid2=self.ca_l2.get()))

    def run(self):
        self.root.mainloop()


def main():
    app = LabToolboxApp()
    app.run()


if __name__ == "__main__":
    main()
