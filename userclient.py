import datetime
import json
import random
import re
import string
import time
import pika.connection
import database
from settings import settings
import httpx, urllib
import pika

class UserClient():
    def __init__(self, database: database.DatabaseHandler, redis: database.RedisDatabaseHandler, rabbitmqConnection: pika.BlockingConnection) -> None:
        self.database = database
        self.http_client = httpx.Client(http2=True, follow_redirects=True, verify=False, proxy=random.choice(self.database.proxies))
        self.redis = redis
        self.requests_sent = 0
        self.bearer_token = self.fetch_bearer_token()
        self.connection = rabbitmqConnection
        self.artist_indexing_channel = None
        self.init_lateral_channels()
        self.mq_artists_sent = []
        self.mq_artists_sent_last_cleared = datetime.datetime.now()

    def send_artist_for_index(self, artist_key):
        time_since_last_cleared = datetime.datetime.now() - self.mq_artists_sent_last_cleared
        if time_since_last_cleared.total_seconds() > 120:  # 5 minutes = 300 seconds
            self.mq_artists_sent.clear()
            self.mq_artists_sent_last_cleared = datetime.datetime.now()

        if artist_key not in self.mq_artists_sent:

            self.mq_publish_message(self.artist_indexing_channel, 'sp_artist_pathfinder_index', artist_key)
            self.mq_artists_sent.append(artist_key)

    def convert_to_unix_timestamp(self, date_pathfinder_dict: dict):
        # Extract day, month, and year from the input date
        day = date_pathfinder_dict["day"]
        month = date_pathfinder_dict["month"]
        year = date_pathfinder_dict["year"]

        # Create a datetime object (set time to 00:00:00 by default)
        dt = datetime.datetime(year, month, day)

        # Convert the datetime object to a Unix timestamp (seconds since epoch)
        unix_timestamp = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())

        return unix_timestamp


    def convert_bools_for_encoding(self, d):
        if isinstance(d, dict):
            return {k: self.convert_bools_for_encoding(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [self.convert_bools_for_encoding(v) for v in d]
        elif isinstance(d, bool):
            # Return actual booleans as true or false, not as strings
            return d
        else:
            return d

    def dict_to_query_string(self, d, use_double_quotes=True):
        """
        Converts a dictionary to a query string, ensuring boolean values are not quoted.
        """
        items = []
        for k, v in d.items():
            if isinstance(v, dict):
                v = str(v).replace("'", '"') if use_double_quotes else str(v)
            elif isinstance(v, bool):
                v = 'true' if v else 'false'
            items.append(f"{k}={urllib.parse.quote(str(v))}")
        return '&'.join(items)

    def dict_to_json_query_string(self, params: dict) -> str:
        """
        Converts a dictionary to a JSON-like query string and URL-encodes it.

        Args:
        - params (dict): The dictionary to convert.

        Returns:
        - str: The JSON-encoded query string.
        """
        # Convert the dictionary to a JSON string
        json_string = json.dumps(params, separators=(',', ':'))

        # URL-encode the JSON string
        encoded_string = urllib.parse.quote(json_string)

        return encoded_string



    def encode_query_string(self, params: dict, operation_name: str, use_double_quotes: bool = True) -> str:
        """
        Encodes a single dictionary containing 'variables' and 'extensions' into a URL query string 
        with the option to use double quotes (%22) or single quotes (%27). Allows for custom operation names,
        and ensures booleans are represented as true or false (without quotes) in the query string.

        Args:
        - params (dict): A dictionary containing 'variables' and 'extensions' as keys.
        - operation_name (str): The operation name to be included in the query string.
        - use_double_quotes (bool): If True, use double quotes (%22), else use single quotes (%27).

        Returns:
        - str: The encoded query string.
        """
        # Convert booleans and prepare params for encoding
        params_for_encoding = self.convert_bools_for_encoding(params)

        # Extract 'variables' and 'extensions' from the provided params dictionary
        variables = params_for_encoding.get('variables', {})
        extensions = params_for_encoding.get('extensions', {})

        # Encode the variables and extensions using the helper function
        variables_encoded = self.dict_to_query_string(variables, use_double_quotes)
        extensions_encoded = self.dict_to_query_string(extensions, use_double_quotes)

        # Construct the final query string
        query_string = f"operationName={operation_name}&variables={urllib.parse.quote(variables_encoded)}&extensions={urllib.parse.quote(extensions_encoded)}"

        return query_string

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
                #print("Fetched bearer token:", bearer)
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
            "user-agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0',
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
        try:

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


            # Convert variables and extensions to JSON and URL-encode them
            operation_name = params['operationName']
            variables_encoded = urllib.parse.quote(json.dumps(params['variables']))
            extensions_encoded = urllib.parse.quote(json.dumps(params['extensions']))

            pathfinder_json = self.get_API(url=f"https://api-partner.spotify.com/pathfinder/v1/query?operationName={operation_name}&variables={variables_encoded}&extensions={extensions_encoded}", params=None)
            #print(pathfinder_json)

            artistUnion = pathfinder_json["data"]["artistUnion"]
            #print(artistUnion)
            profile = artistUnion["profile"]
            stats = artistUnion["stats"]
            discography = artistUnion["discography"]
            goods = artistUnion["goods"]
            relatedcontent = artistUnion["relatedContent"]
            relatedvideos = artistUnion["relatedVideos"]
            relatedartists = relatedcontent["relatedArtists"]
            self.database.insert_artist_pathfinder_over_time(artist_key, stats, profile, goods, relatedcontent, relatedartists, discography, relatedvideos)
            related_artist_keys = [artist['id'] for artist in relatedartists['items']]
            self.process_artist_relations(artist_key, relatedartists)
            for key in related_artist_keys:
                self.send_artist_for_index(key)
            try:
                if not self.database.artist_key_exists(artist_key):

                    artist_entry = self.database.insert_artist_json(artist_key=artist_key, artist_data_json={"name": profile["name"]})
                    if artist_entry:
                        self.database.insert_artist_information(artist_key, pathfinder_json, artist_entry)
            except:
                pass
            self.process_discography_items(artist_key, discography)
            return True
        except Exception as err:
            print(err)
            return False


    def process_artist_relations(self, artist_key: str, relatedartists: dict):
        related_artist_keys = [artist['id'] for artist in relatedartists['items']]
        print(related_artist_keys)
        if not self.database.find_relation_with_exact_artist_keys(artist_key, related_artist_keys):
            self.database.insert_artist_relations(artist_key, related_artist_keys)
        else:
            print("artist relations already existing")
        
    def process_album(self, artist_key: str, album: dict):
        time_release = self.convert_to_unix_timestamp(album["date"])
        name = album["name"]
        label = album["label"]
        artist_key = artist_key
        album_key = album["id"]
        tracks_count = album["tracks"]["totalCount"]

        self.database.insert_album({
            "time_release": time_release,
            "album_key": album_key,
            "artist_key": artist_key,
            "name": name,
            "tracks_count": tracks_count,
            "pathfinder_json": album,
            "label": label
        })

    def process_track(self, artist_key: str, track: dict): #track is case sens
        if track.get("uid"):
            track = track["track"]
        track_key = track["id"]
        name = track["name"]
        artists = track["artists"]["items"]
        duration = track["duration"]["totalMilliseconds"]
        playcount = int(track["playcount"])
        album_key = track["albumOfTrack"]["uri"].split(":album:")[1]
        content_rating = track["contentRating"]

        self.database.insert_track({
            "track_key": track_key, "album_key": album_key, "name": name, "playcount": playcount,
            "artists": artists, "content_rating": content_rating
        })

        for artist in artists:
            self.mq_publish_message(self.artist_indexing_channel, 'sp_artist_pathfinder_index', artist["uri"].split(":artist:")[1])

        

    def process_discography_items(self, artist_key: str, discography: dict):
        processed_ids = []
        albums = discography["albums"]

        # Process albums
        if albums["totalCount"] > 0:
            for album in albums["items"]:
                releases = album["releases"]["items"]
                for release in releases:
                    # Check if it is an album and if the ID is not already processed
                    if "album" in release["uri"] and release["uri"].split(":")[-1] not in processed_ids:
                        self.process_album(artist_key, release)
                        processed_ids.append(release["id"])

        # Process singles
        singles = discography["singles"]
        if singles["totalCount"] > 0:
            for single in singles["items"]:
                releases = single["releases"]["items"]
                for release in releases:
                    # Process albums in singles
                    if "album" in release["uri"] and release["uri"].split(":")[-1] not in processed_ids:
                        self.process_album(artist_key, release)
                        processed_ids.append(release["id"])

                    # Process tracks in singles
                    if "track" in release["uri"] and release["uri"].split(":")[-1] not in processed_ids:
                        self.process_track(artist_key, release)
                        processed_ids.append(release["id"])

        # Process top tracks
        top_tracks = discography["topTracks"]
        if len(top_tracks["items"]) > 0:
            for top_track in top_tracks["items"]:
                release = top_track["track"]
                if "track" in release["uri"] and release["uri"].split(":")[-1] not in processed_ids:
                    self.process_track(artist_key, release)
                    processed_ids.append(release["id"])

        
        
    
        
        

        
        
    
        
        
        
        
        
        
        









        
    
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
    
    def init_lateral_channels(self):
        self.artist_indexing_channel = self.connection.channel()
        self.artist_indexing_channel.queue_declare('sp_artist_pathfinder_index')

    def mq_publish_message(self, channel, queue, message):
        # Publish a message to the specified channel and queue
        channel.basic_publish(exchange='',
                              routing_key=queue,
                              body=message)
        print(f" [x] Sent '{message}' to {queue}")


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

