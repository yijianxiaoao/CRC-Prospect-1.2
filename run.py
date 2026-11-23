# -*- coding: utf-8 -*-
"""
Research Platform for Behavioral Mechanisms of Colonoscopy Screening in High-Risk Colorectal Cancer Populations —— Start entry.

    python run.py                 # Start the service (automatic database and table creation, with simulated data generation when the database is empty)
    python run.py --port 5012
Direct reading and writing of data MySQL (default database name crc_prospect).
"""
import argparse
import os

from app import create_app

app = create_app()


def ensure_data() -> None:
    """Automatically generate a simulated cohort when the database is empty; the platform is ready to use immediately. """
    from app.db import Session
    from app.models import Subject
    from app.service.seed import generate_cohort

    count = Session().query(Subject).count()
    Session.remove()
    if count == 0:
        print('The database is empty. Generating a simulated study cohort...')
        import config
        result = generate_cohort(config.DEFAULT_N)
        print('  Generated %d study participants' % result['subject'])
    else:
        print('Database contains %d study participants' % count)


def main() -> None:
    parser = argparse.ArgumentParser(description='Research Platform for Behavioral Mechanisms of Colorectal Cancer Screening')
    parser.add_argument('--host', default=os.getenv('HOST', '127.0.0.1'))
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '5012')))
    args = parser.parse_args()

    ensure_data()

    import config
    print('=' * 60)
    print('  %s' % config.RESEARCH_TITLE)
    print('  MySQL database: %s' % config.DB_NAME)
    print('  URL: http://%s:%d' % (args.host, args.port))
    print('  Administrator account: admin (The initial password is 1264383161)')
    print('=' * 60)
    if os.getenv('CRC_DEV_SERVER', '0').lower() in ('1', 'true', 'yes'):
        app.run(host=args.host, port=args.port, debug=False)
        return
    try:
        from waitress import serve
        print('  Production WSGI: waitress (Set CRC_DEV_SERVER=1 to use the Flask development server)')
        serve(app, host=args.host, port=args.port, threads=8)
    except ImportError:
        print('  Warning: waitress is not installed, using the Flask development server temporarily; install requirements.txt in production')
        app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()
