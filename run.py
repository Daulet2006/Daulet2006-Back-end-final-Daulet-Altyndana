# run.py
from app import create_app, db
from flask.cli import with_appcontext
import logging

app = create_app()
logging.basicConfig(level=logging.DEBUG)

@app.cli.command('init-db')
@with_appcontext
def init_db():
    db.create_all()
    print('Database initialized.')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
