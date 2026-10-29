from pathlib import Path
import os, hashlib
import pandas as pd
import numpy as np

_nearby=Path(__file__).resolve().parent.parent
_default_data=_nearby if (_nearby/'bengaluru_urban_groundwater_hourly_interpolated.csv').is_file() else Path.home()/'Downloads'/'el sem 3'
DATA_DIR=Path(os.environ.get('PUMPPULSE_DATA_DIR',str(_default_data)))
GW_NAME='bengaluru_urban_groundwater_hourly_interpolated.csv'
SOLAR_NAME='POWER_Point_Hourly_20240101_20251201_013d01N_077d62E_LST.csv'
NOTES=['Groundwater timestamps assumed IST; positive levels interpreted as depth below ground. Confirm source timezone and datum.', 'Solar extraction point is a regional proxy, not a sensor at each well. Horizontal irradiance approximates array-plane input.', 'Selected conceptual pump specifications, installation, drawdown and wear are uncalibrated assumptions.', 'Half-hour dynamics start at rest at the selected replay start. Carry state across days; changing start date changes initial conditions.']

class DataStore:
 def __init__(self):
  self.paths=[DATA_DIR/GW_NAME,DATA_DIR/SOLAR_NAME]
  for p in self.paths:
   if not p.is_file():raise ValueError('Missing data file: '+str(p))
  self.gw=pd.read_csv(self.paths[0],dtype={'Station Code':str},low_memory=False)
  self.gw['time']=pd.to_datetime(self.gw['Monitoring Date'],errors='raise')
  self.gw['Ground Water Level']=pd.to_numeric(self.gw['Ground Water Level'],errors='coerce')
  if self.gw.duplicated(['Station Code','time']).any():raise ValueError('Duplicate groundwater station/time records')
  s=pd.read_csv(self.paths[1],skiprows=9)
  s.index=pd.to_datetime(s[['YEAR','MO','DY','HR']].rename(columns={'YEAR':'year','MO':'month','DY':'day','HR':'hour'}))+pd.Timedelta(minutes=30)
  self.solar=s.ALLSKY_SFC_SW_DWN.sort_index()
  if self.solar.index.has_duplicates:raise ValueError('Duplicate solar timestamps')
  self.sources=[{'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in self.paths]
  self.stations=[]
  for key,g in self.gw.groupby('Station Code'):
   a=g.iloc[0];lat=float(a.Latitude);lon=float(a.Longitude)
   self.stations.append(dict(id=key,name='Bengaluru well '+key,latitude=lat,longitude=lon,distance_km=round(111*np.hypot(lat-13.0122,(lon-77.617)*np.cos(np.radians(13))),2),start=str(g.time.min().date()),end=str(g.time.max().date()),first_complete_day=str(g.time.min().ceil('D').date()),last_complete_day=str((g.time.max().floor('D')-pd.Timedelta(days=1)).date()),rows=len(g),observed_anchors=int((g['Data Status']=='Observed at exact hour').sum())))
  self.stations.sort(key=lambda x:x['distance_km'])
 def prepare(self, station, start, end):
  g=self.gw[self.gw['Station Code']==station].sort_values('time').set_index('time')
  if g.empty:raise ValueError('Unknown Bengaluru station')
  a=pd.Timestamp(start);b=pd.Timestamp(end)+pd.Timedelta(days=1)
  if not (1<=(b-a).days<=90):raise ValueError('Select 1 to 90 inclusive days')
  ix=pd.date_range(a,b,freq='30min',inclusive='left')
  if ix[0]<g.index.min() or ix[-1]>g.index.max():raise ValueError('Dates exceed selected well coverage. Use complete days within its range.')
  if not (g.index.to_series().diff().dropna()==pd.Timedelta(hours=1)).all():raise ValueError('Selected well has gaps in supplied hourly timeline')
  w=g['Ground Water Level'].reindex(g.index.union(ix)).sort_index().interpolate(method='time',limit_area='inside').reindex(ix)
  original=g['Ground Water Level'].reindex(ix[ix.minute==0])
  if original.isna().any():raise ValueError('Missing original groundwater levels in requested interval')
  solar=self.solar.reindex(ix,method='ffill',tolerance=pd.Timedelta(minutes=30))
  if not np.isfinite(w).all() or not np.isfinite(solar).all() or w.isna().any() or solar.isna().any() or (w<=0).any() or (w>500).any() or (solar<0).any():raise ValueError('Missing or invalid input values; no extrapolation permitted')
  status=g['Data Status'].reindex(ix).fillna('Additional half-hour interpolation')
  inputs=pd.DataFrame(dict(timestamp_IST=ix,groundwater_depth_m_assumed=w.values,groundwater_provenance=status.values,solar_mean_W_m2=solar.values))
  meta=dict(station=next(s for s in self.stations if s['id']==station),start=start,end=end,days=(b-a).days,timezone='Asia/Kolkata',time_step_minutes=30,observed_hourly_anchors=int((status=='Observed at exact hour').sum()),supplied_hourly_values=len(ix)//2,solar_time_alignment='POWER LST UTC+5 swath shifted +30 min to IST; hourly values held for two half-hour bins, assumed beginning at labelled hour.',solar_units='Hourly Wh/m2 / 1 hour = mean W/m2',sources=self.sources,assumptions=NOTES)
  return inputs,meta
