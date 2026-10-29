import unittest
from data import DataStore
from service import simulate
from robustness import challenge,explain_result

class DiagnosticTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.store=DataStore()
 def test_screenshot_configuration_is_demand_limited(self):
  exp=simulate(self.store,dict(station_id='010203',start='2025-01-01',end='2025-01-01',config=dict(controller_eff=.5,intake_depth_m=21.305)),save=False)
  r=challenge(exp,dict(date='2025-01-01',scenarios=30,seed=42),persist=False)
  self.assertEqual(r['no_feasible_scenarios'],30)
  self.assertEqual(r['diagnostics']['demand_only_no_winner_scenarios'],30)
  self.assertEqual(r['diagnostics']['matching_output_scenarios'],30)
  for s in r['summary']:
   self.assertEqual(s['demand_failures'],30);self.assertEqual(s['risk_failures'],0)
   self.assertAlmostEqual(s['worst_shortfall_L'],5375.2132901747245,places=5)
 def test_low_demand_produces_qualified_winners(self):
  exp=simulate(self.store,dict(station_id='010203',start='2025-01-01',end='2025-01-01',config=dict(daily_target_L=1000)),save=False)
  r=challenge(exp,dict(date='2025-01-01',scenarios=10,seed=42),persist=False)
  self.assertEqual(r['no_feasible_scenarios'],0)
  s=next(s for s in r['summary'] if s['policy']=='P3');self.assertEqual(s['wins'],10);self.assertEqual(s['demand_failures'],0);self.assertEqual(s['risk_failures'],0)
 def test_failure_explanation_distinguishes_both_criteria(self):
  outcomes=[dict(policy='P'+str(i),water_L=100,wear_u=1,shortfall_L=short,low_water_risk_hours=risk) for i,(short,risk) in enumerate([(10,1),(0,1),(10,0),(0,0)])]
  r=dict(trials=[dict(winner='P3',outcomes=outcomes)],summary=[dict(policy='P'+str(i)) for i in range(4)])
  explain_result(r)
  self.assertEqual(r['summary'][0]['both_failures'],1);self.assertEqual(r['summary'][1]['demand_failures'],0);self.assertEqual(r['summary'][2]['risk_failures'],0);self.assertEqual(r['summary'][3]['both_failures'],0)
  self.assertEqual(r['trials'][0]['winner'],'P3')
if __name__=='__main__':unittest.main()
