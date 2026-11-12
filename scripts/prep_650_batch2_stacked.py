# -*- coding: utf-8 -*-
"""Prepare batch-B inputs for plot_650_multirepeat.py.

The batch stores both repeats in one CSV per species; the plotting script expects one
count directory per repeat.  This splits them and writes the exclusion registry
(S. aureus 3 h LIPSS, both repeats — acquisition artefact).
"""
import os

import pandas as pd

DS = ('F:/OneDrive - University of Dundee/Svetlana Zolotovskaya (Staff) 的文件 - '
      'Ruinong Pan_Antibacterial Surfaces/Live_Dead Bacteria Test/650nm-20261111')
OUT = 'E:/LabToolbox/output/650_batch2_20261112_min15/stacked'
SPECIES = [('E.coli', 'E. coli'), ('S.aureus', 'S. aureus')]

os.makedirs(OUT, exist_ok=True)
for rep, tag in [('repeat 1', 'repeat1'), ('repeat 2', 'repeat2')]:
    for sp_dir, _label in SPECIES:
        src = os.path.join(DS, 'imagej_counts_min15', sp_dir, 'livedead_raw_counts.csv')
        d = pd.read_csv(src, encoding='utf-8-sig')
        d = d[d['repeat'] == rep]
        dst_dir = os.path.join(OUT, tag, sp_dir)
        os.makedirs(dst_dir, exist_ok=True)
        d.to_csv(os.path.join(dst_dir, 'livedead_raw_counts.csv'), index=False,
                 encoding='utf-8-sig')
        print('%s/%s: %d rows, areas %s' % (tag, sp_dir, len(d), sorted(d.area.unique())))

rows = []
for rep in ['repeat 1', 'repeat 2']:
    rows.append(dict(level='cell', repeat=rep, species='S. aureus', time='3h', area='1',
                     field='', issue='acquisition anomaly on the LIPSS coupon',
                     detail=('Sub-cell speckle: 7 005-8 875 objects per field with median object '
                             'area 27-71 px in repeat 1; 1 751-2 118 red-channel objects at 39-48 px '
                             'in repeat 2 against 77-95 in the control, green channel normal.'),
                     evidence='object-size + exposure check (diagnose_650_batch2_acquisition.py), '
                              '2026-11-12',
                     rows_removed=5, source='documented'))
reg = pd.DataFrame(rows)
reg_path = os.path.join(OUT, 'batchB_exclusions_registry.csv')
reg.to_csv(reg_path, index=False, encoding='utf-8-sig')
print('registry ->', reg_path)
