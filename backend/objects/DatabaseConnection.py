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
    
    
    def __init__(self, db_filepath:str, log_filepath:str='logs/database.log', logger_name:str='database_logger'): 
        
        # Create log dir if it doesn't exist
        os.makedirs(os.path.dirname(log_filepath), exist_ok=True)
        
        # Init logger first to log success/errors
        self.logger = setup_logger(
            log_filepath,
            logger_name
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
                            sha256:str, accepted:bool=None, request_date:str='', notified:bool=False, ) -> None: 
        """Creates a new entry in either the [PendingIncomingRequest] or [PendingOutgoingRequest] table 
        with the given information. The given [direction] must be either 'incoming' or 'outgoing', other
        values will raise a ValueError. NOTE: assumes the request date is TODAY, notified is False, and 
        accepted is None, if these are not given."""
        
        # Log
        self.logger.info(f'in new_pending_request(): creating new pending request (direction = {direction}, filename = {filename}, request_type = {request_type})')
        
        # Make sure a valid direction is given 
        direction = direction.lower() 
        if not direction in ['incoming', 'outgoing']: 
            raise ValueError(f'Given direction "{direction}" is not valid - must be one of "incoming" or "outgoing"')
        
        # Create query (NOTE: 7 placeholders)
        query:str = f"""
            INSERT INTO PendingRequests(direction, request_type, peer_pub_key, filename, size_gb, sha256, accepted, request_date, notified) 
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?) 
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
                    accepted,
                    dt.datetime.now().strftime('%Y-%m-%d') if not request_date else request_date,
                    notified
                )
            )
            
            # Commit changes 
            self.cxn.commit() 
            self.logger.info(f'in new_pending_request(): created new {direction.upper()} pending request for "{self.cn_from_pub_key(peer_pub_key)}" (ID = {self.get_request_id(peer_pub_key, filename, request_type, direction)})')
            
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in new_pending_request() - {e.__class__}: {e}')
            raise Exception('An error occured while inserting the new pending request.')
    

    def remove_pending_request(self, req_id:int) -> None: 
        """Removes the row for the given [req_id] (request ID) from the [PendingRequests] table."""
        
        # Log
        self.logger.info(f'in remove_pending_request(): removing request ID "{req_id}"')
        
        # Execute query
        self.cursor.execute(
            'DELETE FROM PendingRequests WHERE id = ?',
            (req_id,)
        )
        
        # Commit changes
        self.cxn.commit()
        self.logger.info(f'Deleted pending request ID {req_id}.')
            
    
    def get_request_id(self, peer_pub_key:str, filename:str, request_type:str, direction:str) -> int: 
        """Returns the request ID for the request matching the given peer pub key, filename, request type, and direction."""
        
        self.logger.debug(f'Getting request ID for "{filename}", request type "{request_type}", direction "{direction}"')
        
        # Construct and execute query
        self.cursor.execute(
            'SELECT id FROM PendingRequests WHERE peer_pub_key = ? AND filename = ? AND request_type = ? AND direction = ?',
            (peer_pub_key, filename, request_type, direction)
        )
        
        # Fetch results
        results:tuple = self.cursor.fetchone()
        
        # Log
        self.logger.info(f'in get_request_id(): got results for filename "{filename}", request type "{request_type}", direction "{direction}" | Results: {results}')
        
        # Return according to results
        if results: return int(results[0])
        else: return -1
        
    
    def update_request_date(self, request_id:int, new_date:str) -> None: 
        """Updates the request_date for the given request ID."""
        
        # Log
        self.logger.info(f'in update_request_date(): updating request date for "{request_id}" to "{new_date}"')
        
        # Execute query
        self.cursor.execute(
            'UPDATE PendingRequests SET request_date = ? WHERE id = ?',
            (new_date, request_id)
        )
        
        # Commit changes 
        self.cxn.commit() 
        self.logger.info(f'in update_request_date(): updated the date for PendingRequests ID {request_id} to "{new_date}"')
        
    
    def check_pending_requests_status(self, target_direction:str, target_peer_online_status:bool=True, notified=False) -> list[int]: 
        """Takes in a [target_direction] and returns a list of request IDs where the peer's online status matches 
        [target_peer_online_status] and with the given target direction and notified status. E.g. given target 
        direction 'outgoing'  and target peer online status 'True', returns a list of all pending outgoing request 
        IDs where the associated peer is online. """

        # Construct query
        query:str = """
            SELECT PR.id
            FROM PendingRequests PR
            JOIN Peer P ON PR.peer_pub_key = P.peer_pub_key 
            WHERE PR.direction = ? AND P.online = ? AND PR.notified = ?
        """

        # Execute the query
        self.cursor.execute(
            query,
            (target_direction, int(target_peer_online_status), notified)
        )

        # Fetch results
        results:list[tuple] = self.cursor.fetchall()
        return [r[0] for r in results] if results else []


    def update_request_notified(self, request_id:int, new_notified:bool=True) -> None: 
        """Updates the notified status for the given request ID."""
        
        # Log
        self.logger.info(f'in update_request_notified(): updating "{request_id}" to notified = "{new_notified}"')
        
        # Construct and execute query
        self.cursor.execute(
            'UPDATE PendingRequests SET notified = ? WHERE id = ?',
            (new_notified, request_id)
        )
        
        # Commit changes
        self.cxn.commit()
        self.logger.info(f'Updated "{request_id}" to notified = {new_notified}')
        
        
    def get_pending_request(self, request_id:int) -> dict|None: 
        """Takes in a request ID and returns the row in the PendingRequests table for that request (as a dict)."""

        # Construct and execute query
        self.cursor.execute(
            'SELECT * FROM PendingRequests WHERE id = ?',
            (request_id,)
        )

        # Fetch results
        result:tuple = self.cursor.fetchone()

        # Return accordingly
        if result: 
            return {
                c : r 
                for c,r in zip(self.get_table_columns('PendingRequests'), list(result)) 
            } 
        else: 
            return None


    def check_request_id_exists(self, request_id:int) -> bool: 
        """Checks that the given request_id exists in the PendingRequests table."""

        # Create and execute query
        try: 
            # Execute the query
            self.cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM PendingRequests WHERE id = ?)",
                (request_id,)
            )
            
            # Fetch results
            return self.cursor.fetchone()[0] == 1
        
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in check_request_id_exists() - {e.__class__}: {e}')
            return


    def update_request_accepted(self, request_id:int, accepted:bool) -> None: 
        """Updates the "accepted" field for the given request ID."""

        # Log
        self.logger.info(f'in update_request_accepted(): updating "{request_id}" to accepted = "{accepted}"')
        
        # Create and execute the query
        try: 
            self.cursor.execute(
                'UPDATE PendingRequests SET accepted = ? WHERE id = ?',
                (accepted, request_id)
            )

            # Commit changes
            self.cxn.commit()

        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in update_request_accepted(): {e.__class__} - {e}')
            return 


    def completed_pending_request(self, request_id:int) -> None: 
        """Moves an entry from the PendingRequests table to the CompletedRequests table."""

        # Log 
        self.logger.info(f'in completed_pending_requests(): moving "{request_id}" to CompletedRequests.')
        
        # Get the request info from the pending requests table
        pending_request_info:dict = self.get_pending_request(request_id)
        
        # Check for results
        if not pending_request_info: 
            self.logger.warning(f'in completed_pending_request(): did not find any matches for PendingRequest ID "{request_id}"')
            return 

        # Get the cols for CompletedRequests
        completed_requests_cols:list[str] = self.get_table_columns('CompletedRequests')

        # Extract only the pending request fields that are in completed requests
        insert_tup:tuple = tuple([v for k,v in pending_request_info.items() if k in completed_requests_cols])
        
        # If we get results, then move the entry into CompletedRequests
        # NOTE: 9 placeholders
        self.cursor.execute(
            f"""
            INSERT INTO CompletedRequests({",".join(completed_requests_cols)})
            VALUES ({",".join(["?" for _ in completed_requests_cols])})
            """,
            insert_tup
        )

        # Now delete the PendingRequest entry
        self.remove_pending_request(request_id)
        
        # Commit changes
        self.cxn.commit()


    # ---- Functions for the [Peer] table ---- # 
    
    def new_peer(self, peer_pub_key:str, online:bool, most_recent_ip:str, common_name:str, 
                 mac_last_four:str) -> None: 
        """Creates a new row in the [Peer] table for the given peer info."""
        
        # Log
        self.logger.info(f'in new_peer(): creating new Peer entry for common name "{common_name}"')
        
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
        
        # Log
        self.logger.info(f'in update_peer_status(): updating the (most_recent_ip, new_online_status) for {peer_pub_key} to ({new_ip}, {new_online_status})')
        
        try: 
            # Construct and execute query
            self.cursor.execute(
                """
                    UPDATE Peer 
                    SET most_recent_ip = ?, online = ?
                    WHERE peer_pub_key = ?
                """,
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
        
    
    def get_matching_peers(self, peer_pub_key:str=None, online:bool=None, most_recent_ip:str=None, 
                           common_name:str=None, mac_last_four:str=None) -> pd.DataFrame:
        """Returns the [peer_pub_key]s of all peers that match the intersection (AND) of the given args."""
        
        # Get the cols for the Peer table
        table_cols:list[str] = self.get_table_columns('Peer')
        
        # Construct query
        query:str = f"SELECT {','.join(table_cols)} FROM Peer"
        
        # Generate the conditions and parameters
        conditions:list[str] = []
        params:list[str] = []

        # For each of the args, add it to the conditions and params if given
        if peer_pub_key and peer_pub_key is not None:
            conditions.append("peer_pub_key = ?")
            params.append(peer_pub_key)

        if online is not None:
            conditions.append("online = ?")
            params.append(int(bool(online)))  # ensure boolean is stored as 0/1

        if most_recent_ip and most_recent_ip is not None:
            conditions.append("most_recent_ip = ?")
            params.append(most_recent_ip)

        if common_name and common_name is not None:
            conditions.append("common_name = ?")
            params.append(common_name)

        if mac_last_four and mac_last_four is not None:
            conditions.append("mac_last_four = ?")
            params.append(mac_last_four)

        # Check if we have any conditions to add
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        # Execute the query
        self.cursor.execute(query, params)
        
        # Fetch results and return
        return pd.DataFrame(
            self.cursor.fetchall(),
            columns=table_cols
        )
        

    def cn_from_pub_key(self, pub_key: str) -> str|None:
        """Returns the common name for the given public key."""
        
        # Execute query
        self.cursor.execute("SELECT common_name FROM Peer WHERE peer_pub_key = ?", (pub_key,))
        
        # Fetch results and return
        row = self.cursor.fetchone()
        return row[0] if row else None


    def pub_key_from_cn(self, common_name:str) -> list[str]: 
        """Returns the public key for the given common name. NOTE: if more than one peer match the given 
        common name, then all matched pub keys are returned, but if only one matches, then a list with a 
        single value is returned."""
        
        # Execute query
        self.cursor.execute(
            "SELECT peer_pub_key FROM Peer WHERE common_name = ?",
            (common_name,)
        )
        
        # Fetch results and return
        results:list[tuple] = self.cursor.fetchall()
        return [r[0] for r in results] if results else []
        
        
    def get_interacted_with_peers(self) -> dict:
        """Returns a dict containing peer_pub_keys and interaction statistics (files stored remotely, 
        stored locally, and shared), grouped by peer.
        """

        # Construct a query that aggregates interaction counts
        query:str = """
            SELECT
                peer_pub_key,
                SUM(stored_locally) AS stored_locally,
                SUM(stored_remotely) AS stored_remotely,
                SUM(shared) AS shared
            FROM (
                SELECT peer_pub_key, 1 AS stored_locally, 0 AS stored_remotely, 0 AS shared FROM CurrentlyStoringFor
                UNION ALL
                SELECT peer_pub_key, 0, 1, 0 FROM CurrentlyStoringWith
                UNION ALL
                SELECT peer_pub_key, 0, 0, 1 FROM PreviouslySharedWith
            )
            GROUP BY peer_pub_key
        """

        # Execute the query and get the results as a df
        df:pd.DataFrame = pd.read_sql_query(query, self.cxn)

        # Check for results
        if df.empty:
            return {}

        # Construct result map
        peer_map:dict = {
            row['peer_pub_key']: {
                'common_name': self.cn_from_pub_key(row['peer_pub_key']),
                'storage_data': {
                    'stored_locally': row['stored_locally'],
                    'stored_remotely': row['stored_remotely'],
                    'shared': row['shared']
                }
            }
            for _, row in df.iterrows()
        }

        # Return the peer map
        return peer_map


    # ---- Functions for the [Currently* and PreviouslySharedWith] tables ---- #
    
    def new_shared_file(self, peer_pub_key:str, direction:str, filename:str, size_gb:float, 
                        sha256:str, share_date:str='') -> None: 
        """Creates a new entry in the [PreviouslySharedWith] table with the given info. The [direction] 
        must be either 'incoming' or 'outgoing', other values will raise a ValueError. NOTE: assumes 
        the share date is TODAY if not given."""
        
        # Log
        self.logger.info(f'in new_shared_file(): creating new entry for filename "{filename}" and direction "{direction}"')
        
        # Check that the given direction is valid
        direction = direction.lower()
        if not direction in ['incoming', 'outgoing']: 
            raise ValueError(f'Given direction "{direction}" is not valid - must be one of "incoming" or "outgoing"')
        
        try: 
            # Construct and execute the query (NOTE: 6 placeholders)
            self.cursor.execute(
                """
                    INSERT INTO PreviouslySharedWith(peer_pub_key, direction, filename, size_gb, sha256, share_date) 
                    VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    peer_pub_key,
                    direction,
                    filename,
                    size_gb,
                    sha256,
                    dt.datetime.now().strftime('%Y-%m-%d') if not share_date else share_date
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
                              b64_nonce:str, store_date:str='') -> None: 
        """Creates a new entry in the [CurrentlyStoringWith] table with the given info. NOTE: assumes
        the store date is TODAY if not given."""
        
        # Log
        self.logger.info(f'in new_storing_with_file(): creating new entry for filename "{filename}"')
        
        try: 
            # Construct and execute the query (NOTE: 6 placeholders)
            self.cursor.execute(
                """
                INSERT INTO CurrentlyStoringWith(peer_pub_key, filename, size_gb, sha256, b64_nonce, store_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    peer_pub_key,
                    filename,
                    size_gb,
                    sha256,
                    b64_nonce,
                    dt.datetime.now().strftime('%Y-%m-%d') if not store_date else store_date
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
    
    
    def new_storing_for_file(self, peer_pub_key:str, filename:str, size_gb:float, sha256:str, store_date:str='') -> None:
        """Creates a new entry in the [CurrentlyStoringFor] table with the given info. NOTE: assumes 
        the store date is TODAY if not given."""
        
        # Log
        self.logger.info(f'in new_storing_for_file(): creating new entry for filename "{filename}"')
        
        try: 
            # Construct and execute the query (NOTE: 5 placeholders)
            self.cursor.execute(
                """
                INSERT INTO CurrentlyStoringFor(peer_pub_key, filename, size_gb, sha256, store_date)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    peer_pub_key,
                    filename,
                    size_gb,
                    sha256,
                    dt.datetime.now().strftime('%Y-%m-%d') if not store_date else store_date
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
        
        # Log
        self.logger.info(f'in remove_storing_with_entry(): removing entry for filename "{filename}", peer "{peer_pub_key}"')
        
        try: 
            # Execute the query
            self.cursor.execute(
                "DELETE FROM CurrentlyStoringWith WHERE peer_pub_key = ? AND filename = ?",
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
        
        # Log
        self.logger.info(f'in remove_storing_with_entry(): removing entry for filename "{filename}", peer "{peer_pub_key}"')
        
        try: 
            # Construct and execute the query
            self.cursor.execute(
                "DELETE FROM CurrentlyStoringFor WHERE peer_pub_key = ? AND filename = ?",
                (peer_pub_key, filename)
            )
            
            # Commit changes
            self.cxn.commit() 
            
        # Handle exceptions
        except Exception as e: 
            self.logger.error(f'in remove_storing_for_entry() - {e.__class__}: {e}')
            return 
    
    
    def get_storing_with_info(self, peer_pub_keys:list[str]) -> pd.DataFrame: 
        """Retrieves the contents of the [CurrentlyStoringWith] table for the given peer pub keys. If no
        peer pub keys are given, then returns the entire table as a df."""

        # Get the "CurrentlyStoringWith" table as a df
        curr_storing_with_df:pd.DataFrame = self.table_as_df('CurrentlyStoringWith')
        
        # Check if given pub keys to filter 
        if peer_pub_keys: 
            
            # Filter the df for the peer pub keys
            curr_storing_with_df = curr_storing_with_df[curr_storing_with_df['peer_pub_key'].isin(peer_pub_keys)]
        
        # Return the df
        return curr_storing_with_df
    
    
    def check_stored_with_file_exists(self, peer_pub_key:str, filename:str) -> bool: 
        """Checks that the given filename is actually being stored with the given peer."""
        
        # Execute the query
        self.cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM CurrentlyStoringWith WHERE peer_pub_key = ? AND filename = ?)",
            (peer_pub_key, filename)
        )
        
        # Fetch results
        return self.cursor.fetchone()[0] == 1
    
    
    def check_stored_for_file_exists(self, peer_pub_key:str, filename:str) -> bool: 
        """Checks that the given filename is actually being stored with the given peer."""
        
        # Execute the query
        self.cursor.execute(
            "SELECT EXISTS(SELECT 1 FROM CurrentlyStoringFor WHERE peer_pub_key = ? AND filename = ?)",
            (peer_pub_key, filename)
        )
        
        # Fetch results
        return self.cursor.fetchone()[0] == 1
    

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
    
    
    def get_all_storage_info(self) -> dict[str, float]: 
        """Returns a dict with three keys for "gb_shared", "gb_storing_for", and "gb_storing_with" for 
        all peers."""
        
        # Execute the query
        self.cursor.execute("""
        SELECT 
            (SELECT SUM(size_gb) FROM PreviouslySharedWith) AS gb_shared,
            (SELECT SUM(size_gb) FROM CurrentlyStoringFor) AS gb_storing_for,
            (SELECT SUM(size_gb) FROM CurrentlyStoringWith) AS gb_storing_with
        """)
    
        # Fetch results
        row:tuple = self.cursor.fetchone()

        # Return the results
        return {
            'gb_shared': row[0] or 0.0,
            'gb_storing_for': row[1] or 0.0,
            'gb_storing_with': row[2] or 0.0
        }
        
    
    def get_user_history(self, peer_pub_key:str=None) -> dict[str, list[dict]]: 
        """Returns the history of this client with the given peer."""
        
        # Prepare base queries for each relevant table
        base_queries:dict[str, str] = {
            'storing_for': "SELECT * FROM CurrentlyStoringFor",
            'storing_with': "SELECT * FROM CurrentlyStoringWith",
            'shared': "SELECT * FROM PreviouslySharedWith"
        }

        # Add WHERE clause if filtering by peer pub key
        if peer_pub_key:
            for key in base_queries:
                base_queries[key] += " WHERE peer_pub_key = ?"

        # Execute and load into DataFrames
        storing_for_df = pd.read_sql_query(base_queries['storing_for'], self.cxn, params=(peer_pub_key,) if peer_pub_key else None)
        storing_with_df = pd.read_sql_query(base_queries['storing_with'], self.cxn, params=(peer_pub_key,) if peer_pub_key else None)
        shared_df = pd.read_sql_query(base_queries['shared'], self.cxn, params=(peer_pub_key,) if peer_pub_key else None)

        # Return all as a dict
        return {
            'storing_for': storing_for_df.to_dict(orient='records'),
            'storing_with': storing_with_df.to_dict(orient='records'),
            'shared': shared_df.to_dict(orient='records')
        }
        
        
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