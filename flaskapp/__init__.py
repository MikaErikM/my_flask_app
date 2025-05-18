from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Creating your flaskapp instance
app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')

# Configuring the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'

# Add engine options for SQLite timeout
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'timeout': 15}  # Timeout in seconds
}

# Creating a SQLAlchemy database instance
db = SQLAlchemy(app)

app.app_context().push()

# Import routes after app and db are initialized to avoid circular imports
from flaskapp import routes

# Optional: Setup basic logging if you haven't already for app.logger to work well
import logging
if not app.debug: 
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    app.logger.addHandler(stream_handler)
app.logger.setLevel(logging.INFO) # Set a default logging level
app.logger.info('Flask app initialized with enhanced SQLite settings.')