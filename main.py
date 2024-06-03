import os
import uvicorn
import src.scheduler  # Import the scheduler module

if __name__ == "__main__":
    # Determine if running in a development environment
    is_dev = os.getenv("ENV") == "development"
    
    if is_dev:
        # For development, specify the path to the .env file
        env_file = ".env"
    else:
        # For production, set env_file to None
        env_file = None

    # Start the scheduler
    src.scheduler.start_scheduler()

    config = uvicorn.Config(
        "src.api.server:app", port=3000, log_level="info", reload=is_dev, env_file=env_file
    )
    server = uvicorn.Server(config)
    server.run()
