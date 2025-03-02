# PeerVault

# File Structures 

```text
PeerVault
├── backend/
│   ├── blueprints/
│   │   ├── __init__.py
│   │   └── ...
│   ├── config/
│   │   ├── config.json
│   │   └── ...
│   ├── objects/
│   │   ├── __init__.py
│   │   └── ...
│   ├── peer_storage/
│   │   └── ...
│   ├── utils/
│   │   ├── __init__.py
│   │   └── ...
│   ├── client.py
│   ├── requirements.txt
│   └── server.py
├── frontend/
│   └── ...
└── README.md
```

## backend/

The [backend/](backend/) directory contains all the server-side code that the user does not directly interact with.

### blueprints/

The blueprints folder contains all the endpoints for the flask API, sorted into files based on their utility. 

Example: all the endpoints for identity check handshakes are contained in [blueprints/identity_check.py](blueprints/identity_check.py).

### config/

The [config/](config/) directory contains all the configuration files for the API, including base URLs, keys, etc. 

### objects/

The [objects/](objects/) directory contains all the custom class definitions for the API. To use a class, import the class like: 

```python 
from objects import MyClass
```

### peer_storage/

The [peer_storage/](peer_storage/) directory contains all the data and metadata pertaining to other peers, including the network graph and files being stored on this peer for other peers. 

### utils/

The [utils/](utils/) directory contains all utility functions that do not specifically relate to a particular class. 

### client.py

The [server.py](server.py) file instantiates the required classes and endpoints for the flask app. 

### requirements.txt

The [requirements.txt](requirements.txt) file contains all the required python dependencies to install via: 

```bash
pip install -r backend/requirements.txt
```
