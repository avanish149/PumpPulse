import json, math, tempfile, unittest, urllib.request, urllib.error
from pathlib import Path
from unittest.mock import patch
import pandas as pd
import service
from data import DataStore

class BackendTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.store=DataStore()
  cls.payload=dict(station_id='010203',start='2025-01-01',end='2025-03-20',config={})
  cls.result=service.simulate(cls.store,cls.payload,save=False)
 def test_matches_original_pilot(self):
  expected={'P0':(44215.925962,75,646.94360),'P1':(42347.245119,75,446.45280),'P2':(34912.198159,45,235.38345)}
  for row in self.result['summary']:
   if row['policy'] not in expected:continue
   water,days,wear=expected[row['policy']]
   self.assertAlmostEqual(row['mean_water_L_day'],water,places=4);self.assertEqual(row['full_target_days'],days);self.assertAlmostEqual(row['wear_u'],wear,places=4)
 def test_time_and_provenance(self):
  r=self.result;self.assertEqual(len(r['inputs']),3792);self.assertEqual(len(r['half_hourly']),15168)
  self.assertEqual(r['inputs'][0]['timestamp_IST'],'2025-01-01T00:00:00+05:30')
  self.assertTrue(any('half-hour' in x['groundwater_provenance'] for x in r['inputs']))
  self.assertEqual(r['inputs'][1]['solar_mean_W_m2'],r['inputs'][2]['solar_mean_W_m2'])
 def test_energy_and_no_solar(self):
  for row in self.result['half_hourly']:
   self.assertLessEqual(row['hydraulic_W'],row['input_W']*.85*.60+1e-5)
   self.assertLessEqual(row['input_W'],row['available_W']+1e-6)
   if row['available_W']==0:self.assertEqual(row['water_L'],0)
 def test_changing_config_changes_result(self):
  short=dict(station_id='010203',start='2025-01-01',end='2025-01-03',config={'array_Wp':800})
  low=service.simulate(self.store,short,save=False)
  short['config']['array_Wp']=4500;high=service.simulate(self.store,short,save=False)
  self.assertGreater(high['summary'][0]['total_water_L'],low['summary'][0]['total_water_L'])
  short['config']['daily_target_L']=200000;changed=service.simulate(self.store,short,save=False)
  self.assertEqual(changed['summary'][0]['full_target_days'],0)
 def test_validation_and_coverage(self):
  cases=[{'array_Wp':float('nan')},{'array_Wp':-1},{'start_hour':18,'end_hour':8},{'power_W':900},{'daily_target_L':True},{'intake_depth_m':2}]
  for c in cases:
   with self.subTest(c=c),self.assertRaises(ValueError):service.simulate(self.store,{**self.payload,'config':c},save=False)
  for fields in [dict(station_id='nope'),dict(start='2024-01-01'),dict(end='2025-03-21'),dict(start='2025-01-02',end='2025-01-01')]:
   with self.subTest(fields=fields),self.assertRaises(ValueError):service.simulate(self.store,{**self.payload,**fields},save=False)
 def test_timeline_exact_depth_and_night_state(self):
  r=service.state_at(self.result,'2025-01-01T19:00','P2')
  source=self.store.gw[(self.store.gw['Station Code']=='010203')&(self.store.gw.time==pd.Timestamp('2025-01-01 19:00'))].iloc[0]
  self.assertAlmostEqual(r['state']['depth_m'],float(source['Ground Water Level']),places=8)
  self.assertEqual(r['status'],'OFF');self.assertEqual(r['rpm'],0)
  self.assertIn('Outside configured operating window',r['reasons'])
  self.assertEqual(r['input']['timestamp_IST'],r['timestamp_IST'])
  day=service.state_at(self.result,'2025-01-01T12:00','P0');self.assertEqual(day['status'],'RUNNING');self.assertGreater(day['state']['flow_L_min'],0)
  self.assertEqual(service.state_at(self.result,'2025-01-01T13:30Z','P2')['timestamp_IST'],r['timestamp_IST'])
 def test_timeline_rejects_invented_steps(self):
  for time,policy in [('2025-01-01T19:15','P2'),('2025-01-01T19:00:01','P2'),('2025-05-01T19:00','P2'),('NaT','P2'),('2025-01-01T19:00','P4')]:
   with self.subTest(time=time,policy=policy),self.assertRaises(ValueError):service.state_at(self.result,time,policy)
 def test_demand_policy_stops_after_target_and_resets_daily(self):
  out=service.simulate(self.store,dict(station_id='010203',start='2025-01-01',end='2025-01-02',config={'daily_target_L':1000}),save=False)
  rows=[x for x in out['half_hourly'] if x['policy']=='P3']
  for day in ['2025-01-01','2025-01-02']:
   r=[x for x in rows if x['date_IST']==day];self.assertGreater(sum(x['water_L'] for x in r),999)
   reached=False
   for x in r:
    if reached:self.assertEqual(x['water_L'],0)
    if x['daily_delivered_L']>=1000:reached=True
  self.assertEqual(sum(x['low_water_risk_hours'] for x in rows),0)
 def test_uncertainty_reproducibility_and_zero_ranges(self):
  from robustness import challenge
  payload=dict(date='2025-01-01',scenarios=10,seed=42,solar_pct=0,groundwater_m=0,wear_pct=0)
  a=challenge(self.result,payload,persist=False);b=challenge(self.result,payload,persist=False)
  self.assertEqual(a['trials'],b['trials']);self.assertEqual(a['summary'],b['summary'])
  self.assertEqual(sum(s['wins'] for s in a['summary'])+a['no_feasible_scenarios'],10)
  self.assertTrue(all(t['outcomes']==a['trials'][0]['outcomes'] for t in a['trials']))
  for invalid in [dict(scenarios=0),dict(seed=-1),dict(solar_pct=float('nan')),dict(date='2024-01-01')]:
   with self.assertRaises(ValueError):challenge(self.result,{**payload,**invalid},persist=False)
 def test_p3_does_not_use_future_solar(self):
  from engine import run
  inputs,_=self.store.prepare('010203','2025-01-01','2025-01-02');c=self.result['config'].copy()
  a=run(inputs,3,c);changed=inputs.copy();changed.loc[changed.timestamp_IST>=pd.Timestamp('2025-01-02'),'solar_mean_W_m2']=0
  b=run(changed,3,c);pd.testing.assert_frame_equal(a.iloc[:48],b.iloc[:48])
 def test_uncertainty_persistence(self):
  from robustness import challenge,load_challenge
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp,patch.object(service,'DB',Path(tmp)/'test.sqlite3'):
   r=challenge(self.result,dict(date='2025-01-01',scenarios=10,seed=7))
   self.assertEqual(load_challenge(r['id']),r)
 def test_hourly_recommendation_continuity(self):
  from recommendations import recommend
  r=recommend(self.result,dict(date='2025-01-01'),persist=False)
  self.assertEqual(len(r['schedule']),24);self.assertEqual(len(r['trace']),48)
  self.assertAlmostEqual(sum(x['expected_water_L'] for x in r['schedule']),r['summary']['water_L'],places=6)
  for a,b in zip(r['trace'],r['trace'][1:]):
   expected=a['additional_drawdown_m']*.8**.5+6*a['speed_fraction']*(1-.8**.5)
   self.assertAlmostEqual(b['additional_drawdown_m'],expected,places=7)
   self.assertAlmostEqual(b['daily_delivered_L'],a['daily_delivered_L']+b['water_L'],places=7)
  for h in r['schedule']:
   if int(h['hour_IST'][:2])<8 or int(h['hour_IST'][:2])>=18:self.assertEqual(h['action'],'OFF')
  self.assertEqual(r['summary']['low_water_risk_hours'],0)
  with self.assertRaises(ValueError):recommend(self.result,dict(date='2024-01-01'),persist=False)
 def test_hourly_recommendation_target_stop(self):
  from recommendations import recommend
  import copy
  exp=copy.deepcopy(self.result);exp['config']['daily_target_L']=1000
  r=recommend(exp,dict(date='2025-01-01'),persist=False);hit=False
  for step in r['trace']:
   if hit:self.assertEqual(step['water_L'],0)
   hit=hit or step['daily_delivered_L']>=1000
  self.assertTrue(hit)
 def test_saved_experiment_roundtrip(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp,patch.object(service,'DB',Path(tmp)/'test.sqlite3'):
   out=service.simulate(self.store,dict(station_id='010203',start='2025-01-01',end='2025-01-01'),save=True)
   self.assertEqual(service.load(out['id']),out);self.assertEqual(service.history()[0]['id'],out['id'])

if __name__=='__main__':unittest.main(verbosity=2)
