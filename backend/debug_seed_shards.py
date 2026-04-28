import json
from app import create_app
from app.extensions import db
from app.models import AssetBudget, Campus, Laboratory, User
from app.services.db_router_service import campus_db_session

app=create_app()
print('app ok')
with app.app_context():
    raw = app.config.get('CAMPUS_DB_URI_MAP','')
    print('raw map', raw)
    data = json.loads(raw)
    campus_map={int(k):v for k,v in data.items()}
    print('map keys',sorted(campus_map.keys()))
    source_campuses={row.id:row for row in db.session.query(Campus).all()}
    print('source campuses', list(source_campuses.keys()))
    source_labs=db.session.query(Laboratory).all(); print('labs',len(source_labs))
    source_users=db.session.query(User).all(); print('users',len(source_users))
    cid=sorted(campus_map.keys())[0]
    print('try campus',cid)
    with campus_db_session(cid) as session:
        print('entered session')
        c=session.query(Campus).count(); print('count campus',c)
        b=session.query(AssetBudget).count(); print('count budget',b)
        session.commit(); print('commit ok')
print('done')
