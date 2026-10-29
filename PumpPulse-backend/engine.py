import pandas as pd
import numpy as np

POLICIES={'P0':'Fixed schedule','P1':'Threshold protection','P2':'Wear-aware rule','P3':'Demand-aware rule'}
def hydraulic(q,depth,draw,C):
 v=q/60000/(np.pi*C['pipe_diameter_m']**2/4)
 return depth+draw+C['darcy_factor']*C['pipe_length_m']/C['pipe_diameter_m']*v*v/(2*9.81)

def operating_point(speed,available,depth,draw,C):
 if C.get('pump_type') in ('surface','irrigation') and depth+draw>7:return 0.,0.,0.
 if speed*C['nominal_rpm']<C['min_rpm']:speed=0
 power=min(C['power_W']*speed**3,available,C['voltage_V']*C['current_limit_A']);budget=power*C['motor_eff']*C['hydraulic_eff'];lo=0.;hi=min(C['max_flow_L_min'],C['nominal_flow_L_min']*speed)
 for _ in range(35):
  q=(lo+hi)/2;h=hydraulic(q,depth,draw,C)
  if 1000*9.81*q/60000*h<=budget and h<=C['max_head_m']*speed**2:lo=q
  else:hi=q
 q=lo
 if q<.001:q=power=speed=0.
 return speed,q,power

def run(inputs,policy,C,initial=None):
 initial=initial or {};dt=.5;dr=float(initial.get('drawdown_m',0));prev=float(initial.get('previous_speed',0));records=[];day=inputs.timestamp_IST.iloc[0].date() if len(inputs) else None;delivered=float(initial.get('daily_delivered_L',0))
 for row in inputs.itertuples(index=False):
  tm=row.timestamp_IST
  if day!=tm.date():day=tm.date();delivered=0.
  depth=row.groundwater_depth_m_assumed;sub=C['intake_depth_m']-depth-C['drawdown_m']-dr;av=C['array_Wp']*row.solar_mean_W_m2/1000*C['temperature_retention']*C['controller_eff']*C['wiring_retention'];on=C['start_hour']<=tm.hour<C['end_hour'];minimum=C['min_submergence_m'];reason=''
  if policy==3:
   remaining=max(0,C['daily_target_L']-delivered)
   if not on:sp=q=power=0.;reason='Outside configured operating window'
   elif remaining<=0:sp=q=power=0.;reason='Daily water target already reached'
   elif sub<=minimum:sp=q=power=0.;reason='Policy minimum-submergence protection'
   else:
    options=[]
    for speed in [v for v in C.get('supported_levels',[0,.4,.7,1]) if v>0]:
     if C['power_W']*speed**3<=av+1e-9:
      point=operating_point(speed,av,depth,C['drawdown_m']+dr,C)
      if point[1]>0:options.append(point)
    hours=max(dt,C['end_hour']-(tm.hour+tm.minute/60))
    # Delivery feedback with 40% planning reserve; uses only the current input, not future records.
    required_rate=remaining/hours*1.4
    point=next((x for x in options if x[1]*60>=required_rate),options[-1] if options else (0.,0.,0.))
    sp,q,power=point;reason='Lowest supported speed meeting remaining-delivery rate with 40% planning reserve' if options and q*60>=required_rate else 'Highest feasible speed to reduce remaining demand' if options else 'No feasible supported flow/head operating point'
  else:
   cmd=(1 if on else 0) if policy==0 else (1 if on and sub>minimum else 0) if policy==1 else (.7 if on and sub>minimum+1 else .4 if on and sub>minimum else 0)
   cap=min(cmd,np.cbrt(max(0,av/C['power_W'])));sp=next((x for x in sorted(C.get('supported_levels',[0,.4,.7,1]),reverse=True) if x<=cap+1e-9),0)
   sp,q,power=operating_point(sp,av,depth,C['drawdown_m']+dr,C)
  if not sp and not reason:
   reason='Outside configured operating window' if not on else 'Policy minimum-submergence protection' if policy!=0 and sub<=minimum else 'No feasible supported speed under sunlight and head limits'
  if sp and not reason:reason='Running under '+POLICIES['P'+str(policy)]
  head=hydraulic(q,depth,C['drawdown_m']+dr,C);ph=1000*9.81*q/60000*head;dry=int(sp>0 and sub<minimum);start=int(sp>0 and prev==0);sw=C['speed_wear']*sp**3*dt;dw=C['dry_wear']*dry*sp*dt;stw=C['start_wear']*start;water=q*60*dt;delivered+=water
  records.append(dict(timestamp_IST=tm,policy='P'+str(policy),depth_m=depth,submergence_m=sub,additional_drawdown_m=dr,solar_W_m2=row.solar_mean_W_m2,available_W=av,speed_fraction=sp,flow_L_min=q,head_m=head,input_W=power,hydraulic_W=ph,water_L=water,energy_kWh=power/1000*dt,wear_u=sw+dw+stw,speed_wear_u=sw,dry_wear_u=dw,start_wear_u=stw,low_water_risk_hours=dry*dt,starts=start,daily_delivered_L=delivered,remaining_demand_L=max(0,C['daily_target_L']-delivered),control_reason=reason))
  decay=.8**dt;dr=dr*decay+6*sp*(1-decay);prev=sp
 return pd.DataFrame(records)
