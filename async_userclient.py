import json
import random
import re
import string
import time
import urllib
import asyncio
import httpx
from settings import settings
import database

class UserClient():
    def __init__(self, database: database.DatabaseHandler, redis: database.RedisDatabaseHandler) -> None:
        self.database = database
        self.redis = redis
        self.requests_sent = 0
        self.bearer_token = None
        self.loop = asyncio.get_running_loop()
    
    async def initialize(self):
        self.http_client = httpx.AsyncClient(http2=True, follow_redirects=True, verify=False, proxies=random.choice(self.database.proxies))
        self.bearer_token = await self.fetch_bearer_token()

    def convert_bools_for_encoding(self, d):
        if isinstance(d, dict):
            return {k: self.convert_bools_for_encoding(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [self.convert_bools_for_encoding(v) for v in d]
        elif isinstance(d, bool):
            return d
        else:
            return d

    def dict_to_query_string(self, d, use_double_quotes=True):
        items = []
        for k, v in d.items():
            if isinstance(v, dict):
                v = str(v).replace("'", '"') if use_double_quotes else str(v)
            elif isinstance(v, bool):
                v = 'true' if v else 'false'
            items.append(f"{k}={urllib.parse.quote(str(v))}")
        return '&'.join(items)

    def dict_to_json_query_string(self, params: dict) -> str:
        json_string = json.dumps(params, separators=(',', ':'))
        encoded_string = urllib.parse.quote(json_string)
        return encoded_string

    def encode_query_string(self, params: dict, operation_name: str, use_double_quotes: bool = True) -> str:
        params_for_encoding = self.convert_bools_for_encoding(params)
        variables = params_for_encoding.get('variables', {})
        extensions = params_for_encoding.get('extensions', {})
        variables_encoded = self.dict_to_query_string(variables, use_double_quotes)
        extensions_encoded = self.dict_to_query_string(extensions, use_double_quotes)
        query_string = f"operationName={operation_name}&variables={urllib.parse.quote(variables_encoded)}&extensions={urllib.parse.quote(extensions_encoded)}"
        return query_string

    def generate_random_string(self, length=32):
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def generate_random_int(self, start, end):
        return random.randint(start, end)
    
    def fetch_client_token(self):
        return self.redis.fetch_random_key_value()["value"]
    
    async def fetch_bearer_token(self, proxy_url=None):
        try:
            request_options = {
                "follow_redirects": True,
                "timeout": 10.0,
            }
            async with httpx.AsyncClient(http2=True) as client:
                response = await client.get(
                    "https://open.spotify.com/playlist/3IyY3EphrdZfnpsrT84YBM",
                    **request_options
                )
                response.raise_for_status()
                playlist_page = response.text
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

        common_headers = {
            "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br, zstd",
            "content-type": "application/json;charset=UTF-8",
            "referer": "https://open.spotify.com",
            "origin": "https://open.spotify.com",
            "client-token": client_token,
            'Authorization': f'Bearer {self.bearer_token}'
        }
        if is_mobile_or_sp_client:
            return {
                **common_headers,
                "user-agent": f'Spotify/8.9.34.590 Android/{self.generate_random_int(27, 29)} (Pixel)',
                "spotify-app-version": "8.9.34.590",
                "x-client-id": self.generate_random_string()
            }
        return {
            **common_headers,
            "app-platform": "WebPlayer",
            "spotify-app-version": "1.2.41.273.ge0010ef5"
        }
    
    async def get_API(self, url: str, params: dict|None):
        client_token = self.fetch_client_token()
        if not client_token or not isinstance(client_token, str):
            raise ValueError("Invalid client token")

        is_mobile_or_sp_client = "spclient" in url
        headers = self.generate_headers(client_token, is_mobile_or_sp_client)
        try:
            response = await self.http_client.get(url, params=params, headers=headers)
            print(response.url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as http_err:
            print(f"HTTP error occurred: {http_err}")
            raise
        except Exception as err:
            print(f"Error in sync_get: {err}")
            raise
    
    async def process_artist_pathfinder(self, artist_key: str):
        """
        Fetch artist data and process it, including recursively processing related artists.
        """
        params = {
            "operationName": "queryArtistOverview",
            "variables": {
                "uri": f"spotify:artist:{artist_key}",
                "locale": "intl-us",
                "includePrerelease": True
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "da986392124383827dc03cbb3d66c1de81225244b6e20f8d78f9f802cc43df6e"
                }
            }
        }

        # Fetch the artist data (API call is async)
        pathfinder_json = await self.get_API(
            url=f"https://api-partner.spotify.com/pathfinder/v1/query?operationName={params['operationName']}&variables={urllib.parse.quote(json.dumps(params['variables']))}&extensions={urllib.parse.quote(json.dumps(params['extensions']))}",
            params=None
        )

        artistUnion = pathfinder_json["data"]["artistUnion"]
        profile = artistUnion["profile"]
        stats = artistUnion["stats"]
        discography = artistUnion["discography"]
        goods = artistUnion["goods"]
        relatedcontent = artistUnion["relatedContent"]
        relatedvideos = artistUnion["relatedVideos"]
        relatedartists = relatedcontent["relatedArtists"]

        self.database.insert_artist_pathfinder_over_time(artist_key, stats, profile, goods, relatedcontent, relatedartists, discography, relatedvideos)
        self.loop.create_task(self.process_artist_relations(artist_key, relatedartists, True))
        try:
            if not self.database.artist_key_exists(artist_key):

                artist_entry = self.database.insert_artist_json(artist_key=artist_key, artist_data_json={"name": profile["name"]})
                if artist_entry:
                    self.database.insert_artist_information(artist_key, pathfinder_json, artist_entry)
        except:
            pass



    async def process_artist_relations(self, artist_key: str, relatedartists: dict, spider_pathfinder_recursion: bool):
            """
            Process the artist's relations (related artists), checking if they exist in the database
            and recursively processing their relations if necessary.
            """
            related_artist_keys = [artist['id'] for artist in relatedartists['items']]
            print(related_artist_keys)

            relation_exists = self.database.find_relation_with_exact_artist_keys(artist_key, related_artist_keys)

            if not relation_exists:

                self.database.insert_artist_relations(artist_key, related_artist_keys)
            else: 
                print("relation exists")

            if spider_pathfinder_recursion:
                for key in related_artist_keys:
                    asyncio.create_task(self.process_artist_pathfinder(key))  # Fire-and-forget
    
    

    async def fetch_artist_performance_information(self, artist_key: str):
        print("Scrape Time started")
        start_time = time.time()

        try:
            params = {"fields": "listenerCount,monthlyListenerRank"}
            info = await self.get_API(f"https://spclient.wg.spotify.com/creatorabout/v0/artist/{artist_key}/about", params=params)
            print(info)

            if info.get("artistGid"):
                entry = {
                    "artist_key": artist_key,
                    "world_rank": info.get("globalChartPosition", 0),
                    "monthly_listeners": info.get("monthlyListeners"),
                    "monthly_listeners_delta": info.get("monthlyListenersDelta")
                }

                if entry["monthly_listeners_delta"]:
                    self.database.insert_artist_performance_over_time(entry)

                self.requests_sent += 1
                print("Scrape Time ended")
                print(f"Total Scrape Time: {time.time() - start_time:.2f} seconds")
                await self.refresh_client_token()
                return True
        except Exception as error:
            print(f"Error scraping artist {artist_key}: {error}")

        return False

    async def produce_client_token(self):
        try:
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

            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0',
                'accept': 'application/json',
                'accept-language': 'en-US,en;q=0.5',
                'accept-encoding': 'gzip, deflate, br',
                'referer': 'https://open.spotify.com/',
                'origin': 'https://open.spotify.com'
            }

            response = await self.http_client.post(
                "https://clienttoken.spotify.com/v1/clienttoken",
                json=body,
                headers=headers
            )

            response.raise_for_status()
            r = response.json()

            if r.get("response_type") == "RESPONSE_GRANTED_TOKEN_RESPONSE":
                token = r['granted_token']['token']
                refresh_time = r['granted_token']['refresh_after_seconds']
                self.redis.set_key(self.generate_random_string(7), token, refresh_time // 2)
                print("Produced client token")

        except httpx.HTTPStatusError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except Exception as err:
            print(f"Error producing client token: {err}")

    async def refresh_client_token(self):
        if self.requests_sent % 500 == 0:
            await self.produce_client_token()

