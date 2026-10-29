import json, uuid
from datetime import datetime, timezone
import pandas as pd
from engine import run, POLICIES
from service import connect

def ending_state(frame):
 last=frame.iloc[-1];decay=.8**.5
 return dict(drawdown_m=float(last.additional_drawdown_m*decay+6*last.speed_fraction*(1-decay)),previous_speed=float(last.speed_fraction),daily_delivered_L=float(last.daily_delivered_L))

def recommend(experiment,payload,persist=True):
 if not isinstance(payload,dict) or set(payload)-{'experiment_id','date'}:raise ValueError('Use experiment_id and date')
 date=payload.get('date');source=[r for r in experiment['inputs'] if r['timestamp_IST'][:10]==date]
 if len(source)!=48:raise ValueError('Choose a complete day within the saved experiment')
 inputs=pd.DataFrame(source);inputs['timestamp_IST']=pd.to_datetime(inputs.timestamp_IST);c=experiment['config'];initial={};warm_policy='P3' if any(r['policy']=='P3' for r in experiment['summary']) else 'P1'
 before=[r for r in experiment['half_hourly'] if r['policy']==warm_policy and r['timestamp_IST'][:10]<date]
 if before:
  last=before[-1];decay=.8**.5;initial=dict(drawdown_m=last['additional_drawdown_m']*decay+6*last['speed_fraction']*(1-decay),previous_speed=last['speed_fraction'])
 initial['daily_delivered_L']=0.;state=initial.copy();executed=[];decisions=[];hourly=[];pref={'P3':0,'P2':1,'P1':2,'P0':3}
 for hour in range(24):
  remaining=inputs.iloc[hour*2:];candidates=[];frames={}
  for p in POLICIES:
   f=run(remaining,int(p[1:]),c,state);frames[p]=f;water=float(f.water_L.sum());wear=float(f.wear_u.sum());risk=float(f.low_water_risk_hours.sum());short=max(0,c['daily_target_L']-state['daily_delivered_L']-water)
   candidates.append(dict(policy=p,projected_shortfall_L=short,projected_wear_u=wear,projected_low_water_hours=risk,projected_energy_kWh=float(f.energy_kWh.sum()),feasible=short<=1e-6 and risk==0))
  fulfilled=state['daily_delivered_L']>=c['daily_target_L'];feasible=[x for x in candidates if x['feasible']]
  if fulfilled:chosen=next(x for x in candidates if x['policy']=='P3');reason='Daily target already reached; stop pumping.'
  elif feasible:
   chosen=min(feasible,key=lambda x:(x['projected_wear_u'],x['projected_energy_kWh'],pref[x['policy']]));reason='Lowest projected remaining stress among policies meeting full demand with zero low-water-risk hours.'
  else:
   chosen=min(candidates,key=lambda x:(x['projected_low_water_hours']>0,x['projected_low_water_hours'],x['projected_shortfall_L'],x['projected_wear_u'],pref[x['policy']]));reason='No policy projects full demand with zero low-water risk. Prioritise protection, then minimise projected shortfall.'
  p=chosen['policy'];step=frames[p].iloc[:2].copy();step['selected_policy']=p;state=ending_state(step);executed.append(step);running=bool((step.speed_fraction>0).any())
  if not running:reason='OFF: '+str(step.control_reason.iloc[0])+'. '+('' if fulfilled else reason)
  stamps=[r.strftime('%Y-%m-%dT%H:%M:%S+05:30') for r in step.timestamp_IST]
  hourly.append(dict(hour_IST=f'{hour:02d}:00',action='RUN' if running else 'OFF',recommended_policy=p if running else 'OFF',governing_policy=p,speed_first_half_pct=float(step.speed_fraction.iloc[0]*100),speed_second_half_pct=float(step.speed_fraction.iloc[1]*100),expected_water_L=float(step.water_L.sum()),expected_energy_kWh=float(step.energy_kWh.sum()),relative_stress_u=float(step.wear_u.sum()),dataset_depth_start_m=float(step.depth_m.iloc[0]),minimum_submergence_m=float(step.submergence_m.min()),cumulative_water_L=state['daily_delivered_L'],remaining_demand_L=max(0,c['daily_target_L']-state['daily_delivered_L']),projected_shortfall_at_decision_L=chosen['projected_shortfall_L'],reason=reason))
  decisions.append(dict(hour_IST=f'{hour:02d}:00',selected=p,candidates=candidates,executed_timestamps=stamps))
 trace=pd.concat(executed,ignore_index=True);trace['timestamp_IST']=trace.timestamp_IST.dt.strftime('%Y-%m-%dT%H:%M:%S+05:30');water=float(trace.water_L.sum())
 result=dict(id=str(uuid.uuid4()),experiment_id=experiment['id'],date=date,created=datetime.now(timezone.utc).isoformat(),version='hourly-plan-1.1',engine_version='local-backend-1.1',schedule=hourly,trace=json.loads(trace.to_json(orient='records',double_precision=10)),decisions=decisions,summary=dict(water_L=water,shortfall_L=max(0,c['daily_target_L']-water),full_target_met=water>=c['daily_target_L'],energy_kWh=float(trace.energy_kWh.sum()),wear_u=float(trace.wear_u.sum()),low_water_risk_hours=float(trace.low_water_risk_hours.sum()),policy_switches=sum(hourly[i]['governing_policy']!=hourly[i-1]['governing_policy'] for i in range(1,24))),initial_state=initial,warm_start_policy=warm_policy if before else 'At rest at replay start',config=c,sources=experiment['metadata']['sources'],method='Historical look-ahead recommendation, not a weather forecast or proven global optimum. At each hour, compare four remaining-day policy rollouts from the same actual simulated state. Execute only the next hour, then replan. Full target and zero low-water-risk hours are required for feasibility; minimise remaining stress among feasible candidates. If none are feasible, prioritise zero risk then shortfall. After the target is met, stop. Depth, drawdown, starts and delivered water carry through switches. The day begins from the saved baseline policy midnight state, not from a previously recommended day. Hourly speed columns distinguish the two half-hour steps.')
 if persist:
  with connect() as db:
   db.execute('CREATE TABLE IF NOT EXISTS recommendations (id TEXT PRIMARY KEY, experiment_id TEXT, result TEXT)');db.execute('INSERT INTO recommendations VALUES (?,?,?)',(result['id'],experiment['id'],json.dumps(result,allow_nan=False)))
 return result

def load_plan(identifier):
 with connect() as db:
  db.execute('CREATE TABLE IF NOT EXISTS recommendations (id TEXT PRIMARY KEY, experiment_id TEXT, result TEXT)');r=db.execute('SELECT result FROM recommendations WHERE id=?',(identifier,)).fetchone()
 return json.loads(r[0]) if r else None
