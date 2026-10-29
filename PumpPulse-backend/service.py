import json, math, sqlite3, uuid
from contextlib import contextmanager
from pathlib import Path
from datetime import date, datetime, timezone
import pandas as pd
import numpy as np
from engine import run, POLICIES
from models import MODELS, model_config

DEFAULTS=dict(power_W=2200,array_Wp=3600,motor_eff=.85,hydraulic_eff=.60,temperature_retention=.90,controller_eff=.95,wiring_retention=.95,voltage_V=220,current_limit_A=13,nominal_rpm=2900,min_rpm=900,max_head_m=110,nominal_flow_L_min=100,max_flow_L_min=150,pipe_diameter_m=.05,pipe_length_m=60,darcy_factor=.025,drawdown_m=2,intake_depth_m=None,min_submergence_m=5,daily_target_L=36000,speed_wear=.9,dry_wear=2.5,start_wear=.6,start_hour=8,end_hour=18)
# This pilot fixes motor specifications; installation and experimental assumptions are adjustable.
BOUNDS=dict(array_Wp=(400,20000),drawdown_m=(0,40),intake_depth_m=(1,500),min_submergence_m=(.1,30),daily_target_L=(100,200000),pipe_diameter_m=(.01,.2),pipe_length_m=(1,1000),darcy_factor=(.008,.08),motor_eff=(.1,.98),hydraulic_eff=(.1,.9),temperature_retention=(.4,1),controller_eff=(.5,1),wiring_retention=(.5,1),speed_wear=(.01,5),dry_wear=(.01,10),start_wear=(.01,5),start_hour=(0,23),end_hour=(1,24))
DB=Path(__file__).parent/'experiments.sqlite3'
@contextmanager
def connect():
 c=sqlite3.connect(DB)
 try:
  c.execute('CREATE TABLE IF NOT EXISTS experiments (id TEXT PRIMARY KEY, created TEXT, station TEXT, start TEXT, end TEXT, result TEXT)')
  with c:yield c
 finally:c.close()

def validate(payload):
 if not isinstance(payload,dict):raise ValueError('Request must be a JSON object')
 if set(payload)-{'station_id','start','end','config'}:raise ValueError('Unknown request fields')
 station=payload.get('station_id','010203')
 if not isinstance(station,str):raise ValueError('Station ID must be a string, preserving leading zeros')
 for k in ['start','end']:
  v=payload.get(k)
  if not isinstance(v,str):raise ValueError('Dates must be YYYY-MM-DD strings')
  try: parsed=date.fromisoformat(v)
  except ValueError:raise ValueError('Invalid '+k+' date')
  if parsed.isoformat()!=v:raise ValueError('Use YYYY-MM-DD dates')
 config=payload.get('config',{})
 if not isinstance(config,dict):raise ValueError('Config must be an object')
 if set(config)-(set(BOUNDS)|{'model_id'}):raise ValueError('Unknown or fixed motor configuration field: '+', '.join(sorted(set(config)-(set(BOUNDS)|{'model_id'}))))
 c=DEFAULTS.copy();key=config.get('model_id','ILL-3HP')
 if not isinstance(key,str):raise ValueError('Pump model ID must be text')
 c.update(model_config(key))
 for k,v in config.items():
  if k=='model_id':continue
  if k=='intake_depth_m' and v is None:continue
  if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):raise ValueError(k+' must be a finite number')
  lo,hi=BOUNDS[k]
  if not lo<=v<=hi:raise ValueError(k+' outside allowed range '+str((lo,hi)))
  if k in ('start_hour','end_hour') and int(v)!=v:raise ValueError('Schedule hours must be whole numbers')
  c[k]=v
 if c['start_hour']>=c['end_hour']:raise ValueError('Start hour must precede end hour')
 return station,c

