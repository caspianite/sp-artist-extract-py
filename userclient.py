import json
import os
import random
import re
import string
import time
import database
from settings import settings
import httpx
class UserClient():
    def __init__(self, database: database.DatabaseHandler, redis: database.RedisDatabaseHandler) -> None:
        self.database = database
        self.http_client = httpx.Client(http2=True, follow_redirects=True, verify=False, proxy=None if settings.skip_proxy else random.choice(self.database.proxies))
        self.redis = redis
        self.requests_sent = 0
        self.bearer_token = self.fetch_bearer_token()
    def generate_random_string(self, length=32):
        """Generate a random alphanumeric string of lowercase letters of a given length."""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def generate_random_int(self, start, end):
        """Generate a random integer between start and end (inclusive)."""
        return random.randint(start, end)
    
    def fetch_client_token(self):
        return self.redis.fetch_random_key_value()["value"]
    
    @staticmethod
    def fetch_bearer_token(proxy_url=None):
        """
        Fetch the bearer token from the Spotify playlist page.

        :param proxy_url: Optional proxy URL to route the request through.
        :return: Bearer token as a string.
        :raises: Exception if token fetch fails.
        """
        try:
            # Set up the request options
            request_options = {
                "follow_redirects": True,
                "timeout": 10.0,  # Optional timeout for the request
            }

            # Add proxy if provided
            #if proxy_url:
            #    request_options["proxies"] = {"http://": proxy_url, "https://": proxy_url}

            # Make the HTTP GET request to fetch the playlist page
            response = httpx.get(
                "https://open.spotify.com/playlist/3IyY3EphrdZfnpsrT84YBM",
                **request_options
            )

            response.raise_for_status()  # Raise an exception for non-200 responses

            playlist_page = response.text

            # Extract the bearer token using a regular expression
            bearer_token = re.search(r'<script id="session" data-testid="session" type="application/json">{"accessToken":"(.*?)","accessTokenExpirationTimestampMs"', playlist_page)

            if bearer_token:
                bearer = bearer_token.group(1)
                print("Fetched bearer token:", bearer)
                return bearer
            else:
                raise ValueError("Bearer token not found in the page content.")

        except httpx.HTTPStatusError as http_err:
            print(f"HTTP error occurred: {http_err}")
            raise
        except Exception as err:
            print(f"Failed to fetch bearer token: {err}")
            raise


    def generate_headers(self, client_token: str, is_mobile_or_sp_client: bool):
        if not self.bearer_token:
            raise ValueError("Bearer token is missing")

        """Generate headers for Spotify requests."""

        # Common headers for both mobile and web clients
        common_headers = {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br, zstd",
            "content-type": "application/json;charset=UTF-8",
            "referer": "https://open.spotify.com",
            "origin": "https://open.spotify.com",
            "client-token": client_token,
            'Authorization': f'Bearer {self.bearer_token}'
        }
        # If it's a mobile or spclient request, include mobile-specific headers
        if is_mobile_or_sp_client:
            return {
                **common_headers,
                "user-agent": f'Spotify/8.9.34.590 Android/{self.generate_random_int(27, 29)} (Pixel)',
                "spotify-app-version": "8.9.34.590",
                "x-client-id": self.generate_random_string()
            }
        # If it's a web client, include web-specific headers
        return {
            **common_headers,
            "app-platform": "WebPlayer",
            "spotify-app-version": "1.2.41.273.ge0010ef5"
        }
    
    def get_API(self, url: str, params: dict|None):
         # Fetch client token and random client ID
        client_token = self.fetch_client_token()
        client_id = self.generate_random_string()
        if not client_token or not isinstance(client_token, str):
            raise ValueError("Invalid client token")




        # Determine if it's a mobile or spclient request
        is_mobile_or_sp_client = "spclient" in url

        # Generate headers
        headers = self.generate_headers(client_token, is_mobile_or_sp_client)
        proxy_url = random.choice(self.database.proxies)


        try:
            # Perform the HTTP GET request using httpx (sync)
            response = self.http_client.get(url, params=params, headers=headers)
            print(response.url)
            response.raise_for_status()  # Raise an error for non-200 responses
            return response.json()  # Return response as JSON
        except httpx.HTTPStatusError as http_err:
            print(f"HTTP error occurred: {http_err}")
            raise
        except Exception as err:
            print(f"Error in sync_get: {err}")
            raise
    
    def process_artist_pathfinder(self, artist_key: str):
        pathfinder_json = self.get_API(url="https://api-partner.spotify.com/pathfinder/v1/query", params={
                "operationName": "queryArtistOverview",
                "variables": {
                    "uri": f"spotify:artist:{artist_key}",
                    "locale": "intl-us",
                    "includePrerelease": True
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 1,
                        "sha256Hash": "7c5a08a226e4dc96387c0c0a5ef4bd1d2e2d95c88cbb33dcfa505928591de672"
                    }
                }
        })

        artistsUnion = pathfinder_json["data"]["artistsUnion"]
        profile = artistsUnion["profile"]
        stats = artistsUnion["stats"]
        discography = artistsUnion["discography"]
        goods = artistsUnion["goods"]
        relatedcontent = artistsUnion["relatedContent"]
        relatedvideos = artistsUnion["relatedVideos"]
        relatedartists = artistsUnion["relatedArtists"]
        if self.database.insert_artist_information(artist_key, pathfinder_json):
            self.database.insert_artist_json(artist_key=artist_key, artist_data_json={"name": profile["name"]})

        self.database.insert_artist_pathfinder_over_time(artist_key, stats, profile, goods, relatedcontent, relatedartists, discography, relatedvideos)

    
    def process_artist_relations(self, artist_key: str, relatedartists: dict, spider_pathfinder_recursion: bool):
        related_artist_keys = [artist['id'] for artist in relatedartists['items']]

        if not self.database.find_relation_with_exact_artist_keys(artist_key, related_artist_keys):
            self.database.insert_artist_relations(artist_key, related_artist_keys)
        
        if spider_pathfinder_recursion:
            for key in related_artist_keys:
                if not self.database.artist_key_exists(key):
                    self.process_artist_pathfinder(key)




        
    
    def fetch_artist_performance_information(self, artist_key: str):
        """Scrape artist data and insert performance data into the database."""
        print("Scrape Time started")
        start_time = time.time()


        try:
            # Make a synchronous GET request to scrape artist data
            params = {"fields": "listenerCount,monthlyListenerRank"}
            info = self.get_API(f"https://spclient.wg.spotify.com/creatorabout/v0/artist/{artist_key}/about", params=params)
            print(info)

            # Check if the artistGid exists in the response
            if info.get("artistGid"):
                # Prepare the entry for inserting into the database
                entry = {
                    "artist_key": artist_key,
                    "world_rank": info.get("globalChartPosition", 0),  # Provide a default of 0
                    "monthly_listeners": info.get("monthlyListeners"),  # No need for a fallback, None is fine
                    "monthly_listeners_delta": info.get("monthlyListenersDelta")  # No need for a fallback, None is fine
                }

                # Insert into the database if there is a delta in monthly listeners
                if entry["monthly_listeners_delta"]:
                    self.database.insert_artist_performance_over_time(entry)

                # Increment the count of artists scraped
                self.requests_sent += 1
                print("Scrape Time ended")
                print(f"Total Scrape Time: {time.time() - start_time:.2f} seconds")
                self.refresh_client_token()
                return True
        except Exception as error:
            print(f"Error scraping artist {artist_key}: {error}")

        return False


    def produce_client_token(self):
        """Produces a client token and stores it in Redis."""
        try:
            # Prepare the request body
            body = {
                "client_data": {
                    "client_id": "d8a5ed958d274c2e8ee717e6a4b0971d",
                    "client_version": "1.2.46.351.g10226ba9",
                    "js_sdk_data": {
                        "device_brand": "unknown",
                        "device_id": self.generate_random_string(),
                        "device_model": "unknown",
                        "device_type": "computer",
                        "os": "windows",
                        "os_version": "NT 10.0"
                    }
                }
            }

            # Define headers
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0',
                'accept': 'application/json',
                'accept-language': 'en-US,en;q=0.5',
                'accept-encoding': 'gzip, deflate, br',
                'referer': 'https://open.spotify.com/',
                'origin': 'https://open.spotify.com'
            }

            # Fetch a proxy URL from the database
            #proxy_url = random.choice(self.database.proxies)

            # Make the POST request
            response = self.http_client.post(
                "https://clienttoken.spotify.com/v1/clienttoken",
                json=body,
                headers=headers
            )

            # Raise an exception for non-200 status codes
            response.raise_for_status()

            # Parse the JSON response
            r = response.json()

            # Check if the response contains the granted token
            if r.get("response_type") == "RESPONSE_GRANTED_TOKEN_RESPONSE":
                token = r['granted_token']['token']
                refresh_time = r['granted_token']['refresh_after_seconds']
                self.redis.set_key(self.generate_random_string(7), token, refresh_time // 2)
                print("Produced client token")

        except httpx.HTTPStatusError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"Error producing client token: {err}")

    def refresh_client_token(self):
        if self.requests_sent % 500 == 0:
            self.produce_client_token()

