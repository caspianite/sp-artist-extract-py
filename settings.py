import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    def __init__(self):
        self.postgres_conn_string = os.getenv("POSTGRES_CONN_STRING", "")
        self.redis_conn_string = os.getenv("REDIS_CONN_STRING", "")
        self.debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
        self.debug_proxy = os.getenv("DEBUG_PROXY")
        self.rabbitmq_conn_string = os.getenv("RABBITMQ_CONN_STRING", "")
        self.send_combinations = os.getenv("SEND_COMBINATIONS", "false").lower() == "true"
        self.scrape_combinations = os.getenv("SCRAPE_COMBINATIONS", "false").lower() == "true"
        self.pathfinder_process_threads = int(os.getenv("PATHFINDER_PROCESS_THREADS", "30"))
        self.rabbitmq_user = os.getenv("RABBITMQ_USER", "guest")
        self.rabbitmq_password = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.rabbitmq_mgmt_port = os.getenv("RABBITMQ_MGMT_PORT", "15672")
        self.skip_proxy = os.getenv("SKIP_PROXY", "false").lower() == "true"

    def log_debug_info(self):
        if self.debug_mode:
            print("ON DEBUG MODE")
            print(f"Using debug proxy: {self.debug_proxy}")

# Create a settings instance
settings = Settings()

if os.getenv('NODE_ENV') == 'production':
    # Disable print statements in production
    def print(*args, **kwargs):
        pass

settings.log_debug_info()
