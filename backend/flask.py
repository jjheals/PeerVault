
from flask import Flask, g, request, current_app
from flask_compress import Compress
from flask_cors import CORS
from gevent.pywsgi import WSGIServer
from configparser import ConfigParser

from blueprints import fi_bp

from objects import Server


# ---- Config ---- #
config:ConfigParser = ConfigParser()
config.read('config/flask.conf')

PORT:int = int(config['flask-config']['PORT'])
FRONTEND_URL:str = config['flask-config']['FRONTEND_URL']


# ---- Flask init ---- #
app = Flask(__name__)
compress = Compress()
compress.init_app(app)

# Init a server obj
tmp_server:Server = Server()

# Tie the server obj to the flask app
app.server = tmp_server

# Add logging before & after requests
@app.before_request
def before_request(): 
    print(f'\n\033[92mINCOMING REQUEST: \033[0m\n\n\tMETHOD: {request.method}\n\tPATH: {request.path}\n\tARGS: {request.args}')
    
@app.after_request
def after_request(response):    
    print(f"\n\033[94mOUTGOING response: \033[0m\n\n\tMETHOD: {request.method} \n\tPATH: {request.path} \n\tSTATUS: {response.status}\n")
    return response 


# ---- Add blueprints ---- #
app.register_blueprint(fi_bp)



# ---- Run ---- #
if __name__ == '__main__': 
    
    # NOTE: use loopback as the interface so the API is not exposed to the network 
    http_server = WSGIServer(('127.0.0.1', PORT), app)
    http_server.serve_forever()