
# NOTE: a Server obj is created and added to the app (app.server) by the /ui/init-application/ endpoint,
# so this endpoint MUST be used BEFORE any p2p communication takes place, because it relies on the given
# passphrase to load the keys  

# Third-party imports
from flask import Flask, g, request
from flask_compress import Compress
from flask_cors import CORS
from gevent.pywsgi import WSGIServer
from configparser import ConfigParser

# Blueprints
from blueprints import fi_bp, fe_p2p_bp

# Custom objs & util funcs
from utils import  now
from objects import DatabaseConnection


# ---- Load configs ---- #
print(f'\033[0m[{now()}] \033[94mLoading configurations')

# Flask config
flask_config:ConfigParser = ConfigParser()
flask_config.read('config/flask.conf')

# Encryption config 
enc_config:ConfigParser = ConfigParser()
enc_config.read('config/encryption.conf')

# Multicast config 
network_config:ConfigParser = ConfigParser()
network_config.read('config/network.conf')

# Identity config 
identity_config:ConfigParser = ConfigParser()
identity_config.read('config/identity.conf')

# Extract attrs from the flask config 
PORT:int = int(flask_config['flask-config']['PORT'])
FRONTEND_URL:str = flask_config['flask-config']['FRONTEND_URL']


# ---- Flask init ---- #
app = Flask(__name__)
compress = Compress()
compress.init_app(app)

# Init CORS 
print(f'\033[0m[{now()}] \033[94mConfiguring CORS\033[0m')
CORS(
    app, 
    origins=['http://localhost:3000'],
    allow_headers=['Content-Type'],
    supports_credentials=True
)  

# Add all the configs to the app so they are accessible in the blueprints
app.flask_config = flask_config
app.enc_config = enc_config
app.network_config = network_config
app.identity_config = identity_config

# Create a DB connection and add to the app
app.db_connection = DatabaseConnection(flask_config['paths']['DB_PATH'])

# NOTE: init app.server as None to start, and it is changed via the /ui/init-application endpoint
app.server = None

# Add logging before & after requests
@app.before_request
def before_request(): 
    print(f'\n\033[92mINCOMING REQUEST: \033[0m\n\n\tADDRESS: {request.remote_addr}\033[0m\n\tMETHOD: {request.method}\n\tPATH: {request.path}\n\tARGS: {request.args}')
    
@app.after_request
def after_request(response):    
    print(f"\n\033[94mOUTGOING response: \033[0m\n\n\tMETHOD: {request.method} \n\tPATH: {request.path} \n\tSTATUS: {response.status}\n")
    return response 


# ---- Add blueprints ---- #
print(f'\033[0m[{now()}] \033[94mRegistering blueprints\033[0m')

app.register_blueprint(fi_bp)       # Frontend interaction
app.register_blueprint(fe_p2p_bp)   # Frontend P2P requests


# ---- Run ---- #
if __name__ == '__main__': 

    # Run on the interface specified in the network config so it is limited to that IP and not all
    # network interfaces
    print(f'\033[0m[{now()}] \033[92mFlask app running')
    http_server = WSGIServer((network_config['network']['IFACE'], PORT), app)
    http_server.serve_forever()