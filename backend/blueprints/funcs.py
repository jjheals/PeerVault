from flask import request, jsonify
from functools import wraps


def require_localhost(f):
    """Wrapper function that restricts the incoming address to localhost only (ipv4/ipv6 loopbacks only)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):

        # Check if the incoming request is coming from a loopback address
        if request.remote_addr not in ['127.0.0.1', '::1']:  

            # Deny access
            return jsonify({"error": "Unauthorized - Local access only"}), 403
        
        # If we make it here, then the incoming IP is a loopback addr
        return f(*args, **kwargs)
    
    return decorated_function