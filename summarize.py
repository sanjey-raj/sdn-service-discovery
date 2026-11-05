"""Aggregate measured CSVs only; no synthetic benchmark values."""
import csv
import glob
import math
import statistics
import sys

print('run,samples,success_pct,discovery_p50_ms,discovery_p95_ms,total_p95_ms')
for folder in sys.argv[1:]:
    rows = []
    for path in glob.glob(folder + '/client-*.csv'):
        with open(path) as f:
            rows.extend(csv.DictReader(f))
    if not rows:
        continue
    def metric(key, percentile):
        vals = sorted(float(r[key]) for r in rows if r[key] != '')
        return round(vals[max(0, math.ceil(len(vals)*percentile)-1)], 3) if vals else ''
    print(','.join(map(str, [folder, len(rows), round(100*sum(int(r['success']) for r in rows)/len(rows),2),
                            metric('discovery_ms',.5), metric('discovery_ms',.95), metric('total_ms',.95)])))
