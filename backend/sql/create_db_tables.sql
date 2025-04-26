
/* Table for storing info about each peer */
CREATE TABLE Peer(
    peer_pub_key TEXT PRIMARY KEY,
    online BOOLEAN NOT NULL,
    most_recent_ip TEXT NOT NULL,
    common_name TEXT NOT NULL,
    mac_last_four TEXT NOT NULL,
    CHECK (most_recent_ip GLOB '[0-9]*.[0-9]*.[0-9]*.[0-9]*')
);


/* Table for storing the peers and filenames of files we're currently storing for other peers */
CREATE TABLE CurrentlyStoringFor(
    peer_pub_key TEXT NOT NULL,
    filename TEXT NOT NULL,
    size_gb REAL NOT NULL,
    sha256 TEXT NOT NULL,
    store_date TEXT NOT NULL,   -- Must be in [YYYY-MM-DD] format 
    CHECK (store_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    PRIMARY KEY (peer_pub_key, filename),
    FOREIGN KEY (peer_pub_key) REFERENCES Peer(peer_pub_key)
);


/* Table for storing the peers and filenames of files we're currently storing with other peers */
CREATE TABLE CurrentlyStoringWith(
    peer_pub_key TEXT NOT NULL,
    filename TEXT NOT NULL,
    size_gb REAL NOT NULL,
    sha256 TEXT NOT NULL,
    b64_nonce TEXT NOT NULL,
    store_date TEXT NOT NULL,   -- Must be in [YYYY-MM-DD] format 
    CHECK (store_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    PRIMARY KEY (peer_pub_key, filename),
    FOREIGN KEY (peer_pub_key) REFERENCES Peer(peer_pub_key)
);


/* Table for storing the names and dates of files that were previously shared with a peer */ 
CREATE TABLE PreviouslySharedWith(
    peer_pub_key TEXT NOT NULL,
    direction TEXT NOT NULL,        -- Must be either [incoming | outgoing]
    filename TEXT NOT NULL,
    size_gb REAL NOT NULL,
    sha256 TEXT NOT NULL,
    share_date TEXT NOT NULL,       -- Must be in [YYYY-MM-DD] format 
    CHECK (share_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    CHECK (direction = 'incoming' OR direction = 'outgoing'),
    PRIMARY KEY (peer_pub_key, filename, direction),
    FOREIGN KEY (peer_pub_key) REFERENCES Peer(peer_pub_key)
);


/* Table for pending requests that have not yet been processed */
CREATE TABLE PendingRequests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL,       -- Must be either [incoming | outgoing]
    request_type TEXT NOT NULL,    -- Must be one of [store | share | delete]
    peer_pub_key TEXT NOT NULL,
    filename TEXT NOT NULL,
    size_gb REAL NOT NULL,
    sha256 TEXT NOT NULL,
    accepted BOOLEAN DEFAULT NULL,     -- Whether or not the request has been accepted (for outgoing reqs, the peer accepts; for incoming reqs, we accept)
    request_date TEXT NOT NULL,        -- Must be in [YYYY-MM-DD] format 
    CHECK (request_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    CHECK (direction = 'incoming' OR direction = 'outgoing'),
    CHECK (request_type IN ('store', 'share', 'delete', 'retrieve')),
    FOREIGN KEY (peer_pub_key) REFERENCES Peer(peer_pub_key)
);


/* Table for completed requests that have been processed or declined (basically a copy of PendingRequests) */
CREATE TABLE CompletedRequests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL,       -- Must be either [incoming | outgoing]
    request_type TEXT NOT NULL,    -- Must be one of [store | share | delete]
    peer_pub_key TEXT NOT NULL,
    filename TEXT NOT NULL,
    size_gb REAL NOT NULL,
    sha256 TEXT NOT NULL,
    accepted BOOLEAN DEFAULT NULL,     -- Whether or not the request has been accepted (for outgoing reqs, the peer accepts; for incoming reqs, we accept)
    request_date TEXT NOT NULL,        -- Must be in [YYYY-MM-DD] format 
    CHECK (request_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    CHECK (direction = 'incoming' OR direction = 'outgoing'),
    CHECK (request_type IN ('store', 'share', 'delete', 'retrieve')),
    FOREIGN KEY (peer_pub_key) REFERENCES Peer(peer_pub_key)
)