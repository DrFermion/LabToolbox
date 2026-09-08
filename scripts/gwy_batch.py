#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
"""
gwy_batch.py - Gwyddion kernel batch processing (leveling + ISO roughness stats)
Runs inside WSL Ubuntu with pygwy (python2.7 + Gwyddion 2.67 built --enable-pygwy).

Pipeline per file (true Gwyddion processing):
  1. load SPM file (.ibw/.tif/...) via gwy_file_load
  2. pick channel (auto: title contains 'height', fallback ch0)
  3. optional plane leveling  (gwy_process_func_run 'level', RUN_IMMEDIATE
     == GUI Data Process -> Correct -> Plane Level)
  4. statistics via Gwyddion kernel: get_stats -> (mean, Sa/ra, Sq/rms, skew, kurt),
     get_min_max -> Sz   (values converted m -> nm by magnitude heuristic)

Usage:
  python2.7 gwy_batch.py <file|dir> [-o out.csv] [--level] [--channel N]

Output CSV columns: file, channel, mean_nm, Sa_nm, Sq_nm, Sz_nm, skew, kurt
"""
import sys
import os
import csv
import glob
import types

# --- fake gtk so pygwy's class registration completes headless ---
class _DummyGtk(object):
    gtk_version = (2, 24, 0)
    pygtk_version = (2, 24, 0)
    def __getattr__(self, name):
        t = type(name, (object,), {})
        setattr(self, name, t)
        return t

sys.modules['gtk'] = _DummyGtk()
sys.modules['gtk.gdk'] = _DummyGtk()

sys.path.insert(0, '/usr/local/lib/python2.7/site-packages')
import gwy  # noqa

M_TO_NM = 1e9


def pick_data_field(container, ch_hint=None):
    """Return (df, key) of chosen channel (auto: height-like title, else ch0)."""
    keys = sorted([k for k in container.keys_by_name() if k.endswith('/data')])
    if not keys:
        return None, None
    if ch_hint is not None and ch_hint < len(keys):
        return container.get_value_by_name(keys[ch_hint]), keys[ch_hint]
    # auto: prefer title containing 'height'
    for k in keys:
        tkey = k + '/title'
        try:
            title = container.get_string_by_name(tkey) or ''
            if 'height' in title.lower():
                return container.get_value_by_name(k), k
        except Exception:
            pass
    return container.get_value_by_name(keys[0]), keys[0]


def to_nm(v, df):
    """Convert data value to nm: Bruker .ibw is stored in metres."""
    if v is None:
        return None
    try:
        unit = df.get_si_unit_z()
        # unit = (base_string, power); if base 'm' -> convert
        if unit and unit[0] in ('m',):
            return v * M_TO_NM
    except Exception:
        pass
    return v * M_TO_NM if abs(v) < 1e-3 else v


def process_file(path, do_level, ch_hint):
    c = gwy.gwy_file_load(path, 0)
    if c is None:
        return None
    df, key = pick_data_field(c, ch_hint)
    if df is None:
        return None
    # register so process functions can resolve the 'current' data field
    gwy.gwy_app_data_browser_add(c)
    gwy.gwy_app_data_browser_select_data_field(c, int(key.split('/')[1]))
    if do_level:
        gwy.gwy_process_func_run('level', c, gwy.RUN_IMMEDIATE)
    st = df.get_stats()          # (mean, Sa, Sq, skew, kurt)
    mn = df.get_min_max()
    return {
        'file': os.path.basename(path),
        'channel': key.split('/')[1],
        'mean_nm': to_nm(st[0], df),
        'Sa_nm': to_nm(st[1], df),
        'Sq_nm': to_nm(st[2], df),
        'Sz_nm': to_nm(mn[1] - mn[0], df),
        'skew': st[3],
        'kurt': st[4],
    }


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    inp = args[0]
    out_csv = 'gwy_batch_output.csv'
    do_level = '--level' in args
    ch_hint = None
    if '--channel' in args:
        ch_hint = int(args[args.index('--channel') + 1])
    if '-o' in args:
        out_csv = args[args.index('-o') + 1]

    if os.path.isdir(inp):
        paths = sorted(glob.glob(os.path.join(inp, '*.ibw')))
        if not paths:
            paths = sorted(glob.glob(os.path.join(inp, '*.tif')))
        if not paths:
            paths = sorted(glob.glob(os.path.join(inp, '*.gwy')))
    else:
        paths = [inp]

    rows = []
    for p in paths:
        try:
            r = process_file(p, do_level, ch_hint)
            if r:
                rows.append(r)
                print('%s: Sa=%.4f nm Sq=%.4f nm Sz=%.1f nm' % (
                    r['file'], r['Sa_nm'] or 0, r['Sq_nm'] or 0, r['Sz_nm'] or 0))
        except Exception as e:
            print('ERROR %s: %s' % (os.path.basename(p), str(e)[:100]))
    if rows:
        with open(out_csv, 'wb') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print('Wrote %d rows -> %s' % (len(rows), out_csv))
    return 0


if __name__ == '__main__':
    sys.exit(main())
