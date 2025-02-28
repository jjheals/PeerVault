
from flask import Blueprint, jsonify, g, request, abort, current_app
import json 
import pandas as pd
from objects import Server


# ---- Config & init ---- #
# Create blueprint
p2p_bp:Blueprint = Blueprint('p2p_interaction', __name__)


@p2p_bp.route('/api/share-file', methods=['POST'])
def share_file(): 

    # Get server obj from current app
    server:Server = current_app.server
    
    raise NotImplementedError


@p2p_bp.route('/api/store-file', methods=['POST'])
def store_file(): 
    raise NotImplementedError




