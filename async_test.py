import asyncio
from urllib.parse import urlencode
from async_userclient import UserClient
import database

class TestConsumer:
    def __init__(self, database: database.DatabaseHandler, redis: database.RedisDatabaseHandler):
        self.database = database
        self.redis = redis
        self.user_client = None  # Initialize later asynchronously
        self.stop = False

    async def initialize(self):
        """Initialize UserClient asynchronously."""
        self.user_client = UserClient(self.database, self.redis)
        await self.user_client.initialize()  # Initialize UserClient asynchronously

    async def process_artist(self, artist_id: str):
        """Process artist pathfinder asynchronously."""
        await self.user_client.process_artist_pathfinder(artist_id)


# Example usage in an async context
async def main():
    # Initialize the database and Redis handlers
    db = database.DatabaseHandler()
    redis = database.RedisDatabaseHandler()

    # Initialize the consumer
    consumer = TestConsumer(db, redis)
    
    # Initialize the user client asynchronously
    await consumer.initialize()
    
    # Process artist pathfinder asynchronously
    await consumer.process_artist("6dKdNHGdsBvEeNDxXV8AMP")

# Run the main async function
if __name__ == "__main__":
    asyncio.run(main())
