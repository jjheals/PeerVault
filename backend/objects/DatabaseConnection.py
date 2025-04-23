import sqlite3 as sql
import pandas as pd
import logging 
import os 
import datetime as dt 

from utils import setup_logger


class DatabaseConnection: 
    
    cxn:sql.Connection      # Connection to the DB 
    cursor:sql.Cursor       # Cursor for the DB
    logger:logging.Logger   # Logger
    
    
    def __init__(self, db_filepath:str, log_filepath:str='logs/database.log'): 
        
        # Create log dir if it doesn't exist
        os.makedirs(os.path.dirname(log_filepath), exist_ok=True)
        
        # Init logger first to log success/errors
        self.logger = setup_logger(
            log_filepath,
            'database_logger'
        )
        
        # Try to make a cxn to the DB
        try: 
            
            # Check if the DB directory exists to avoid errors if we have to create it
            if not os.path.exists(os.path.dirname(db_filepath)): 
                
                # Create the dir 
                self.logger.info(f'Creating directory for DB "{os.path.dirname(db_filepath)}".')
                os.makedirs(os.path.dirname(db_filepath))

                # Since the dir didn't exist, then the file didn't exist either
                self.logger.info(f'Creating DB file at "{db_filepath}".')
                
        
            # DB file already exists, so we will connect to that
            else: 
                self.logger.info(f'Connecting to existing database at "{log_filepath}".')
                    
            # Init SQLite cxn and cursor and enable FK contraints 
            self.cxn = sql.connect(db_filepath) 
            self.cursor = self.cxn.cursor()
            self.cxn.execute("PRAGMA foreign_keys = ON")
            
        # Handle exceptions
        except Exception as e:
            self.logger.critical(f'DatabaseConnection.__init__() - there was an error connecting to the database. {e.__class__}: {e}') 
            
            # Init cxn and cursor as None
            self.cxn = None
            self.cursor = None
            
    
    # ---- General util functions ---- #
    
    def get_table_columns(self, table_name:str) -> list[str]: 
        """Returns the columns for the given table name."""
        
        # Execute query
        self.cursor.execute(f'PRAGMA table_info({table_name})')
        
        # Return results
        return [c[1] for c in self.cursor.fetchall()]
    

    def table_as_df(self, table_name:str) -> pd.DataFrame: 
        """Returns the given table as a DataFrame."""
        
        # Execute select query for the table
        self.cursor.execute(f'SELECT * FROM {table_name}')
        
        # Fetch all results and create a df, and return
        return pd.DataFrame(
            self.cursor.fetchall(),
            columns=self.get_table_columns(table_name)
        )
    
    
    # ---- Functions for the PendingRequests table ---- #
    
    def new_pending_request(self, direction:str, request_type:str, peer_pub_key:str, filename:str, size_gb:float,
                            sha256:str) -> None: 
        """Creates a new entry in either the [PendingIncomingRequest] or [PendingOutgoingRequest] table 
        with the given information. The given [direction] must be either 'incoming' or 'outgoing', other
        values will raise a ValueError. NOTE: assumes the request date is TODAY."""
        
        # Make sure a valid direction is given 
        direction = direction.lower() 
        if not direction in ['incoming', 'outgoing']: 
            raise ValueError(f'Given direction "{direction}" is not valid - must be one of "incoming" or "outgoing"')
        
        # Create query (NOTE: 7 placeholders)
        query:str = f"""
            INSERT INTO PendingRequests(direction, request_type, peer_pub_key, filename, size_gb, sha256, request_date) 
            VALUES(?, ?, ?, ?, ?, ?, ?) 
        """
        
        try: 
            # Execute the query
            self.cursor.execute(
                query,
                (
                    direction,
                    request_type,
                    peer_pub_key,
                    filename,
                    size_gb,
                    sha256,
                    dt.datetime.now().strftime('%Y-%m-%d')
                )
            )
            
            # Commit changes 
            self.cxn.commit() 
        
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in new_pending_request - {e.__class__}: {e}')
            raise Exception('An error occured while inserting the new pending request.')
    

    def remove_pending_request(self, req_id:int, direction:str) -> None: 
        """Removes the row for the given [req_id] (request ID) from either the [PendingIncomingRequest] or 
        [PendingOutgoingRequest] table. The given [direction] must be either 'incoming' or 'outgoing', other
        values will raise a ValueError."""
        
        return NotImplementedError
    
    
    # ---- Functions for the [Peer] table ---- # 
    
    def new_peer(self, peer_pub_key:str, online:bool, most_recent_ip:str, common_name:str, 
                 mac_last_four:str) -> None: 
        """Creates a new row in the [Peer] table for the given peer info."""
        
        # Construct the query (NOTE: 5 placeholders)
        query:str = """
            INSERT INTO Peer(peer_pub_key, online, most_recent_ip, common_name, mac_last_four)
            VALUES (?, ?, ?, ?, ?)
        """
        
        try: 
            # Execute the query
            self.cursor.execute(
                query,
                (
                    peer_pub_key,
                    online,
                    most_recent_ip,
                    common_name,
                    mac_last_four
                )
            )
            
            # Commit changes
            self.cxn.commit() 
            
        # Handle exceptions
        # Integrity error means a peer w/ this public key already exists
        except sql.IntegrityError as e: 
            self.logger.error(f'in new_peer() - Integrity Error: {e}')
            return
        
        # Other exceptions
        except Exception as e: 
            self.logger.error(f'in new_peer() - {e.__class__}: {e}')
            return 

    
    def peer_info_from_pub_key(self, peer_pub_key:str) -> dict: 
        """Returns a dict containing the information for the peer with the given public key."""
        
        # Get the columns for the "Peer" table
        table_cols:list[str] = self.get_table_columns('Peer') 
        
        # Construct the query
        query:str = f"SELECT {','.join(table_cols)} FROM Peer WHERE peer_pub_key = ?"
        
        try: 
            # Exceute the query
            self.cursor.execute(
                query, 
                (peer_pub_key,)
            )

            # Fetch results
            results:tuple = self.cursor.fetchone()

            # Convert results to a dict and return 
            if results and len(results) > 0: 
                return {
                    c : r 
                    for c,r in zip(table_cols, results)
                } 
                
            # Return None if no results
            else: return None
            
        # Handle exceptions    
        except Exception as e: 
            self.logger.error(f'in peer_info_from_pub_key() - {e.__class__}: {e}')
            return None
        
    
    def update_peer_status(self, peer_pub_key:str, new_ip:str, new_online_status:bool=True) -> None: 
        """Updates the online status and most recent IP for the given peer."""
        
        # Construct query 
        query:str = """
            UPDATE Peer 
            SET most_recent_ip = ?, online = ?
            WHERE peer_pub_key = ?
        """
        
        try: 
            # Execute the query
            self.cursor.execute(
                query,
                (new_ip, new_online_status, peer_pub_key)
            )
            
            # Commit changes
            self.cxn.commit() 
            
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in update_peer_status() - {e.__class__}: {e}')
            return 
        
    
    def check_peer_exists(self, peer_pub_key:str) -> bool: 
        """Checks if a peer with the given public key exists."""
        
        try: 
            # Execute the query
            self.cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM Peer WHERE peer_pub_key = ?)",
                (peer_pub_key,)
            )
            
            # Fetch results
            return self.cursor.fetchone()[0] == 1
        
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in check_peer_exists() - {e.__class__}: {e}')
            return 
        
    
    def pub_key_from_ip(self, ip:str) -> str|None: 
        """Returns the public key for the peer that currently (or most recently) has/had the given IP."""
        
        # Construct query
        query:str = "SELECT peer_pub_key FROM Peer WHERE most_recent_ip = ?"
        
        try: 
            # Execute query
            self.cursor.execute(
                query,
                (ip,)
            )
            
            # Fetch results
            results:tuple = self.cursor.fetchone()
            
            if results: return results[0]
            else: return None
            
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in check_peer_exists() - {e.__class__}: {e}')
            return None
        
           
    # ---- Functions for the [Currently* and PreviouslySharedWith] tables ---- #
    
    def new_shared_file(self, peer_pub_key:str, direction:str, filename:str, size_gb:float, 
                        sha256:str) -> None: 
        """Creates a new entry in the [PreviouslySharedWith] table with the given info. The [direction] 
        must be either 'incoming' or 'outgoing', other values will raise a ValueError. NOTE: assumes 
        the share date is TODAY."""
        
        # Check that the given direction is valid
        direction = direction.lower()
        if not direction in ['incoming', 'outgoing']: 
            raise ValueError(f'Given direction "{direction}" is not valid - must be one of "incoming" or "outgoing"')
        
        # Construct the query (NOTE: 6 placeholders)
        query:str = """
            INSERT INTO PreviouslySharedWith(peer_pub_key, direction, filename, size_gb, sha256, share_date) 
            VALUES(?, ?, ?, ?, ?, ?)
        """
        
        try: 
            # Execute the query
            self.cursor.execute(
                query,
                (
                    peer_pub_key,
                    direction,
                    filename,
                    size_gb,
                    sha256,
                    dt.datetime.now().strftime('%Y-%m-%d')
                )
            )
            
            # Commit changes
            self.cxn.commit() 
        
        # Handle exceptions
        # Integrity Error means a key constraint was violated
        except sql.IntegrityError as e: 
            self.logger.error(f'in new_shared_file() - Integrity Error: {e}')
            return 
        
        # Other exceptions
        except Exception as e: 
            self.logger.error(f'in new_shared_file() - {e.__class__}: {e}')
            return 
    
    
    def new_storing_with_file(self, peer_pub_key:str, filename:str, size_gb:float, sha256:str, 
                              b64_nonce:str) -> None: 
        """Creates a new entry in the [CurrentlyStoringWith] table with the given info. NOTE: assumes
        the store date is TODAY."""
        
        # Construct the query (NOTE: 6 placeholders)
        query:str = """
            INSERT INTO CurrentlyStoringWith(peer_pub_key, filename, size_gb, sha256, b64_nonce, store_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        try: 
            # Exceute the query
            self.cursor.execute(
                query,
                (
                    peer_pub_key,
                    filename,
                    size_gb,
                    sha256,
                    b64_nonce,
                    dt.datetime.now().strftime('%Y-%m-%d')
                )
            )
            
            # Commit changes
            self.cxn.commit()
            
        # Handle exceptions
        # Integrity Error means a key constraint was violated
        except sql.IntegrityError as e: 
            self.logger.error(f'in new_storing_with_file() - Integrity Error: {e}')
            return 
        
        # Other exceptions
        except Exception as e: 
            self.logger.error(f'in new_storing_with_file() - {e.__class__}: {e}')
            return 
    
    
    def new_storing_for_file(self, peer_pub_key:str, filename:str, size_gb:float, sha256:str) -> None:
        """Creates a new entry in the [CurrentlyStoringFor] table with the given info. NOTE: assumes 
        the store date is TODAY."""
        
        # Construct the query (NOTE: 5 placeholders)
        query:str = """
            INSERT INTO CurrentlyStoringFor(peer_pub_key, filename, size_gb, sha256, store_date)
            VALUES (?, ?, ?, ?, ?)
        """
        
        try: 
            # Exceute the query
            self.cursor.execute(
                query,
                (
                    peer_pub_key,
                    filename,
                    size_gb,
                    sha256,
                    dt.datetime.now().strftime('%Y-%m-%d')
                )
            )
            
            # Commit changes
            self.cxn.commit()
            
        # Handle exceptions
        # Integrity Error means a key constraint was violated
        except sql.IntegrityError as e: 
            self.logger.error(f'in new_storing_for_file() - Integrity Error: {e}')
            return 
        
        # Other exceptions
        except Exception as e: 
            self.logger.error(f'in new_storing_for_file() - {e.__class__}: {e}')
            return 
    
    
    def remove_storing_with_entry(self, peer_pub_key:str, filename:str) -> None: 
        """Removes the entry in the [CurrentlyStoringWith] table for the given peer pub key 
        and filename."""
        
        # Construct query
        query:str = "DELETE FROM CurrentlyStoringWith WHERE peer_pub_key = ? AND filename = ?"
        
        try: 
            # Execute the query
            self.cursor.execute(
                query,
                (peer_pub_key, filename)
            )
            
            # Commit changes
            self.cxn.commit() 
            
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in remove_storing_with_entry() - {e.__class__}: {e}')
            return 
    
    
    def remove_storing_for_entry(self, peer_pub_key:str, filename:str) -> None: 
        """Removes the entry in the [CurrentlyStoringFor] table for the given peer pub key 
        and filename."""
        
        # Construct query
        query:str = "DELETE FROM CurrentlyStoringFor WHERE peer_pub_key = ? AND filename = ?"
        
        try: 
            # Execute the query
            self.cursor.execute(
                query,
                (peer_pub_key, filename)
            )
            
            # Commit changes
            self.cxn.commit() 
            
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in remove_storing_for_entry() - {e.__class__}: {e}')
            return 
    
    
    # ---- Functions that aggregate columns in various tables ---- # 
    
    def get_local_used_storage(self, peer_pub_key:str=None) -> float: 
        """Returns the sum of the [size_gb] column in the [CurrentlyStoringFor] table, optionally 
        filtering by the given peer public key to return just the sum for that peer."""
                
        # Construct a base query
        base_query:str = f'SELECT SUM(size_gb) FROM CurrentlyStoringFor'
        
        try: 
            # Check if given a pub key to filter on and execute the appropriate query
            # YES filter by pub key
            if peer_pub_key: 
                self.cursor.execute(
                    base_query + ' WHERE peer_pub_key = ?',
                    (peer_pub_key,)
                )
            
            # NO filter by pub key
            else: 
                self.cursor.execute(base_query)
                
            # Fetch results and return
            results:tuple = self.cursor.fetchone()
            
            if results: return float(results[0])
            else: return 0.0
        
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in get_local_used_storage() - {e.__class__}: {e}')
            return 
        
    
    def get_remote_used_storage(self, peer_pub_key:str=None) -> float: 
        """Returns the sum of the [size_gb] column in the [CurrentlyStoringWith] table, optionally 
        filtering by the given peer public key to return just the sum for that peer."""
        
        # Construct a base query
        base_query:str = f'SELECT SUM(size_gb) FROM CurrentlyStoringWith'
        
        try: 
            # Check if given a pub key to filter on and execute the appropriate query
            # YES filter by pub key
            if peer_pub_key: 
                self.cursor.execute(
                    base_query + ' WHERE peer_pub_key = ?',
                    (peer_pub_key,)
                )
            
            # NO filter by pub key
            else: 
                self.cursor.execute(base_query)
                
            # Fetch results and return
            results:tuple = self.cursor.fetchone()
            
            if results: return float(results[0])
            else: return 0.0
        
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in get_remote_used_storage() - {e.__class__}: {e}')
            return 
    
    
    def get_stored_file_nonce(self, peer_pub_key:str, filename:str) -> str: 
        """Retrieves the [b64_nonce] from the [CurrentlyStoringWith] table for the given peer and filename."""
        
        try: 
            # Construct and execute query
            self.cursor.execute(
                'SELECT b64_nonce FROM CurrentlyStoringWith WHERE peer_pub_key = ? AND filename = ?',
                (peer_pub_key, filename)
            )
            
            # Fetch results
            results:tuple = self.cursor.fetchone()
            
            if results: return results[0]
            else: return None
        
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in get_stored_file_nonce() - {e.__class__}: {e}')
            return None