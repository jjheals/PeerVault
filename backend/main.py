
# NOTE: a Server obj is created and added to the app (app.server) by the /ui/init-application/ endpoint,
# so this endpoint MUST be used BEFORE any p2p communication takes place, because it relies on the given
# passphrase to load the keys  

from flask import Flask, g, request
from flask_compress import Compress
from flask_cors import CORS
from gevent.pywsgi import WSGIServer
from configparser import ConfigParser
import os 

# Blueprints
from blueprints import fi_bp, fe_p2p_bp

# Custom objs & util funcs
from utils import now, load_configs, setup_logger
from objects import DatabaseConnection


# ---- Load configs ---- #
print(f'\033[0m[{now()}] \033[94mLoading configurations')

configs:dict[str, ConfigParser] = load_configs('config/')

# Extract attrs from the flask config 
PORT:int = int(configs['flask']['flask-config']['PORT'])
FRONTEND_URL:str = configs['flask']['flask-config']['FRONTEND_URL']


# ---- Flask init ---- #
app = Flask(__name__)
compress = Compress()
compress.init_app(app)

# Init CORS 
print(f'\033[0m[{now()}] \033[94mConfiguring CORS\033[0m')
CORS(
    app, 
    origins=[FRONTEND_URL, 'http://localhost:3000'],
    allow_headers=['Content-Type'],
    supports_credentials=True
)  

# Set strict slashes to False to allow paths with trailing "/" 
app.url_map.strict_slashes = False

# Add all the configs to the app so they are accessible in the blueprints
app.flask_config = configs['flask']
app.enc_config = configs['encryption']
app.network_config = configs['network']
app.identity_config = configs['identity']

# Init a logger and add to the app 
app.logger = setup_logger(
    os.path.join(configs['flask']['paths']['LOGS_DIR'], 'flask.log'),
    'flask_logger'
)

# Create a DB connection and add to the app
app.db_connection = DatabaseConnection(
    configs['flask']['paths']['DB_PATH'],
    log_filepath=os.path.join(configs['flask']['paths']['LOGS_DIR'], 'flask-database.log'),
    logger_name='flask_database_logger'
)

# NOTE: init app.server as None to start, and it is changed via the /ui/init-application endpoint
app.server = None

# Add logging before & after requests
@app.before_request
def before_request(): 
    app.logger.info(f'Incoming Request - [ ADDRESS: {request.remote_addr} | METHOD: {request.method} | PATH: {request.path} {f"| ARGS: {request.args} " if request.method == "GET" else ""}]')
    
@app.after_request
def after_request(response):    
    app.logger.info(f'Outgoing Response - [ ADDRESS: {request.remote_addr} | METHOD: {request.method} | PATH: {request.path} | STATUS: {response.status} ]')
    return response 


# ---- Add blueprints ---- #
print(f'\033[0m[{now()}] \033[94mRegistering blueprints\033[0m')

app.register_blueprint(fi_bp)       # Frontend interaction
app.register_blueprint(fe_p2p_bp)   # Frontend P2P requests


# ---- Run ---- #
if __name__ == '__main__': 

    # Run on the interface specified in the network config so it is limited to that IP and not all
    # network interfaces
    app.logger.info('Flask app running.')
    print(f'\033[0m[{now()}] \033[92mFlask app running\033[0m')
    http_server = WSGIServer(('0.0.0.0', PORT), app)
    http_server.serve_forever()