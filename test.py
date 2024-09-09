#import time
import pika
#import httpx
from urllib.parse import urlencode
from userclient import UserClient
import database
from settings import settings
class TestConsumer:
    def __init__(self, database: database.DatabaseHandler, redis: database.RedisDatabaseHandler, rabbitmq):
        self.database = database
        self.redis = redis
        self.user_client = UserClient(database, redis, rabbitmq)
        self.stop = False
        self.user_client.process_artist_pathfinder("2nVix2vo1cXOBj9iLHWta3")




# Example usage
if __name__ == "__main__":
    # Initialize the consumer and start the RabbitMQ consumer loop
    db = database.DatabaseHandler()
    redis = database.RedisDatabaseHandler()
    rabbitmq = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_conn_string))
    consumer = TestConsumer(db, redis, rabbitmq)
