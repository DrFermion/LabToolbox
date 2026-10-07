# -*- coding: utf-8 -*-
"""Scan how the Sipe-predicted LIPSS period shifts with the assumed effective
dielectric function (bulk vs laser-excited / oxidised surface), at 515 nm.

Run:  python lipss_eps_scan.py   (from the same folder as lipss_period_predictor.py)
"""
import os
import numpy as np

import lipss_period_predictor as P
from lipss_sipe.core import compute_eta_array


def main():
    lam = 515.0
    eps_list = [
        ("bulk (Karlsson)", -8.44, 13.35),
        ("eff A", -6.0, 8.0),
        ("eff B", -4.5, 5.0),
        ("eff C", -3.5, 3.5),
        ("eff D", -2.8, 2.5),
        ("eff E", -2.3, 1.5),
    ]
    kx = np.linspace(-1.8, 1.8, 121)
    ky = np.linspace(-1.8, 1.8, 121)
    out = r"C:\Users\PC\AppData\Local\hermes\cache\scratch\review_20261007\lipss_probe"
    rows = []
    for name, e1, e2 in eps_list:
        eps = complex(e1, e2)
        ETA = compute_eta_array(kx, ky, "spol", 0.0, eps, P.F_FACTOR, P.S_FACTOR)
        peaks = P.top_peaks(kx, ky, ETA)
        p = peaks[0]
        rows.append((name, e1, e2, p[2], lam / p[2], p[4]))
        print(f"{name:16s} eps={e1:+.1f}{e2:+.1f}j | peak |k|={p[2]:.3f} "
              f"-> Lambda = {lam/p[2]:.1f} nm ({(lam/p[2])/lam:.2f} lambda), eta={p[4]:.2f}")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "eps_scan.csv"), "w", encoding="utf-8") as f:
        f.write("case,eps1,eps2,kappa,period_nm,period_over_lambda,eta\n")
        for r in rows:
            f.write(f"{r[0]},{r[1]},{r[2]},{r[3]:.4f},{r[4]:.1f},{r[4]/lam:.3f},{r[5]:.2f}\n")
    print("scan saved to", out)


if __name__ == "__main__":
    main()
