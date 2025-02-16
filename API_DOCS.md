# Flask API Docs

## Jump to

* [Structure](#structure)
* [Endpoints](#endpoints) 
* [Usage & Examples](#usage--examples)

# Structure 

The flask API is structured like the following: 

* All configuration settings are stored in the [config/](config/) folder
* All blueprints for endpoint functions are defined in the [blueprints/](blueprints/) folder
* All data relating to peers is stored in the [peer-data](peer-data/) folder
* The main program is run with the [main.py](main.py) script

# Endpoints

## /api/get-peer-data 

**Endpoint:** /api/get-peer-data

**Methods:** GET

**Description:** returns the contents of the [all-peers.json](peer-data/all-peers.json) file after applying the supplied filters

### Arguments 

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

### Returns 

| HTTP | Format | Description |
|-------------|--------|--------------------------------------------------------------|
| `200`         | `JSON`   | An array JSON object where each value is a dictionary containing the information for a single peer, and where the returned values match the given criteria. |
| `400`         | -      | Bad request: if the client supplies an unsupported method or some other error in the client's request. |
| `500`         | -      | Server error: if some unexpected error occurs during server-side processing of the request. |


### CURL example

```bash
curl -X GET "http://localhost:8000/get-peer-data?online=1&common_name=jjhealey"
```

# Usage & Examples

## Using the API

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

## Example Queries (cURL)

*Assuming the API is running on the interface "127.0.0.1" (loopback) on port 8000*

**Example: get peer list with optional filters**
```bash
curl -X GET "127.0.0.1:8000/api/get-peer-list?common_name=quentin"
```

```bash
curl -X GET "127.0.0.1:8000/api/get-peer-list?online=0&common_name=quentin"
```