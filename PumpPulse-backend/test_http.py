import json, urllib.request, urllib.error, csv, io
BASE='http://127.0.0.1:8765'
def request(path,payload=None,headers=None):
 body=None if payload is None else json.dumps(payload).encode()
 req=urllib.request.Request(BASE+path,data=body,headers=headers or ({'Content-Type':'application/json'} if body else {}))
 with urllib.request.urlopen(req,timeout=30) as r:return r.status,r.read(),dict(r.headers)
assert json.loads(request('/api/health')[1])['status']=='ok'
assert len(json.loads(request('/api/stations')[1])['stations'])==36
for path in ['/','/demo','/app.js','/style.css','/api/config']:
 assert request(path)[0]==200
for payload in [dict(station_id='010203',start='2025-01-01',end='2025-01-01',config={'array_Wp':-1}),dict(station_id='010203',start='2024-01-01',end='2024-01-02')]:
 try:request('/api/simulations',payload);raise AssertionError('Invalid request accepted')
 except urllib.error.HTTPError as e:assert e.code==422
for headers in [{'Origin':'http://untrusted.example'},{'Host':'untrusted.example'}]:
 try:request('/api/health',headers=headers);raise AssertionError('Nonlocal origin accepted')
 except urllib.error.HTTPError as e:assert e.code==403
items=json.loads(request('/api/experiments')[1])['experiments'];assert items,'Run an experiment from the dashboard first'
item=json.loads(request('/api/experiments/'+items[0]['id'])[1]);assert len(item['summary']) in (3,4)
for table in ['summary','daily','half_hourly','inputs']:
 status,body,headers=request('/api/experiments/'+item['id']+'/'+table+'.csv')
 rows=list(csv.DictReader(io.StringIO(body.decode('utf-8'))));assert len(rows)==len(item[table]);assert 'attachment' in headers['Content-Disposition']
print('HTTP checks passed: health, 36 wells, config, frontend assets, invalid requests, local-origin checks, saved-run retrieval, four CSV exports.')

status,body,_=request('/api/experiments/'+item['id']+'/state?timestamp=2025-01-01T19%3A00&policy=P2')
state=json.loads(body);assert state['timestamp_IST']=='2025-01-01T19:00:00+05:30';assert state['state']['depth_m']==state['input']['groundwater_depth_m_assumed'];assert state['status']=='OFF'
try:request('/api/experiments/'+item['id']+'/state?timestamp=2025-01-01T19%3A15&policy=P2');raise AssertionError('Unrecorded step accepted')
except urllib.error.HTTPError as e:assert e.code==422
assert request('/timeline.js')[0]==200
print('Timeline HTTP checks passed: exact source-depth match, 19:00 OFF state, 19:15 rejection, timeline asset.')

for asset in ['/twin3d.js','/robustness.js','/vendor/three.min.js']:
 assert request(asset)[0]==200
status,body,_=request('/api/robustness',dict(experiment_id=item['id'],date='2025-01-01',scenarios=10,seed=42,solar_pct=15,groundwater_m=1,wear_pct=30))
unc=json.loads(body);assert status==201 and len(unc['summary'])==4;assert len(unc['trials'])==10
assert sum(x['wins'] for x in unc['summary'])+unc['no_feasible_scenarios']==10
assert json.loads(request('/api/robustness/'+unc['id'])[1])==unc
print('3D assets and persisted uncertainty API checks passed.')

status,body,_=request('/api/recommendations',dict(experiment_id=item['id'],date='2025-01-01'));plan=json.loads(body)
assert status==201 and len(plan['schedule'])==24 and len(plan['trace'])==48
assert json.loads(request('/api/recommendations/'+plan['id'])[1])==plan
assert len(list(csv.DictReader(io.StringIO(request('/api/recommendations/'+plan['id']+'/schedule.csv')[1].decode()))))==24
assert request('/recommendations.js')[0]==200
print('Hourly plan HTTP checks passed: generation, persistence, 24-row CSV and frontend asset.')
