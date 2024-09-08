import time
import pika
import httpx
from urllib.parse import urlencode
from userclient import UserClient
import database
from settings import settings
class TestConsumer:
    def __init__(self, database: database.DatabaseHandler, redis: database.RedisDatabaseHandler):
        self.database = database
        self.redis = redis
        self.user_client = UserClient(database, redis)
        self.stop = False
        self.user_client.process_artist_pathfinder("5ZTKDjtRclyhO4UW8vV6fN")




# Example usage
if __name__ == "__main__":
    # Initialize the consumer and start the RabbitMQ consumer loop
    db = database.DatabaseHandler()
    redis = database.RedisDatabaseHandler()
    consumer = TestConsumer(db, redis)
