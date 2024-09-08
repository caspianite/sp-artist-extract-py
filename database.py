import os
import random
import string
import psycopg2
import psycopg2.extras
from typing import Union
import redis
from settings import settings
import json

# TODO fix/manage the specific use of conn.cursor.execute() fetch methods



class DatabaseHandler:
    def __init__(self) -> None:
        self.conn = psycopg2.connect(settings.postgres_conn_string) # dangerous
        self.cursor = self.conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        self.proxies = self.fetch_all_proxy_urls()

    def escape_unicode(self, text):
        # This function will escape non-ASCII characters into their Unicode equivalents
        return text.encode('unicode_escape').decode('ascii')
    
    def generate_random_string(self, length=12):
        """Generate a random alphanumeric string of lowercase letters of a given length."""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


    def fetch_all_proxy_urls(self):
        
        """Fetch all proxy URLs from the proxies_urls table."""
        print("fetching proxies")

        if settings.debug_mode:
            print("using proxy ", [settings.debug_proxy])
            return [settings.debug_proxy]

        try:
            self.cursor.execute("SELECT url FROM proxies_urls")
            rows = self.cursor.fetchall()  # Fetches all rows from the query result
            print(rows)
            return [row['url'] for row in rows]  # Extracts only the URL from each row
        except Exception as err:
            print(f"Error fetching proxy URLs: {err}")
            return []
        
    def insert_artist_performance_over_time(self, artist_performance):
        """
        Inserts an artist's performance data into the artist_performance_over_time table.
        
        artist_performance: A dictionary containing the artist's performance data.
        """
        # Base query
        query = """
            INSERT INTO artist_performance_over_time
            (artist_key, world_rank, monthly_listeners, monthly_listeners_delta)
            VALUES (%s, %s, %s, %s)
        """
        
        # Values to insert (using tuple)
        values = (
            artist_performance['artist_key'],
            artist_performance['world_rank'],
            artist_performance['monthly_listeners'],
            artist_performance['monthly_listeners_delta']
        )

        try:
            # Execute the insert query
            self.cursor.execute(query, values)
            self.conn.commit()  # Commit the transaction
            print(f"ArtistPerformanceOverTimeInput inserted: {artist_performance['artist_key']}")
        except Exception as err:
            print(f"Error executing insert query: {err}")
            print(f"Interface passed: {artist_performance}")
            print(f"Query: {query}")
            self.conn.rollback()  # Rollback in case of error
    
    def insert_artist_information(self, artist_key: str, artist_pathfinder_json: dict):
        # Base query
        query = """
            INSERT INTO artist_information (artist_key, artist_pathfinder_json)
            VALUES (%s, %s)
        """

        # Prepare values
        values = [
            artist_key,
            self.escape_unicode(json.dumps(artist_pathfinder_json)),
        ]

        try:
            # Execute the query
            self.client.execute(query, values)
            # Commit the transaction
            self.client.commit()
            print('ArtistInformationInput inserted and transaction committed')
            return True
        except Exception as err:
            print('Error executing insert query', err)
            if "Unicode" in str(err):
                print("unicode error")
                ##with open("artist_pathfinder.json", "w") as f:
                ##    json.dump(artist_pathfinder_json, f)
            print('interface passed:', artist_pathfinder_json)
            print("query:", query)
    
    def insert_artist_pathfinder_over_time(self, artist_key, stats, profile, goods, relatedcontent, relatedartists, discography, relatedvideos):
        query = """
        INSERT INTO artist_table (
            artist_key, 
            stats, 
            profile, 
            goods, 
            relatedcontent, 
            relatedartists, 
            discography, 
            relatedvideos
        ) 
        VALUES (
            %s, 
            %s, 
            %s, 
            %s, 
            %s, 
            %s, 
            %s, 
            %s
        )
        """

        try:
            self.cursor.execute(query, (
                artist_key, 
                json.dumps(stats), 
                json.dumps(profile), 
                json.dumps(goods), 
                json.dumps(relatedcontent), 
                json.dumps(relatedartists), 
                json.dumps(discography), 
                json.dumps(relatedvideos)
            ))
            self.connection.commit()
            print("Artist data inserted successfully")

        except Exception as e:
            print("Failed to insert artist data", e)
            self.connection.rollback()

    def insert_artist_json(self, artist_key, artist_data_json):
        # Query excluding artist_entry_id and scraped_at, which have default values
        query = """
        INSERT INTO artist_json (
            artist_key, 
            artist_data_json
        ) 
        VALUES (
            %s, 
            %s
        )
        """

        try:
            # Execute the query with values for artist_key and artist_data_json
            self.cursor.execute(query, (
                artist_key, 
                json.dumps(artist_data_json)  # Convert the data to JSON string format
            ))
            # Commit the transaction
            self.connection.commit()
            print("Artist JSON data inserted successfully")

        except Exception as e:
            print("Failed to insert artist JSON data:", e)
            # Rollback the transaction in case of error
            self.connection.rollback()

    def insert_artist_relations(self, artist_key, relates_to_artist_keys: list[str]):
        # Query excluding scraped_at, which has a default value
        query = """
        INSERT INTO artist_relations (
            artist_key, 
            relates_to_artist_key, 
            relation_id
        ) 
        VALUES (
            %s, 
            %s, 
            %s
        )
        """

        try:
            relation_id = self.generate_random_string()
            # Loop through each relates_to_artist_key and insert a row for each
            for relates_to_artist_key in relates_to_artist_keys:
                self.cursor.execute(query, (
                    artist_key, 
                    relates_to_artist_key, 
                    relation_id
                ))

            # Commit the transaction after inserting all rows
            self.connection.commit()
            print(f"Inserted {len(relates_to_artist_keys)} artist relations data rows successfully")

        except Exception as e:
            print("Failed to insert artist relations data:", e)
            # Rollback the transaction in case of error
            self.connection.rollback()

    def find_relation_with_exact_artist_keys(self, artist_key: str, related_artist_keys: list[str]):
        """
        Find a relation where the artist_key and the exact set of related artist keys match.
        """
        # Sort related_artist_keys to ensure consistent ordering
        related_artist_keys_sorted = sorted(related_artist_keys)

        # Create a query that looks for relations where the artist_key and the related artist keys match exactly
        query = """
        SELECT relation_id
        FROM artist_relations
        WHERE artist_key = %s
        AND relates_to_artist_key = ANY(%s)
        GROUP BY relation_id
        HAVING array_agg(DISTINCT relates_to_artist_key ORDER BY relates_to_artist_key) = %s
        """

        try:
            # Execute the query with the artist_key and sorted related_artist_keys list for exact matching
            self.cursor.execute(query, (artist_key, related_artist_keys, related_artist_keys_sorted))

            # Fetch the matching relation_id if any
            result = self.cursor.fetchone()

            if result:
                return result['relation_id']
            else:
                return None  # No relation found with the exact artist key and related artist keys
        except Exception as e:
            print("Failed to find relation with exact artist keys:", e)
            return None

    def artist_key_exists(self, artist_key: str) -> bool:
        """
        Check if the artist_key exists in the artist_information table.
        """
        try:
            query = "SELECT EXISTS(SELECT 1 FROM artist_information WHERE artist_key = %s);"
            # Execute the query
            self.cursor.execute(query, (artist_key,))
            # Fetch the result, which will be a boolean
            result = self.cursor.fetchone()[0]
            return result
        except Exception as e:
            print(f"Error checking if artist_key exists: {e}")
            return False





    



