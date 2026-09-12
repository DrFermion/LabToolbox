# -*- coding: utf-8 -*-
"""650 nm water contact angle — add Day 2 and rebuild the plots.

Day 2 raw values were transcribed from the handwritten sheet
(header: Day 2 · 23 °C · 44% RH · 650 nm, each cell = left/right reading):

    column 1 (marker (1))        82.1/82.5   67.6/69.6   57.7/60.3
    column 2 (no marker)         65.6/67.3   58.1/55.8   52.3/51.7
    column 3 (marker (2))        64.4/64.7   54.0/54.4   51.1/51.9
    column 4 (marker C)          65.1/66.0   67.1/68.3   65.8/64.2

Column order matches the existing workbook (area1 | area1 (rot 90°) | area2 | control);
markers on the sheet are the area numbers ((1) area1, (2) area2) plus C for the control.

Outputs (into the 650 folder):
    650nm.xlsx                                     Day 2 appended + summary + raw note
    650nm_water_contact_angle.png                  mean ± SD, Day 0-2   (updated)
    650nm_water_contact_angle_first_repeat.png     repeat 1 only        (new, requested)
    650nm_water_contact_angle_repeat_drift.png     within-day drift     (supporting)
"""
import os
import statistics as st

import openpyxl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = (r"F:\OneDrive - University of Dundee\Svetlana Zolotovskaya (Staff) 的文件 - "
        r"Ruinong Pan_Antibacterial Surfaces\Contact Angle and Surface energy\650")
XLSX = os.path.join(BASE, "650nm.xlsx")

GROUPS = ["area1", "area1-R90", "area2", "control"]
LABEL = {"area1": "area1", "area1-R90": "area1 (rot 90°)", "area2": "area2", "control": "control"}
COLOR = {"area1": "#1565C0", "area1-R90": "#EF6C00", "area2": "#6A1B9A", "control": "#546E7A"}
MARK = {"area1": "o", "area1-R90": "s", "area2": "^", "control": "D"}

# Day 2 (12/9, 23 °C, 44% RH) — left/right readings per repeat
DAY2 = {
    "area1":     [(82.1, 82.5), (67.6, 69.6), (57.7, 60.3)],
    "area1-R90": [(65.6, 67.3), (58.1, 55.8), (52.3, 51.7)],
    "area2":     [(64.4, 64.7), (54.0, 54.4), (51.1, 51.9)],
    "control":   [(65.1, 66.0), (67.1, 68.3), (65.8, 64.2)],
}
COND = {0: ("10/9", 24, 39), 1: ("11/9", 23, 34), 2: ("12/9", 23, 44)}
DAYS = ["Day 0", "Day 1", "Day 2"]


def avg(pair):
    vals = [v for v in pair if v is not None]
    return sum(vals) / len(vals)


def read_sheet(ws):
    """{day: {repeat: value}} from one area sheet."""
    out = {}
    for r in range(3, ws.max_row + 1):
        day = ws.cell(r, 1).value
        rep = ws.cell(r, 2).value
        if day is None or rep is None:
            continue
        if isinstance(rep, str) and rep.strip().lower().startswith("average"):
            continue
        vals = [ws.cell(r, c).value for c in (3, 4)]
        nums = [float(v) for v in vals if isinstance(v, (int, float))]
        if not nums:
            continue
        out.setdefault(str(day).strip(), {})[int(rep)] = sum(nums) / len(nums)
    return out


def append_day2(ws, pairs):
    """Write the Day 2 block under the existing Day 0/1 blocks."""
    last = 0
    for r in range(3, ws.max_row + 1):
        if ws.cell(r, 1).value is not None or ws.cell(r, 3).value is not None:
            last = r
    start = last + 2
    ws.cell(start - 1, 1)  # keep the blank spacer row
    for i, (left, right) in enumerate(pairs):
        r = start + i
        ws.cell(r, 1, "Day 2")
        ws.cell(r, 2, i + 1)
        ws.cell(r, 3, left)
        ws.cell(r, 4, right)
        ws.cell(r, 5, round(avg((left, right)), 2))
    ravg = start + len(pairs)
    ws.cell(ravg, 1, "Day 2")
    ws.cell(ravg, 2, "average")
    ws.cell(ravg, 5, round(st.mean(avg(p) for p in pairs), 2))
    return start, ravg


