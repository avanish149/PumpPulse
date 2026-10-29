import json, math, uuid
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from engine import run, POLICIES
from service import connect

def explain_result(result):
 """Explain qualification failures without changing winners or simulated outcomes."""
 trials=result['trials'];counts={p:dict(demand_failures=0,risk_failures=0,both_failures=0,mean_water_L=0.,minimum_water_L=float('inf'),maximum_water_L=0.) for p in POLICIES};matched=0
 for trial in trials:
  outcomes=trial['outcomes'];reference=outcomes[0]
  matched+=int(all(all(math.isclose(o[k],reference[k],rel_tol=1e-9,abs_tol=1e-6) for k in ('water_L','wear_u','low_water_risk_hours')) for o in outcomes[1:]))
  for outcome in outcomes:
   stats=counts[outcome['policy']];demand=outcome['shortfall_L']>1e-6;risk=outcome['low_water_risk_hours']>0
   stats['demand_failures']+=int(demand);stats['risk_failures']+=int(risk);stats['both_failures']+=int(demand and risk);stats['mean_water_L']+=outcome['water_L']/len(trials);stats['minimum_water_L']=min(stats['minimum_water_L'],outcome['water_L']);stats['maximum_water_L']=max(stats['maximum_water_L'],outcome['water_L'])
 for summary in result['summary']:summary.update(counts[summary['policy']])
 result['diagnostics']=dict(matching_output_scenarios=matched,scenario_count=len(trials),qualification='Full daily demand and zero low-water-risk hours. No qualifying policy means no winner; low stress alone does not qualify.',demand_only_no_winner_scenarios=sum(t['winner'] is None and all(o['low_water_risk_hours']==0 for o in t['outcomes']) for t in trials))
 return result

def challenge(experiment,payload,persist=True):
 if not isinstance(payload,dict) or set(payload)-{'experiment_id','date','scenarios','seed','solar_pct','groundwater_m','wear_pct'}:raise ValueError('Unknown uncertainty request fields')
 count=payload.get('scenarios',30);seed=payload.get('seed',42)
 if isinstance(count,bool) or not isinstance(count,int) or not 10<=count<=100:raise ValueError('Use 10 to 100 scenarios')
 if isinstance(seed,bool) or not isinstance(seed,int) or not 0<=seed<=2147483647:raise ValueError('Invalid seed')
 limits={'solar_pct':(15,0,50),'groundwater_m':(1,0,4),'wear_pct':(30,0,50)};ranges={}
 for k,(default,lo,hi) in limits.items():
  v=payload.get(k,default)
  if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:raise ValueError(k+' outside allowed range')
  ranges[k]=v
 day=payload.get('date');rows=[x for x in experiment['inputs'] if x['timestamp_IST'][:10]==day]
 if len(rows)!=48:raise ValueError('Select a complete day within the saved replay')
 base=pd.DataFrame(rows);base['timestamp_IST']=pd.to_datetime(base.timestamp_IST)
 if base.groundwater_depth_m_assumed.min()<=ranges['groundwater_m']:raise ValueError('Groundwater shift could cross ground level; reduce the range')
 rng=np.random.default_rng(seed);trials=[];stats={p:dict(policy=p,wins=0,feasible=0,worst_shortfall_L=0.,worst_wear_u=0.) for p in POLICIES};none=0
 for i in range(count):
  shift=float(rng.uniform(-ranges['groundwater_m'],ranges['groundwater_m']));solar=float(rng.uniform(1-ranges['solar_pct']/100,1+ranges['solar_pct']/100));mult={k:float(rng.uniform(1-ranges['wear_pct']/100,1+ranges['wear_pct']/100)) for k in ('speed_wear','dry_wear','start_wear')}
  c=experiment['config'].copy()
  for k,v in mult.items():c[k]*=v
  inputs=base.copy();inputs['groundwater_depth_m_assumed']+=shift;inputs['solar_mean_W_m2']*=solar;outcomes=[]
  for p in POLICIES:
   r=run(inputs,int(p[1:]),c);water=float(r.water_L.sum());wear=float(r.wear_u.sum());risk=float(r.low_water_risk_hours.sum());short=max(0,c['daily_target_L']-water);feasible=short<=1e-6 and risk==0
   outcomes.append(dict(policy=p,water_L=water,wear_u=wear,low_water_risk_hours=risk,shortfall_L=short,feasible=feasible));s=stats[p];s['feasible']+=int(feasible);s['worst_shortfall_L']=max(s['worst_shortfall_L'],short);s['worst_wear_u']=max(s['worst_wear_u'],wear)
  candidates=[x for x in outcomes if x['feasible']];winner=min(candidates,key=lambda x:(x['wear_u'],x['policy']))['policy'] if candidates else None
  if winner:stats[winner]['wins']+=1
  else:none+=1
  trials.append(dict(index=i,groundwater_shift_m=shift,solar_multiplier=solar,wear_multipliers=mult,winner=winner,outcomes=outcomes))
 summary=[]
 for p,s in stats.items():s['win_pct']=100*s['wins']/count;s['feasible_pct']=100*s['feasible']/count;summary.append(s)
 result=dict(id=str(uuid.uuid4()),experiment_id=experiment['id'],date=day,created=datetime.now(timezone.utc).isoformat(),seed=seed,scenarios=count,ranges=ranges,summary=summary,no_feasible_scenarios=none,trials=trials,method='Isolated-day scenarios start at rest. All policies share each perturbed input series. Feasible means full daily target and zero low-submergence hours. Lowest relative wear wins; exact ties use policy ID. Uniform ranges are experiment assumptions, not calibrated probability distributions. Frequencies are not statistical confidence or field safety certificates.',engine_version='local-backend-1.1',source_version=experiment['version'],base_config=experiment['config'],sources=experiment['metadata']['sources'])
 explain_result(result)
 if persist:
  with connect() as db:
   db.execute('CREATE TABLE IF NOT EXISTS robustness (id TEXT PRIMARY KEY, experiment_id TEXT, result TEXT)');db.execute('INSERT INTO robustness VALUES (?,?,?)',(result['id'],experiment['id'],json.dumps(result,allow_nan=False)))
 return result

def load_challenge(identifier):
 with connect() as db:
  db.execute('CREATE TABLE IF NOT EXISTS robustness (id TEXT PRIMARY KEY, experiment_id TEXT, result TEXT)');r=db.execute('SELECT result FROM robustness WHERE id=?',(identifier,)).fetchone()
 return explain_result(json.loads(r[0])) if r else None
