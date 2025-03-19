# Backend Documentation

This is the documentation for the backend program. There are three main sections: 

* [Setup](#setup): how to set up the backend program and install the required python packages.
* [Flask app](#flask-app): handles the specific endpoints for communication between the react & flask apps via localhost AND the network communication between multiple peers on the network.
* [Server Class](#server-class): contains the functions that execute specific requests on behalf of the flask app. 

# Setup 

*The following setup is required to run the backend program.*

### Optional: create and activate a virtual environment

*Linux/Unix/MacOS*

*Create venv*
```bash 
# Create venv
python -m venv venv

# Activate venv
source venv/bin/activate
```

*Windows*

```bash 
# Create venv
python -m venv venv

# Activate venv (cmd prompt)
venv\Scripts\activate

# Activate venv (PowerShell)
venv\Scripts\Activate.ps1
```

If you receive a security error, first run:
```bash
# (PowerShell)
Set-ExecutionPolicy Unrestricted -Scope Process
```

Then re-run:
```bash
# (PowerShell)
venv\Scripts\Activate.ps1
```

### Required: install the required packages

*Linux/Unix/MacOS/Windows*
```bash 
python -m pip install -r refs/requirements.txt
```

# Flask App

The backend API endpoints are managed by the [flask application](./flask.py). All of the endpoints are separated into Blueprints and defined in the relevant blueprint file in [blueprints/](./blueprints/).

## Jump to

* [Structure](#structure)
* [Endpoints](#endpoints) 
* [Usage & Examples](#usage--examples)

## Structure 

The flask API is structured like the following: 

* All configuration settings are stored in the [config/](config/) folder
* All blueprints for endpoint functions are defined in the [blueprints/](blueprints/) folder
* All data relating to peers is stored in the [peer-data](peer-data/) folder
* The flask application is run with the [flask.py](./flask.py) script

**Separating communication for React -> Flask (via localhost) and External Peer -> Local Peer (via network)**

* The endpoints for communications between the React app and local flask application: 

    *  Defined in [blueprints/frontend-interaction.py](./blueprints/frontend_interaction.py) 
    * Each endpoint is wrapped in a decorator function that restricts the incoming IP to a loopback address (localhost)
    * URI prefix is "/ui/*" 
    * These endpoints return unecrypted responses

* The endpoints for communications between External Peers and the Local Peer:
    * Defined in [blueprints/p2p-interaction.py](./blueprints/p2p_interaction.py)
    * URI prefix is "/api/*" 
    * These endpoints return encrypted responses

## Endpoints

### /ui/get-peer-list 

**Endpoint:** /ui/get-peer-list

**Methods:** GET

**Description:** returns the contents of the [all-peers.json](peer-data/all-peers.json) file after applying the supplied filters

#### Arguments 

| Argument            | Type     | Description                                              |
|---------------------|---------|----------------------------------------------------------|
| `online`           | `int`   | Filter by if the peers are active or not (`0` or `1`).  |
| `allowed_to_receive` | `int`   | Filter by the status of `allowed_to_receive` (`-1`, `0`, or `1`). |
| `public_key`       | `str`   | Filter by public key.                                   |
| `most_recent_ip`   | `str`   | Filter by the most recently known IP for peers.        |
| `common_name`      | `str`   | Filter by common name.                                  |
| `mac_last_four`    | `str`   | Filter by the last four characters of the MAC address. |

**Notes:**
- All arguments are optional.
- All arguments are filtered by exact matches.
- All provided arguments are applied as **AND** clauses, meaning only peers that match **all** given arguments will be returned.
- Arguments that are not provided, `None`, empty, or do not match the expected type will be ignored.

#### Returns 

| HTTP | Format | Description |
|-------------|--------|--------------------------------------------------------------|
| `200`         | `JSON`   | An array JSON object where each value is a dictionary containing the information for a single peer, and where the returned values match the given criteria. |
| `400`         | -      | Bad request: if the client supplies an unsupported method or some other error in the client's request. |
| `403` | - | Unauthorized: request came from an address that is not a loopback address (not via localhost) |
| `500`         | -      | Server error: if some unexpected error occurs during server-side processing of the request. |


#### CURL example

```bash
curl -X GET "http://localhost:8000/ui/get-peer-list?online=1&common_name=jjhealey"
```

### /ui/get-stored-with-info

**Endpoint:** /ui-get-stored-with-info

**Methods:** GET

**Description:** returns the info for all files that the user is currently storing with other peers (i.e. the peers that are storing files on behalf of this user).

#### Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `online` | `int` | Filter by if the peers are active or not (`0` or `1`).  |
| `allowed_to_receive` | `int` | Filter by the status of `allowed_to_receive` (`-1`, `0`, or `1`). |
| `public_key` | `str` | Filter by public key. |
| `most_recent_ip` | `str` | Filter by the most recently known IP for peers. |
| `common_name` | `str` | Filter by common name. |
| `mac_last_four` | `str` | Filter by the last four characters of the MAC address. |

#### Returns 

| HTTP | Format | Description |
|------|--------|-------------|
| `200` | `JSON`   | a dict with two keys ['matched_peers', 'matched_files'] where 'matched_peers' is a list of dicts containing the info for each individual peer that matched at least one file, and 'matched_files' is a list of dicts containing the metadata for each of the individual matched files. |
| `400` | - | Bad request: if the client supplies an unsupported method or some other error in the client's request. |
| `403` | - | Unauthorized: request came from an address that is not a loopback address (not via localhost) |
| `500` | - | Server error: if some unexpected error occurs during server-side processing of the request. |

### /ui/whoami

**Endpoint:** /ui/whoami

**Methods:** GET

**Description:** returns all info about this user account (i.e. info stored in the [identity.conf](config/identity.conf) file plus the user's public key and peer storage path).

#### Arguments 

*Takes no arguments.*

#### Returns 

| HTTP | Format | Description |
|------|--------|-------------|
| `200` | `dict` | A JSON object with all the information about this user account with the following keys: ['pub_key', 'common_name', 'mac', 'ip']. |
| `403` | - | Unauthorized if the request comes from a non-loopback address (not localhost). | 
| `500` | - | If there is some internal error processing the request. |

### /ui/signup

**Endpoint:** /ui/signup

**Methods:** POST

**Description:** endpoint to create a new account. Checks if an account already exists, updates the identity config file with the new given info, hashes the given password and stores it in the enc config. 

#### Request Body

The request body should look like: 
```json
{
    "common_name": "<new common name>",
    "peer_storage_path": "<some filepath>",
    "allocated_storage": <int, size in gb>,
    "passphrase": "<some super secure passphrase>"
}
```

#### Returns 

| HTTP | Format | Description | 
|------|--------|-------------|
| `200` | `JSON` | A JSON object that contains the info for the newly submitted and accepted request. |
| `400` | - | If the request fails to supply the required data. |
| `403` | - | If the request comes from a non-loopback address (not localhost). |
| `409` | - | (conflict) If the user already has an account created. | 
| `500` | - | If there is some error in processing the request. | 

### /ui/init-application

**Endpoint:** /ui/init-application

**Methods:** POST

**Description:** endpoint to initialize the application and provide a passphrase. 

### Request Body 

The request body should look like: 
```json
{
    "passphrase": "<super secure passphrase>"
}
```

### Returns 

| HTTP | Format | Description | 
|------|--------|-------------|
| `200` | `JSON` | A JSON object that contains a "message": "success" if the passphrase is correct. | 
| `400` | - | If the request fails to supply the required data. |
| `403` | - | If the request comes from a non-loopback addresss (not localhost) **OR** if the given passphrase is wrong. | 
| `500` | - | If there is some error in processing the request. | 


## Usage & Examples

### Using the API

**To run the API, first install the required dependencies**

*Optional: create a virtual environment:* 
```bash
# Linux/Unix/MacOS/Windows
python -m venv venv
```

*Optional: (if created a venv) active the virtual environment:*
```bash
# Linux/Unix/MacOS 
source venv/bin/activate
```

```bash
# Windows
venv\Scripts\activate
```

*Required: install python dependencies using pip:*
```bash
# Linux/Unix/MacOS/Windows
python -m pip install -r requirements.txt
```

**Now run the API script:**

```bash
# Linux/Unix/MacOS/Windows
python main.py
```

This will start the API on the interface "127.0.0.1" on port 8000.

**Optional: change the port for the API (not recommended)**

1. Open the [flask configuration file](config/flask.conf)
```bash
# Linux/Unix/MacOS
nano config/flask.conf
```

2. Find the line: 
```txt
PORT = 8000
```

3. Change the port number to your desired value:
```txt
PORT = <NEW-INTEGER>
```

### Example Queries (cURL)

*Assuming the API is running on the interface "127.0.0.1" (loopback) on port 8000*

**Example: get peer list with optional filters**
```bash
curl -X GET "127.0.0.1:8000/ui/get-peer-list?common_name=quentin"
```

```bash
curl -X GET "127.0.0.1:8000/ui/get-peer-list?online=0&common_name=quentin"
```


# Server Class
This document is the documentation for the server 

Codes - each packet sent to eachother will have a code for the first 3 bytes execpt when exchangeing public keys 

handshake message layout 
    code        -all
    public key  -all
    mac address
    common name

share message layout 
    code        -all
    public key  -all
    

