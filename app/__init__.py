from flask import Flask
app = Flask(__name__)
from app import routes
from app.back import kraken, bot