def simulate(store,payload,save=True):
 station,c=validate(payload);inputs,meta=store.prepare(station,payload['start'],payload['end'])
 if c['intake_depth_m'] is None:c['intake_depth_m']=float(inputs.groundwater_depth_m_assumed.max()+10.5)
 if c['pump_type'] in ('surface','irrigation') and inputs.groundwater_depth_m_assumed.max()+c['drawdown_m']>7:raise ValueError('Surface pump suction lift exceeds the assumed 7 m limit at this well. Select a submerged model or a shallower compatible well.')
 if c['intake_depth_m']-inputs.groundwater_depth_m_assumed.max()-c['drawdown_m']<c['min_submergence_m']:raise ValueError('Intake does not provide the requested static submergence throughout the period. Increase intake depth or reduce drawdown.')
 results=pd.concat([run(inputs,p,c) for p in range(4)],ignore_index=True)
 num=results.select_dtypes('number')
 if not np.isfinite(num).all().all():raise RuntimeError('Non-finite simulation result')
 if not (results.hydraulic_W<=results.input_W*c['motor_eff']*c['hydraulic_eff']+1e-5).all():raise RuntimeError('Hydraulic energy bound violated')
 results['date_IST']=results.timestamp_IST.dt.strftime('%Y-%m-%d')
 daily=results.groupby(['date_IST','policy']).agg(water_L=('water_L','sum'),energy_kWh=('energy_kWh','sum'),wear_u=('wear_u','sum'),low_water_risk_hours=('low_water_risk_hours','sum'),starts=('starts','sum')).reset_index()
 daily['shortfall_L']=(c['daily_target_L']-daily.water_L).clip(lower=0);daily['target_met_pct']=100*daily.water_L/c['daily_target_L'];daily['meets_full_target']=daily.water_L>=c['daily_target_L'];daily['meets_demo_80pct']=daily.water_L>=.8*c['daily_target_L']
 summary=daily.groupby('policy').agg(days=('date_IST','size'),total_water_L=('water_L','sum'),mean_water_L_day=('water_L','mean'),energy_kWh=('energy_kWh','sum'),wear_u=('wear_u','sum'),full_target_days=('meets_full_target','sum'),demo_80pct_days=('meets_demo_80pct','sum'),low_water_risk_hours=('low_water_risk_hours','sum'),starts=('starts','sum')).reset_index()
 results['timestamp_IST']=results.timestamp_IST.dt.strftime('%Y-%m-%dT%H:%M:%S+05:30')
 inputs['timestamp_IST']=inputs.timestamp_IST.dt.strftime('%Y-%m-%dT%H:%M:%S+05:30')
 records=lambda d:json.loads(d.to_json(orient='records',double_precision=10))
 result=dict(id=str(uuid.uuid4()),created=datetime.now(timezone.utc).isoformat(),version='local-backend-1.0',policies=POLICIES,metadata=meta,config=c,summary=records(summary),daily=records(daily),half_hourly=records(results),inputs=records(inputs),checks=['Finite outputs','Hydraulic power bounded by electrical input and efficiencies','Complete aligned inputs; no extrapolation'])
 if save:
  with connect() as db:db.execute('INSERT INTO experiments VALUES (?,?,?,?,?,?)',(result['id'],result['created'],station,payload['start'],payload['end'],json.dumps(result,allow_nan=False)))
 return result

def history():
 with connect() as db:return [dict(zip(['id','created','station_id','start','end'],r)) for r in db.execute('SELECT id,created,station,start,end FROM experiments ORDER BY created DESC LIMIT 50')]
def load(identifier):
 with connect() as db:r=db.execute('SELECT result FROM experiments WHERE id=?',(identifier,)).fetchone()
 return json.loads(r[0]) if r else None

def state_at(experiment,timestamp,policy):
 if policy not in POLICIES:raise ValueError('Unknown policy')
 if not isinstance(timestamp,str):raise ValueError('Timestamp must be an IST date and time')
 try:t=pd.Timestamp(timestamp)
 except (ValueError,TypeError):raise ValueError('Invalid timestamp')
 if pd.isna(t):raise ValueError('Invalid timestamp')
 if t.tzinfo is None:t=t.tz_localize('Asia/Kolkata')
 else:t=t.tz_convert('Asia/Kolkata')
 if t.minute not in (0,30) or t.second or t.microsecond or t.nanosecond:raise ValueError('Choose an exact half-hour simulation step, such as 19:00 or 19:30 IST')
 key=t.strftime('%Y-%m-%dT%H:%M:%S+05:30')
 row=next((r for r in experiment['half_hourly'] if r['timestamp_IST']==key and r['policy']==policy),None)
 if row is None:raise ValueError('Timestamp is outside this saved replay')
 source=next((r for r in experiment['inputs'] if r['timestamp_IST']==key),None)
 c=experiment['config'];reasons=[]
 if row.get('control_reason'):reasons.append(row['control_reason'])
 elif row['speed_fraction']>0:reasons.append('Running under the saved policy simulation')
 else:
  if not c['start_hour']<=t.hour<c['end_hour']:reasons.append('Outside configured operating window')
  if row['available_W']<=0:reasons.append('No solar power available')
  elif row['available_W']<c['power_W']*.4**3:reasons.append('Insufficient solar power for the lowest supported speed')
  if policy!='P0' and row['submergence_m']<=c['min_submergence_m']:reasons.append('Policy minimum-submergence protection')
  if not reasons:reasons.append('No feasible supported flow/head operating point')
 return dict(experiment_id=experiment['id'],timestamp_IST=key,policy=policy,status='RUNNING' if row['speed_fraction']>0 else 'OFF',reasons=reasons,state=row,input=source,intake_depth_m=c['intake_depth_m'],pumping_depth_m=row['depth_m']+c['drawdown_m']+row['additional_drawdown_m'],rpm=row['speed_fraction']*c['nominal_rpm'])

def station_history():
 with connect() as db:return [dict(zip(['id','created','station_id','start','end'],r)) for r in db.execute('SELECT id,created,station,start,end FROM experiments ORDER BY created DESC')]
