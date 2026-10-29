"""Parameter audit: observable responses, limits and independent output equations."""
import copy
import math
import unittest
import numpy as np
import pandas as pd
import service
from data import DataStore
from engine import run, operating_point
from models import MODELS, model_config
from robustness import challenge

class ParameterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.store=DataStore()
  cls.payload=dict(station_id='010203',start='2025-01-01',end='2025-01-03',config={})
  cls.base=service.simulate(cls.store,cls.payload,save=False)
  cls.responses={}

 def simulate(self,**config):
  return service.simulate(self.store,{**self.payload,'config':config},save=False)

 def test_each_numeric_field_validates_bounds_and_types(self):
  for name,(lo,hi) in service.BOUNDS.items():
   for value in (lo,hi):
    config={name:value}
    if name=='start_hour':config['end_hour']=24
    if name=='end_hour':config['start_hour']=0
    with self.subTest(name=name,value=value):
     self.assertEqual(service.validate({**self.payload,'config':config})[1][name],value)
   for value in (lo-1,hi+1,True,'1',float('nan'),float('inf')):
    with self.subTest(name=name,invalid=repr(value)),self.assertRaises(ValueError):
     service.validate({**self.payload,'config':{name:value}})
   if name!='intake_depth_m':
    with self.subTest(name=name,invalid=None),self.assertRaises(ValueError):
     service.validate({**self.payload,'config':{name:None}})
  for name in ('start_hour','end_hour'):
   with self.assertRaises(ValueError):service.validate({**self.payload,'config':{name:8.5}})

 def test_every_adjustable_numeric_field_has_observable_effect(self):
  cases={
   'array_Wp':(800,6000,{},'energy_kWh'),
   'daily_target_L':(1000,36000,{},'water_L'),
   'drawdown_m':(0,5,{'intake_depth_m':100},'head_m'),
   'intake_depth_m':(80,100,{},'submergence_m'),
   'min_submergence_m':(1,8,{'intake_depth_m':float(self.base['config']['intake_depth_m'])},'water_L'),
   'pipe_diameter_m':(.02,.1,{},'water_L'),
   'pipe_length_m':(10,600,{},'water_L'),
   'darcy_factor':(.008,.08,{},'water_L'),
   'motor_eff':(.2,.95,{},'water_L'),
   'hydraulic_eff':(.15,.85,{},'water_L'),
   'temperature_retention':(.4,1,{},'energy_kWh'),
   'controller_eff':(.5,1,{},'energy_kWh'),
   'wiring_retention':(.5,1,{},'energy_kWh'),
   'speed_wear':(.1,2,{},'speed_wear_u'),
   'dry_wear':(.1,5,{'intake_depth_m':float(self.base['config']['intake_depth_m'])-3},'dry_wear_u'),
   'start_wear':(.1,2,{},'start_wear_u'),
   'start_hour':(6,12,{},'water_L'),
   'end_hour':(12,20,{},'water_L')}
  self.assertEqual(set(cases),set(service.BOUNDS))
  for name,(lo,hi,extra,metric) in cases.items():
   with self.subTest(parameter=name):
    a=self.simulate(**(extra|{name:lo}));b=self.simulate(**(extra|{name:hi}))
    av=sum(x[metric] for x in a['half_hourly']);bv=sum(x[metric] for x in b['half_hourly'])
    self.assertNotAlmostEqual(av,bv,places=5,msg=name+' is inert in its exercising scenario')
    first=next((x,y) for x,y in zip(a['half_hourly'],b['half_hourly']) if abs(x[metric]-y[metric])>1e-7)
    self.responses[name]=dict(low=lo,high=hi,metric=metric,low_total=av,high_total=bv,example=dict(timestamp=first[0]['timestamp_IST'],policy=first[0]['policy'],low=first[0][metric],high=first[1][metric]))

 def test_dates_and_every_station_are_connected(self):
  depths=[]
  for station in self.store.stations:
   if not station['replay_available']:
    self.assertEqual(station['id'],'010317');self.assertEqual(station['rows'],6)
    with self.assertRaises(ValueError):self.store.prepare(station['id'],station['start'],station['start'])
    continue
   day=station['first_complete_day']
   r=service.simulate(self.store,dict(station_id=station['id'],start=day,end=day),save=False)
   self.assertEqual(r['metadata']['station']['id'],station['id'])
   self.assertEqual(len(r['inputs']),48)
   self.assertEqual(len(r['half_hourly']),192)
   depths.append(r['inputs'][0]['groundwater_depth_m_assumed'])
  self.assertGreater(len(set(depths)),1)
  a=service.simulate(self.store,{**self.payload,'end':'2025-01-01'},save=False)
  b=service.simulate(self.store,{**self.payload,'start':'2025-01-02','end':'2025-01-02'},save=False)
  self.assertEqual(len(a['inputs']),48);self.assertEqual(len(self.base['inputs']),144)
  self.assertNotEqual(a['inputs'][0]['timestamp_IST'],b['inputs'][0]['timestamp_IST'])
  self.assertNotEqual(a['inputs'][0]['groundwater_depth_m_assumed'],b['inputs'][0]['groundwater_depth_m_assumed'])

 def test_all_catalogue_models_and_policy_levels(self):
  inputs,_=self.store.prepare('010203','2025-01-01','2025-01-01')
  inputs=inputs.copy();inputs.groundwater_depth_m_assumed=1
  inputs.solar_mean_W_m2=1000  # Controlled shallow/high-sun fixture, not altered source data.
  for key,m in MODELS.items():
   c=service.DEFAULTS|model_config(key)|dict(array_Wp=20000,intake_depth_m=20,drawdown_m=0)
   for policy in range(4):
    with self.subTest(model=key,policy=policy):
     r=run(inputs,policy,c)
     self.assertGreater(r.water_L.sum(),0)
     self.assertTrue(set(r.speed_fraction).issubset(set(m['supported_levels'])))
     self.assertTrue((r.input_W<=m['power_W']+1e-6).all())
     self.assertTrue((r.flow_L_min<=m['nominal_flow_L_min']*r.speed_fraction+1e-6).all())
     self.assertTrue((r.loc[r.speed_fraction>0,'head_m']<=m['max_head_m']*r.loc[r.speed_fraction>0,'speed_fraction']**2+1e-6).all())

 def test_no_water_or_power_when_intake_is_uncovered(self):
  inputs,_=self.store.prepare('010203','2025-01-01','2025-01-01')
  c=self.base['config']|dict(intake_depth_m=1,array_Wp=20000)
  for policy in range(4):
   r=run(inputs,policy,c)
   self.assertEqual(r.water_L.sum(),0);self.assertEqual(r.input_W.sum(),0)

 def test_fixed_motor_limits_bind_when_exercised(self):
  c=self.base['config']|dict(intake_depth_m=100,nominal_flow_L_min=500,max_flow_L_min=500,max_head_m=500)
  normal=operating_point(1,10000,2,0,c)
  for field,value in [('power_W',100),('voltage_V',1),('current_limit_A',.1),('max_flow_L_min',1),('max_head_m',1),('nominal_flow_L_min',1),('min_rpm',3000),('nominal_rpm',500)]:
   with self.subTest(field=field):
    changed=operating_point(1,10000,2,0,c|{field:value})
    self.assertLess(changed[1],normal[1])

 def test_output_equations_and_daily_aggregation(self):
  c=self.base['config']
  for r in self.base['half_hourly']:
   self.assertAlmostEqual(r['available_W'],c['array_Wp']*r['solar_W_m2']/1000*c['temperature_retention']*c['controller_eff']*c['wiring_retention'],places=6)
   self.assertAlmostEqual(r['water_L'],r['flow_L_min']*30,places=6)
   self.assertAlmostEqual(r['energy_kWh'],r['input_W']/2000,places=8)
   velocity=r['flow_L_min']/60000/(math.pi*c['pipe_diameter_m']**2/4)
   head=r['depth_m']+c['drawdown_m']+r['additional_drawdown_m']+c['darcy_factor']*c['pipe_length_m']/c['pipe_diameter_m']*velocity**2/(2*9.81)
   self.assertAlmostEqual(r['head_m'],head,places=6)
   self.assertAlmostEqual(r['hydraulic_W'],1000*9.81*r['flow_L_min']/60000*head,places=6)
   self.assertAlmostEqual(r['submergence_m'],c['intake_depth_m']-r['depth_m']-c['drawdown_m']-r['additional_drawdown_m'],places=6)
   self.assertAlmostEqual(r['wear_u'],r['speed_wear_u']+r['dry_wear_u']+r['start_wear_u'],places=8)
   self.assertAlmostEqual(r['speed_wear_u'],c['speed_wear']*r['speed_fraction']**3*.5,places=8)
   self.assertAlmostEqual(r['start_wear_u'],c['start_wear']*r['starts'],places=8)
   self.assertAlmostEqual(r['dry_wear_u'],c['dry_wear']*r['low_water_risk_hours']*r['speed_fraction'],places=8)
  for row in self.base['daily']:
   steps=[r for r in self.base['half_hourly'] if r['date_IST']==row['date_IST'] and r['policy']==row['policy']]
   for k in ('water_L','energy_kWh','wear_u','starts','low_water_risk_hours'):
    self.assertAlmostEqual(row[k],sum(r[k] for r in steps),places=6)
   self.assertAlmostEqual(row['shortfall_L'],max(0,c['daily_target_L']-row['water_L']),places=6)

 def test_uncertainty_each_parameter_and_seed(self):
  payload=dict(date='2025-01-01',scenarios=10,seed=42,solar_pct=0,groundwater_m=0,wear_pct=0)
  baseline=challenge(self.base,payload,persist=False)
  for field,value in [('scenarios',11),('seed',43),('solar_pct',25),('groundwater_m',2),('wear_pct',40)]:
   with self.subTest(field=field):
    changed=challenge(self.base,payload|{field:value},persist=False)
    if field=='scenarios':self.assertEqual(len(changed['trials']),11)
    elif field=='seed':
     a=challenge(self.base,payload|dict(solar_pct=25),persist=False)
     b=challenge(self.base,payload|dict(solar_pct=25,seed=value),persist=False)
     self.assertNotEqual(a['trials'][0]['solar_multiplier'],b['trials'][0]['solar_multiplier'])
    else:
     key={'solar_pct':'solar_multiplier','groundwater_m':'groundwater_shift_m','wear_pct':'wear_multipliers'}[field]
     self.assertNotEqual(changed['trials'][0][key],baseline['trials'][0][key])
  for field,values in {'scenarios':[9,101,10.5,True],'seed':[-1,2147483648,1.5,True],'solar_pct':[-1,51,None],'groundwater_m':[-1,4.1,None],'wear_pct':[-1,51,None]}.items():
   for value in values:
    with self.subTest(field=field,value=value),self.assertRaises(ValueError):challenge(self.base,payload|{field:value},persist=False)

if __name__=='__main__':unittest.main(verbosity=2)