def stat(ws_data, day):
    vals = [v for v in ws_data.get(day, {}).values()]
    return (st.mean(vals), st.stdev(vals) if len(vals) > 1 else 0.0) if vals else (None, None)


def main():
    wb = openpyxl.load_workbook(XLSX)
    print("工作表:", wb.sheetnames)

    # ---- 1. append Day 2 to every area sheet ----
    for g in GROUPS:
        ws = wb[g]
        if "Day 2" in [str(ws.cell(r, 1).value).strip() for r in range(3, ws.max_row + 1)]:
            print(f"  {g}: Day 2 已存在, 跳过")
            continue
        start, ravg = append_day2(ws, DAY2[g])
        print(f"  {g}: Day 2 写入 r{start}-r{ravg}, 平均 {ws.cell(ravg, 5).value}")

    # ---- 2. read everything back (Day 0-2) ----
    data = {g: read_sheet(wb[g]) for g in GROUPS}
    for g in GROUPS:
        print(f"  {g}: days={sorted(data[g])}  means=" +
              ", ".join(f"{d}:{st.mean(data[g][d].values()):.2f}" for d in sorted(data[g])))

    # ---- 3. summary sheet ----
    ws = wb["summary"]
    if ws.cell(6, 1).value is None or "Day 2" not in str(ws.cell(6, 1).value):
        ws.insert_rows(6)
    date, temp, rh = COND[2]
    ws.cell(6, 1, "Day 2")
    ws.cell(6, 2, date)
    ws.cell(6, 3, temp)
    ws.cell(6, 4, rh)
    for j, g in enumerate(GROUPS):
        m, s = stat(data[g], "Day 2")
        ws.cell(6, 5 + j, f"{m:.2f} ± {s:.2f}")
    # Δ rows
    delta_rows = {"Δ (Day 1 − Day 0)": ("Day 0", "Day 1"), "Δ (Day 2 − Day 1)": ("Day 1", "Day 2"),
                  "Δ (Day 2 − Day 0)": ("Day 0", "Day 2")}
    r = 7
    for title, (d1, d2) in delta_rows.items():
        ws.cell(r, 1, title)
        for j, g in enumerate(GROUPS):
            m1, _ = stat(data[g], d1)
            m2, _ = stat(data[g], d2)
            ws.cell(r, 5 + j, f"{m2 - m1:+.2f}" if (m1 is not None and m2 is not None) else "")
        r += 1

    # ---- 4. raw note sheet: keep the transcribed handwriting ----
    ws = wb["raw note"]
    ws.cell(2, 1, "Day 2 — 12/9 — 23 °C — 44% RH (transcribed from handwritten sheet, L/R as written)")
    for i, g in enumerate(GROUPS):
        r = 4 + i
        ws.cell(r, 1, f"Day 2 / {g}")
        for j, (left, right) in enumerate(DAY2[g]):
            ws.cell(r, 2 + j, f"{left}/{right}")

    wb.save(XLSX)
    print("已写回:", XLSX)

    # ---- 5. figure helper ----
    def draw(path, values, title, note, ymax=None):
        fig, ax = plt.subplots(figsize=(7.6, 5.2))
        xs = range(len(DAYS))
        for g in GROUPS:
            ys = [values[g].get(d, (None, 0))[0] for d in DAYS]
            es = [values[g].get(d, (None, 0))[1] for d in DAYS]
            ax.errorbar(xs, ys, yerr=es, color=COLOR[g], marker=MARK[g], ls="-", lw=1.6,
                        ms=6, capsize=4, label=LABEL[g])
            for xx, yy in zip(xs, ys):
                if yy is not None:
                    ax.annotate(f"{yy:.1f}", (xx, yy), xytext=(6, 7),
                                textcoords="offset points", fontsize=8, color=COLOR[g])
        ax.set_xticks(list(xs))
        ax.set_xticklabels([f"{d} ({COND[i][0]})" for i, d in enumerate(DAYS)])
        for i, d in enumerate(DAYS):
            ax.annotate(f"{COND[i][1]} °C, {COND[i][2]}% RH", (i, 0), xytext=(0, -34),
                        textcoords="offset points", ha="center", fontsize=8, color="#555555")
        ax.set_ylabel("Water contact angle (deg)")
        ax.set_ylim(0, ymax or 100)
        ax.set_title(title, fontsize=11)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(title="Surface area", fontsize=9, title_fontsize=9, loc="upper left")
        if note:
            ax.text(0.99, 0.02, note, transform=ax.transAxes, ha="right", va="bottom",
                    fontsize=7.5, color="#666666", style="italic")
        fig.tight_layout()
        fig.savefig(path, dpi=200)
        plt.close(fig)
        return path

    # mean ± SD over all repeats
    mean_sd = {g: {d: stat(data[g], d) for d in DAYS} for g in GROUPS}
    draw(os.path.join(BASE, "650nm_water_contact_angle.png"), mean_sd,
         "650 nm sample — water contact angle (mean ± SD, n = 3)", "")

    # repeat 1 only (the first drop of each session)
    first = {g: {d: (data[g][d].get(1), 0.0) for d in DAYS if 1 in data[g].get(d, {})}
             for g in GROUPS}
    draw(os.path.join(BASE, "650nm_water_contact_angle_first_repeat.png"), first,
         "650 nm sample — water contact angle, 1st repeat only (mean of left/right)",
         "first drop of each measurement session", ymax=100)

    # within-day drift across the 3 repeats (why repeats do not agree)
    fig, ax = plt.subplots(figsize=(7.6, 5.2))
    for g in GROUPS:
        for i, d in enumerate(DAYS):
            ys = [data[g][d].get(k) for k in (1, 2, 3)]
            if any(v is None for v in ys):
                continue
            ax.plot([k + i * 3.6 for k in range(3)], ys, color=COLOR[g], marker=MARK[g],
                    ls="-" if g != "control" else "--", lw=1.4, ms=5, alpha=0.85,
                    label=LABEL[g] if i == 0 else None)
    ax.set_xticks([i * 3.6 + 1 for i in range(3)])
    ax.set_xticklabels([f"{d} ({COND[i][0]})" for i, d in enumerate(DAYS)])
    ax.set_xlabel("repeat 1 → 2 → 3 within each session")
    ax.set_ylabel("Water contact angle (deg)")
    ax.set_title("650 nm — repeat-to-repeat drift within a session", fontsize=11)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(title="Surface area", fontsize=9, title_fontsize=9, loc="upper left")
    fig.tight_layout()
    drift_path = os.path.join(BASE, "650nm_water_contact_angle_repeat_drift.png")
    fig.savefig(drift_path, dpi=200)
    plt.close(fig)

    print()
    print("Day 0 → 2, mean ± SD (all repeats):")
    for g in GROUPS:
        row = "  %-12s" % LABEL[g]
        for d in DAYS:
            m, s = mean_sd[g][d]
            row += f"  {d}: {m:5.1f}±{s:4.1f}"
        print(row)
    print()
    print("repeat 1 only:")
    for g in GROUPS:
        row = "  %-12s" % LABEL[g]
        for d in DAYS:
            v = data[g].get(d, {}).get(1)
            row += f"  {d}: {v:5.2f}" if v is not None else f"  {d}:   -  "
        print(row)
    print()
    print("图:", os.path.join(BASE, "650nm_water_contact_angle.png"))
    print("图:", os.path.join(BASE, "650nm_water_contact_angle_first_repeat.png"))
    print("图:", drift_path)


if __name__ == "__main__":
    main()
