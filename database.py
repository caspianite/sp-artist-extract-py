import os
import psycopg2
import psycopg2.extras
from typing import Union
import redis
from settings import settings
# TODO fix/manage the specific use of conn.cursor.execute() fetch methods



class DatabaseHandler:
    def __init__(self) -> None:
        self.conn = psycopg2.connect(settings.postgres_conn_string) # dangerous
        self.cursor = self.conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)
        self.proxies = self.fetch_all_proxy_urls()

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
