"""Reproduce run-level metrics and flow evidence from saved experiments."""
import csv,json,math,re,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def percentile(vals,p):
 vals=sorted(vals)
 return vals[max(0,math.ceil(len(vals)*p)-1)] if vals else None

def main():
 records=[]; evidence=[]
 for folder in sorted((ROOT/'results').iterdir()):
  meta=folder/'experiment.json'
  if not meta.exists(): continue
  cfg=json.loads(meta.read_text()); rows=[]
  for f in sorted(folder.glob('client-*.csv')):
   with f.open() as stream: rows.extend(csv.DictReader(stream))
  expected=cfg['count_per_client']*2
  if len(rows)!=expected: raise ValueError(f'{folder.name}: {len(rows)} != {expected}')
  values=lambda key:[float(r[key]) for r in rows if r[key]!='']
  successes=sum(int(r['success']) for r in rows)
  records.append(dict(run=folder.name,mode=cfg['mode'],scenario=cfg['scenario'],samples=len(rows),successes=successes,success_pct=100*successes/len(rows),discovery_p50_ms=percentile(values('discovery_ms'),.5),discovery_p95_ms=percentile(values('discovery_ms'),.95),total_p95_ms=percentile(values('total_ms'),.95)))
  if cfg['scenario'] in ('failure','churn'):
   def read(name):return (folder/name).read_text()
   def allowed(text):return sorted(re.findall(r'priority=200,udp,nw_dst=([\d.]+)',text))
   def drops(text):
    for line in text.splitlines():
     if 'priority=100' in line and 'tp_dst=10001 ' in line:
      return int(re.search(r'n_packets=(\d+)',line).group(1))
    return 0
   before=read('flows-after-expiry.txt');after=read('flows-after-stale-probe.txt')
   evidence.append(dict(run=folder.name,allowed_after_expiry=allowed(before),stale_drop_delta=drops(after)-drops(before),allowed_after_restart=allowed(read('flows-after-restart.txt')) if cfg['scenario']=='churn' else []))
 with (ROOT/'results/verified-run-metrics.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=records[0]);w.writeheader();w.writerows(records)
 groups=[]
 for mode,scenario in sorted({(r['mode'],r['scenario']) for r in records}):
  rs=[r for r in records if r['mode']==mode and r['scenario']==scenario]
  g=dict(mode=mode,scenario=scenario,runs=len(rs),samples=sum(r['samples'] for r in rs),successes=sum(r['successes'] for r in rs))
  for key in ('success_pct','discovery_p50_ms','discovery_p95_ms','total_p95_ms'):
   vals=[r[key] for r in rs];g[key]={'median':statistics.median(vals),'min':min(vals),'max':max(vals)}
  groups.append(g)
 (ROOT/'results/verified-analysis.json').write_text(json.dumps(dict(groups=groups,evidence=evidence),indent=2))
 print(json.dumps(dict(groups=groups,evidence=evidence),indent=2))
if __name__=='__main__':main()
