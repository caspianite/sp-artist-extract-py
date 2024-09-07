import time
import pika
import httpx
from urllib.parse import urlencode
from userclient import UserClient
import database
from settings import settings
class PerformanceScrapingConsumer:
    def __init__(self, database: database.DatabaseHandler, redis: database.RedisDatabaseHandler):
        self.database = database
        self.redis = redis
        self.user_client = UserClient(database, redis)
        self.stop = False

        self.start_rabbitmq_consumer('artist_performance')



    def start_rabbitmq_consumer(self, queue_name: str):
        """Start the RabbitMQ consumer for artist performance messages."""
        # Set up RabbitMQ connection and channel
        connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_conn_string))
        channel = connection.channel()
        # Ensure the queue exists
        channel.queue_declare(queue=queue_name, durable=True)
        print(f"Waiting for messages in queue: {queue_name}")
        # Prefetch count: limits the number of unacknowledged messages on the channel
        channel.basic_qos(prefetch_count=1)
        # Define callback for message consumption
        def callback(ch, method, properties, body):
            artist_key = body.decode()
            print(f"Received artist key: {artist_key}")
            if self.user_client.fetch_artist_performance_information(artist_key):
                ch.basic_ack(delivery_tag=method.delivery_tag)  # Acknowledge the message
            else:
                print(f"Failed to scrape {artist_key}, requeueing the message.")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  # Requeue the message in case of failure
        # Consume messages from the queue
        channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=False)
        # Start consuming messages
        print("Consumer started.")
        channel.start_consuming()



# Example usage
if __name__ == "__main__":
    # Initialize the consumer and start the RabbitMQ consumer loop
    db = database.DatabaseHandler()
    redis = database.RedisDatabaseHandler()
    consumer = PerformanceScrapingConsumer(db, redis)
