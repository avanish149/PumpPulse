# Original conceptual designs. None are manufacturer-verified products.
MODEL_ROWS=[('ILL-3HP','Multistage submersible','submersible',2200,110,100,150,65,220),('ILL-5HP','Deep-lift submersible','submersible',3700,150,130,180,95,220),('DEMO-SURFACE','Surface centrifugal','surface',1500,35,160,220,20,220),('DEMO-BLDC','Solar DC brushless','bldc',900,55,65,100,30,72),('DEMO-HELICAL','Helical rotor / progressive cavity','helical',1200,120,35,55,70,220),('DEMO-BORE','Solar borewell multistage','borewell',3000,180,80,120,100,220),('DEMO-IRRIGATION','Surface irrigation system','irrigation',2200,40,200,300,25,220)]
MODELS={key:dict(id=key,name=name,type=kind,power_W=power,max_head_m=head,nominal_flow_L_min=flow,max_flow_L_min=maxflow,nominal_head_m=nomhead,voltage_V=voltage,current_limit_A=13 if key=='ILL-3HP' else int(power/voltage*1.3+.999),supported_levels=[0,1] if kind in ('surface','irrigation') else [0,.4,.7,1],source='ASSUMED conceptual specifications from the original dashboard; no manufacturer curve',geometry='Conceptual vertical submersible' if kind not in ('surface','irrigation') else 'Conceptual surface installation') for key,name,kind,power,head,flow,maxflow,nomhead,voltage in MODEL_ROWS}

def model_config(key):
 if key not in MODELS:raise ValueError('Unknown pump model')
 m=MODELS[key]
 return {k:m[k] for k in ('power_W','max_head_m','nominal_flow_L_min','max_flow_L_min','voltage_V','current_limit_A','supported_levels')}|dict(model_id=key,pump_type=m['type'])
