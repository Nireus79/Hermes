from flask import Flask
from flaskwebgui import FlaskUI

app = Flask(__name__, template_folder="templates", static_folder='static')

from app import routes
from app.back import kraken, bot

ui = FlaskUI(app)
