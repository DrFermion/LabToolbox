# -*- coding: utf-8 -*-
"""
实验室工具箱 GUI 界面 (tkinter) - 支持中英文切换
- 5 个模块, 每个都有独立配置面板
- 顶部 中/EN 切换按钮
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
from labtoolbox.i18n import tr


class LabToolboxApp:
    def __init__(self):
        self.lang = "zh"  # 'zh' | 'en'
        self._widgets = []  # (widget, text_key) 用于语言切换时刷新

        self.root = tk.Tk()
        self.root.title("实验室工具箱 LabToolbox")
        self.root.geometry("780x580")
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

        # 顶部栏: 标题 + 语言切换
        header = tk.Frame(self.root, bg="#1e1e2e")
        header.pack(fill="x", padx=10, pady=(8, 2))

        self.title_label = tk.Label(header, text=tr("🧪 实验室工具箱 LabToolbox", self.lang),
                                    bg="#1e1e2e", fg="#89b4fa",
                                    font=("Microsoft YaHei UI", 16, "bold"))
        self.title_label.pack(side="left")

        self.lang_btn = tk.Button(header, text="EN", command=self.toggle_lang,
                                  bg="#45475a", fg="#cdd6f4", relief="flat",
                                  activebackground="#89b4fa", activeforeground="#11111b",
                                  font=("Microsoft YaHei UI", 10, "bold"),
                                  cursor="hand2", padx=12, pady=2)
        self.lang_btn.pack(side="right")

        # 标签页
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        self._build_all_tabs()

        # 底部状态栏
        self.status_var = tk.StringVar(value=tr("就绪 - 选择一个模块配置并运行", self.lang))
        status = tk.Label(self.root, textvariable=self.status_var, bg="#1e1e2e",
                          fg="#a6e3a1", font=("Microsoft YaHei UI", 9), pady=6)
        status.pack(fill="x")

    # ---------- 语言切换 ----------
    def toggle_lang(self):
        self.lang = "en" if self.lang == "zh" else "zh"
        self.lang_btn.config(text="中" if self.lang == "en" else "EN")
        self._refresh_all_texts()
        self.status_var.set(tr("就绪 - 选择一个模块配置并运行", self.lang))

    def _refresh_all_texts(self):
        """刷新所有已注册控件的文本"""
        self.title_label.config(text=tr("🧪 实验室工具箱 LabToolbox", self.lang))
        for widget, key in self._widgets:
            try:
                widget.config(text=tr(key, self.lang))
            except Exception:
                pass

    def _T(self, text):
        """注册并返回翻译文本 (用于 Label/Button/Notebook tab)"""
        return tr(text, self.lang)

    # ---------- 通用组件 ----------
    def _file_row(self, parent, label, var, filetypes):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        lbl = ttk.Label(row, text=tr(label, self.lang), width=18)
        lbl.pack(side="left")
        self._widgets.append((lbl, label))
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=4)
        btn = ttk.Button(row, text=tr("浏览...", self.lang),
                         command=lambda: var.set(filedialog.askopenfilename(filetypes=filetypes)))
        btn.pack(side="left")
        self._widgets.append((btn, "浏览..."))
        return row

    def _folder_row(self, parent, label, var):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        lbl = ttk.Label(row, text=tr(label, self.lang), width=18)
        lbl.pack(side="left")
        self._widgets.append((lbl, label))
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=4)
        btn = ttk.Button(row, text=tr("浏览...", self.lang),
                         command=lambda: var.set(filedialog.askdirectory()))
        btn.pack(side="left")
        self._widgets.append((btn, "浏览..."))
        return row

    def _output_row(self, parent, var):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=4)
        lbl = ttk.Label(row, text=tr("输出目录", self.lang), width=18)
        lbl.pack(side="left")
        self._widgets.append((lbl, "输出目录"))
        ttk.Entry(row, textvariable=var).pack(side="left", fill="x", expand=True, padx=4)
        btn = ttk.Button(row, text=tr("浏览...", self.lang),
                         command=lambda: var.set(filedialog.askdirectory()))
        btn.pack(side="left")
        self._widgets.append((btn, "浏览..."))
        return row

    def _run_button(self, parent, text, callback):
        btn = ttk.Button(parent, text=tr(text, self.lang), command=callback)
        btn.pack(pady=10)
        self._widgets.append((btn, text))
        return btn

    def _run_async(self, fn, *args):
        """后台线程运行, 完成后更新状态"""
        self.status_var.set(tr("⏳ 运行中...", self.lang))
        def worker():
            try:
                result = fn(*args)
                self.root.after(0, lambda: self.status_var.set(tr("✅ 完成! 输出见输出目录", self.lang)))
                if isinstance(result, dict) and "figure" in result:
                    self.root.after(0, lambda: messagebox.showinfo(
                        tr("完成", self.lang),
                        f"{tr('分析完成!', self.lang)}\n{tr('图表: ', self.lang)}{result['figure']}"))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"❌ {e}"))
                self.root.after(0, lambda: messagebox.showerror(tr("错误", self.lang), str(e)))
        threading.Thread(target=worker, daemon=True).start()

    # ---------- 标签页 ----------
    def _build_all_tabs(self):
        self._build_growth_tab()
        self._build_dloa_tab()
        self._build_xdlvo_tab()
        self._build_livedead_tab()
        self._build_contact_tab()

    def _build_growth_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=tr("📈 生长曲线", self.lang))
        self._widgets.append((tab, "📈 生长曲线"))  # notebook tab 文本单独处理
        inner = ttk.LabelFrame(tab, text=tr("细菌生长曲线拟合 (OD600 / CFU)", self.lang))
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        self.gc_file = tk.StringVar()
        self._file_row(inner, "数据文件", self.gc_file,
                       [("Excel/CSV", "*.xlsx *.xls *.csv")])
        self.gc_out = tk.StringVar(value="output")
        self._output_row(inner, self.gc_out)
        self._run_button(inner, "🚀 运行生长曲线分析",
                         lambda: self._run_async(gc_run, path=self.gc_file.get(),
                                                 output_dir=self.gc_out.get()))

    def _build_dloa_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=tr("🔬 LIPSS/DLOA", self.lang))
        inner = ttk.LabelFrame(tab, text=tr("SEM 图像 LIPSS 周期与取向角分析", self.lang))
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        self.dloa_folder = tk.StringVar()
        self._folder_row(inner, "SEM 图像文件夹", self.dloa_folder)
        row = ttk.Frame(inner)
        row.pack(fill="x", pady=4)
        lbl = ttk.Label(row, text=tr("每微米像素数", self.lang), width=18)
        lbl.pack(side="left")
        self._widgets.append((lbl, "每微米像素数"))
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

    def _build_xdlvo_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=tr("🧫 XDLVO", self.lang))
        inner = ttk.LabelFrame(tab, text=tr("XDLVO 细菌粘附预测", self.lang))
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        lbl = ttk.Label(row, text=tr("θ 二碘甲烷 (°)", self.lang), width=18)
        lbl.pack(side="left"); self._widgets.append((lbl, "θ 二碘甲烷 (°)"))
        self.xd_t1 = tk.StringVar(value="48.2")
        ttk.Entry(row, textvariable=self.xd_t1, width=10).pack(side="left")

        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        lbl = ttk.Label(row, text=tr("θ 水 (°)", self.lang), width=18)
        lbl.pack(side="left"); self._widgets.append((lbl, "θ 水 (°)"))
        self.xd_t2 = tk.StringVar(value="72.3")
        ttk.Entry(row, textvariable=self.xd_t2, width=10).pack(side="left")

        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        lbl = ttk.Label(row, text=tr("θ 甲酰胺 (°)", self.lang), width=18)
        lbl.pack(side="left"); self._widgets.append((lbl, "θ 甲酰胺 (°)"))
        self.xd_t3 = tk.StringVar(value="61.5")
        ttk.Entry(row, textvariable=self.xd_t3, width=10).pack(side="left")

        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        lbl = ttk.Label(row, text=tr("细菌半径 (nm)", self.lang), width=18)
        lbl.pack(side="left"); self._widgets.append((lbl, "细菌半径 (nm)"))
        self.xd_r = tk.StringVar(value="500")
        ttk.Entry(row, textvariable=self.xd_r, width=10).pack(side="left")
        ttk.Label(row, text=tr("离子强度 (M)", self.lang), foreground="#a6adc8").pack(side="left", padx=(12, 0))
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

    def _build_livedead_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=tr("🦠 LIVE/DEAD", self.lang))
        inner = ttk.LabelFrame(tab, text=tr("LIVE/DEAD 存活率统计 + 双因素 ANOVA", self.lang))
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        self.ld_file = tk.StringVar()
        self._file_row(inner, "数据文件", self.ld_file,
                       [("Excel/CSV", "*.xlsx *.xls *.csv")])
        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        lbl = ttk.Label(row, text=tr("工作表名 (可选)", self.lang), width=18)
        lbl.pack(side="left"); self._widgets.append((lbl, "工作表名 (可选)"))
        self.ld_sheet = tk.StringVar()
        ttk.Entry(row, textvariable=self.ld_sheet, width=20).pack(side="left", padx=4)
        self.ld_out = tk.StringVar(value="output")
        self._output_row(inner, self.ld_out)
        self._run_button(inner, "🚀 运行 LIVE/DEAD 分析",
                         lambda: self._run_async(
                             ld_run, path=self.ld_file.get(),
                             sheet=self.ld_sheet.get() or None,
                             output_dir=self.ld_out.get()))

    def _build_contact_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text=tr("💧 接触角/表面能", self.lang))
        inner = ttk.LabelFrame(tab, text=tr("OWRK 表面自由能计算", self.lang))
        inner.pack(fill="both", expand=True, padx=10, pady=10)

        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        lbl = ttk.Label(row, text=tr("液体1 接触角 (°)", self.lang), width=18)
        lbl.pack(side="left"); self._widgets.append((lbl, "液体1 接触角 (°)"))
        self.ca_t1 = tk.StringVar(value="72.3")
        ttk.Entry(row, textvariable=self.ca_t1, width=10).pack(side="left")
        lbl2 = ttk.Label(row, text=tr("液体1", self.lang), foreground="#a6adc8")
        lbl2.pack(side="left", padx=(12, 0)); self._widgets.append((lbl2, "液体1"))
        self.ca_l1 = tk.StringVar(value="water")
        ttk.Combobox(row, textvariable=self.ca_l1, width=14,
                     values=["water", "diiodomethane", "formamide", "glycerol", "ethylene_glycol"]).pack(side="left")

        row = ttk.Frame(inner); row.pack(fill="x", pady=4)
        lbl = ttk.Label(row, text=tr("液体2 接触角 (°)", self.lang), width=18)
        lbl.pack(side="left"); self._widgets.append((lbl, "液体2 接触角 (°)"))
        self.ca_t2 = tk.StringVar(value="48.2")
        ttk.Entry(row, textvariable=self.ca_t2, width=10).pack(side="left")
        lbl2 = ttk.Label(row, text=tr("液体2", self.lang), foreground="#a6adc8")
        lbl2.pack(side="left", padx=(12, 0)); self._widgets.append((lbl2, "液体2"))
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
