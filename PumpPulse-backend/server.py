from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from pathlib import Path
import argparse, csv, io, json, mimetypes, threading, traceback
from data import DataStore, NOTES
from models import MODELS
from service import DEFAULTS, BOUNDS, simulate, history, load, state_at, station_history

from robustness import challenge, load_challenge
from recommendations import recommend, load_plan

ROOT=Path(__file__).resolve().parent
slots=threading.BoundedSemaphore(2)
class Handler(BaseHTTPRequestHandler):
 def send(self,status,data,kind='application/json; charset=utf-8',attachment=None):
  if kind.startswith('application/json'):data=json.dumps(data,allow_nan=False).encode()
  elif isinstance(data,str):data=data.encode('utf-8')
  self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(data)));self.send_header('X-Content-Type-Options','nosniff');self.send_header('Cache-Control','no-store')
  if attachment:self.send_header('Content-Disposition','attachment; filename="'+attachment+'"')
  self.end_headers();self.wfile.write(data)
 def allowed(self):
  host=self.headers.get('Host','');good={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
  origin=self.headers.get('Origin')
  navigation=self.command=='GET' and self.headers.get('Sec-Fetch-Mode')=='navigate' and self.headers.get('Sec-Fetch-Dest')=='document' and urlsplit(self.path).path in ('/','/demo')
  if host not in good or (origin and origin not in {'http://'+x for x in good}) or (self.headers.get('Sec-Fetch-Site')=='cross-site' and not navigation):
   self.send(403,{'error':'Use the local dashboard origin'});return False
  return True
 def do_GET(self):
  if not self.allowed():return
  u=urlsplit(self.path);p=u.path
  try:
   if p=='/api/health':return self.send(200,dict(status='ok',version='local-backend-1.0',stations=len(self.server.store.stations)))
   if p=='/api/stations':return self.send(200,dict(stations=self.server.store.stations,assumptions=NOTES))
   if p=='/api/models':return self.send(200,dict(models=list(MODELS.values())))
   if p=='/api/capabilities':return self.send(200,dict(live_sensors=False,weather_forecast=False,bearing_recordings=False,historical_replay=True,hourly_planner=True,pump_models=len(MODELS)))
   if p=='/api/fleet':
    latest={}
    for entry in station_history():
     if entry['station_id'] not in latest:
      saved=load(entry['id']);latest[entry['station_id']]=dict(experiment_id=entry['id'],created=entry['created'],model_id=saved['config'].get('model_id','ILL-3HP'),start=entry['start'],end=entry['end'],summary=saved['summary'])
    return self.send(200,dict(stations=[dict(s,latest_experiment=latest.get(s['id'])) for s in self.server.store.stations]))
   if p=='/api/config':return self.send(200,dict(defaults=DEFAULTS,bounds=BOUNDS,pump='Illustrative 3 HP submersible'))
   if p=='/api/experiments':return self.send(200,dict(experiments=history()))
   if p.startswith('/api/recommendations/'):
    parts=p.strip('/').split('/');saved=load_plan(parts[2]) if len(parts) in (3,4) else None
    if saved is None:return self.send(404,{'error':'Hourly plan not found'})
    if len(parts)==3:return self.send(200,saved)
    if parts[3]!='schedule.csv':return self.send(404,{'error':'Unknown plan export'})
    buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=list(saved['schedule'][0]));w.writeheader();w.writerows(saved['schedule'])
    return self.send(200,buf.getvalue(),'text/csv; charset=utf-8','hourly-plan-'+saved['date']+'.csv')
   if p.startswith('/api/robustness/'):
    saved=load_challenge(p.rsplit('/',1)[-1])
    return self.send(200,saved) if saved else self.send(404,{'error':'Uncertainty experiment not found'})
   if p.startswith('/api/experiments/'):
    parts=p.strip('/').split('/');item=load(parts[2]) if len(parts) in (3,4) else None
    if item is None:return self.send(404,{'error':'Experiment not found'})
    if len(parts)==3:return self.send(200,item)
    if parts[3]=='state':
     query=parse_qs(u.query)
     try:return self.send(200,state_at(item,query.get('timestamp',[''])[0],query.get('policy',['P2'])[0]))
     except ValueError as e:return self.send(422,{'error':str(e)})
    table=parts[3].removesuffix('.csv')
    if table not in ('summary','daily','half_hourly','inputs'):return self.send(404,{'error':'Unknown export'})
    rows=item[table];buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return self.send(200,buf.getvalue(),'text/csv; charset=utf-8',table+'-'+parts[2]+'.csv')
   files={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/unified.js':'unified.js','/timeline.js':'timeline.js','/twin3d.js':'twin3d.js','/robustness.js':'robustness.js','/recommendations.js':'recommendations.js','/vendor/three.min.js':'vendor/three.min.js','/style.css':'style.css','/demo':'original-dashboard.html'}
   if p in files:
    f=ROOT/'static'/files[p];kind=mimetypes.guess_type(str(f))[0] or 'application/octet-stream'
    return self.send(200,f.read_bytes(),kind+'; charset=utf-8')
   self.send(404,{'error':'Route not found'})
  except Exception:
   traceback.print_exc();self.send(500,{'error':'Local server error. See terminal for details.'})
 def do_POST(self):
  if not self.allowed():return
  if self.path not in ('/api/simulations','/api/robustness','/api/recommendations'):return self.send(404,{'error':'Route not found'})
  if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send(415,{'error':'Send application/json'})
  try:n=int(self.headers.get('Content-Length','0'))
  except ValueError:return self.send(400,{'error':'Invalid content length'})
  if not 1<=n<=65536:return self.send(413,{'error':'Request must be 1 to 65536 bytes'})
  if not slots.acquire(blocking=False):return self.send(429,{'error':'Two runs already active; try again shortly'})
  try:
   payload=json.loads(self.rfile.read(n))
   if self.path in ('/api/robustness','/api/recommendations'):
    if not isinstance(payload,dict):raise ValueError('Request must be an object')
    item=load(payload.get('experiment_id',''))
    if item is None:raise ValueError('Saved experiment not found')
    result=challenge(item,payload) if self.path=='/api/robustness' else recommend(item,payload)
   else:result=simulate(self.server.store,payload)
   self.send(201,result)
  except (ValueError,TypeError,KeyError) as e:self.send(422,{'error':str(e)})
  except Exception:
   traceback.print_exc();self.send(500,{'error':'Simulation failed. See terminal for details.'})
  finally:slots.release()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--open',action='store_true');args=parser.parse_args()
 if args.open:
  try:
   import urllib.request,webbrowser
   with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/api/health',timeout=2) as response:health=json.load(response)
   if health.get('status')=='ok' and health.get('version','').startswith('local-backend-'):
    print('PumpPulse is already running. Opening the project.',flush=True)
    webbrowser.open(f'http://127.0.0.1:{args.port}/demo#home');return
  except (OSError,ValueError):pass
 store=DataStore();server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.store=store
 print(f'PumpPulse local backend: http://127.0.0.1:{args.port}',flush=True)
 print('Data files loaded. Press Ctrl+C to stop.',flush=True)
 if args.open:
  import webbrowser
  webbrowser.open(f'http://127.0.0.1:{args.port}/demo#backend')
 try:server.serve_forever()
 except KeyboardInterrupt:pass
 finally:server.server_close()
if __name__=='__main__':main()
