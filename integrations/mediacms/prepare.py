"""Create an isolated, localhost-only MediaCMS pilot from inspected upstream source."""
import json,secrets,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PILOT=ROOT/'outputs/mediacms-pilot'
SOURCE=PILOT/'upstream'
EXPECTED='d146be7c3c6828075dfc83719c37819f1b6fbef7'

def prepare():
    revision=subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip()
    if revision!=EXPECTED:raise SystemExit('Upstream revision changed; inspect before preparing.')
    import yaml
    config=yaml.safe_load((SOURCE/'docker-compose.yaml').read_text())
    config.pop('version',None)
    config['name']='course-mediacms-pilot'
    secrets_path=PILOT/'credentials.json'
    if not secrets_path.exists():
        secrets_path.write_text(json.dumps(dict(admin=secrets.token_urlsafe(24),database=secrets.token_urlsafe(24),django=secrets.token_urlsafe(48))),encoding='utf-8')
    credentials=json.loads(secrets_path.read_text())
    for name,service in config['services'].items():
        if name in ('web','migrations','celery_beat','celery_worker'):
            service['volumes']=[f'{SOURCE.as_posix()}:/home/mediacms.io/mediacms/']
            service.setdefault('environment',{}).update(POSTGRES_PASSWORD=credentials['database'],SECRET_KEY=credentials['django'],FRONTEND_HOST='http://127.0.0.1:8770',PORTAL_NAME='课镜视频平台试验')
        if name=='migrations':service['environment']['ADMIN_PASSWORD']=credentials['admin']
        if name=='web':service['ports']=['127.0.0.1:8770:80']
        if name=='db':
            service['volumes']=['pilot-postgres:/var/lib/postgresql/data/']
            service['environment']['POSTGRES_PASSWORD']=credentials['database']
    config['volumes']={'pilot-postgres':{}}
    target=PILOT/'compose.yaml'
    target.write_text(yaml.safe_dump(config,allow_unicode=True,sort_keys=False),encoding='utf-8')
    (PILOT/'provenance.json').write_text(json.dumps({'repository':'https://github.com/mediacms-io/mediacms','commit':revision,'license':'AGPL-3.0','image':'mediacms/mediacms:latest','image_digest':'pending pull; must record before claiming reproducibility','status':'prepared, runtime verification pending'},indent=2),encoding='utf-8')
    print('Prepared isolated pilot on 127.0.0.1:8770. Credentials retained only under ignored outputs/.')

if __name__=='__main__':prepare()
