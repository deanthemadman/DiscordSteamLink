import os
import requests
from flask import Flask, redirect, url_for, session, jsonify, request
from flask_dance.contrib.discord import make_discord_blueprint
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
db = SQLAlchemy(app)

# Discord OAuth setup
discord_bp = make_discord_blueprint(
    client_id=os.getenv('DISCORD_CLIENT_ID'),
    client_secret=os.getenv('DISCORD_CLIENT_SECRET'),
    redirect_to='discord.login'
)
app.register_blueprint(discord_bp, url_prefix='/discord')

# Create a model for your user data
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discord_id = db.Column(db.String(255), unique=True)
    steam_id = db.Column(db.String(255), unique=True)

# Route for index
@app.route('/')
def index():
    return '<a href="/discord/login">Login with Discord</a> <br><a href="/login/steam">Login with Steam</a>'

# Route for Discord login
@app.route('/discord/login')
def discord_login():
    if not discord_bp.session.authorized:
        return redirect(url_for('discord.login'))

    resp = discord_bp.session.get('users/@me')
    assert resp.ok, resp.text
    user_info = resp.json()

    discord_id = user_info['id']

    # Check if user already exists in the database
    existing_user = User.query.filter_by(discord_id=discord_id).first()
    if existing_user:
        return f'User already exists: {user_info["username"]}'

    # Add new user to the database
    new_user = User(discord_id=discord_id)
    db.session.add(new_user)
    db.session.commit()

    return f'Logged in as: {user_info["username"]}'

# Steam OpenID setup
STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"

@app.route('/login/steam')
def login_steam():
    return redirect(get_steam_openid_url())

def get_steam_openid_url():
    return f'{STEAM_OPENID_URL}?openid.ns=http://specs.openid.net/auth/2.0&openid.mode=checkid_setup&openid.return_to=http://localhost:8000/auth/steam/callback&openid.identity=http://specs.openid.net/auth/2.0/identifier_select&openid.claimed_id=http://specs.openid.net/auth/2.0/identifier_select'

@app.route('/auth/steam/callback')
def steam_callback():
    steam_id = request.args.get('steamid')
    
    if not steam_id:
        return 'No Steam ID returned from authentication.'

    user_info = get_steam_user_info(steam_id)

    # Check if the Steam ID exists in the database
    existing_user = User.query.filter_by(steam_id=steam_id).first()
    if existing_user:
        return f'User already exists with Steam ID: {steam_id}'

    # Add new user to the database
    new_user = User(steam_id=steam_id)
    db.session.add(new_user)
    db.session.commit()

    return f'Steam User ID: {user_info["steamid"]}'

def get_steam_user_info(steam_id):
    url = f'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/'
    params = {
        'key': os.getenv('STEAM_API_KEY'),
        'steamids': steam_id
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        return data['response']['players'][0]  # Returns user data
    else:
        print("Error:", response.status_code)
        return None

if __name__ == '__main__':
    # Create the database tables if they don't exist
    with app.app_context():
        db.create_all()

    app.run(host='0.0.0.0', port=8000)
