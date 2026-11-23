import requests,time
s=requests.Session(); s.get('http://127.0.0.1:5033/__typography_login?next=/')
for path in ['/api/overview','/api/subjects','/api/scenarios','/api/biases','/api/risk','/api/constructs','/api/mechanism','/api/sem','/api/probit','/api/forest','/api/psychometrics','/api/qc','/api/audit?action=']:
 t=time.perf_counter(); r=s.get('http://127.0.0.1:5033'+path,timeout=180); print(path,r.status_code,round(time.perf_counter()-t,2))