class RedisDatabaseHandler:
    def __init__(self):
        self.client = redis.StrictRedis.from_url(settings.redis_conn_string)



    def set_key(self, key: str, value: str, ttl_seconds: int = None) -> None:
        """Set a Redis key with an optional TTL (time-to-live)."""
        try:
            if ttl_seconds:
                self.client.set(key, value, ex=ttl_seconds)
            else:
                self.client.set(key, value)
            print(f"Key set: {key} -> {value}")
        except Exception as err:
            print(f"Error setting key: {err}")

    def key_exists(self, key: str) -> bool:
        """Check if a Redis key exists."""
        try:
            exists = self.client.exists(key)
            return exists == 1
        except Exception as err:
            print(f"Error checking if key exists: {err}")
            return False

    def fetch_random_key(self) -> str:
        """Fetch a random key from Redis."""
        try:
            key = self.client.randomkey()
            if key:
                print(f"Random Key fetched: {key}")
                return key
            else:
                print("No keys found in Redis.")
                return None
        except Exception as err:
            print(f"Error fetching random key: {err}")
            return None

    def fetch_random_key_value(self) -> dict:
        """Fetch a random key and its value from Redis."""
        try:
            key = self.client.randomkey()
            if key:
                value = self.client.get(key)
                print(f"Random Key fetched: {key} with value: {value}")
                return {"key": key, "value": value}
            else:
                print("No keys found in Redis.")
                return None
        except Exception as err:
            print(f"Error fetching random key and its value: {err}")
            return None
