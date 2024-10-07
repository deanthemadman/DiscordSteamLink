from flask import Flask, redirect, url_for, session, request
import requests
import mysql.connector
from flask_session import Session
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Flask session configuration
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# MySQL connection setup using environment variables
db = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE")
)
cursor = db.cursor()

# Discord OAuth2 credentials from environment variables
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")

# Steam OAuth2 credentials from environment variables
STEAM_API_KEY = os.getenv("STEAM_API_KEY")
STEAM_REDIRECT_URI = os.getenv("STEAM_REDIRECT_URI")

# Routes

@app.route('/')
def index():
    return """
    <h1>Welcome</h1>
    <p><a href='/login/discord'>Login with Discord</a></p>
    <p><a href='/login/steam'>Login with Steam</a></p>
    """

@app.route('/login/discord')
def login_discord():
    discord_auth_url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify"
    return redirect(discord_auth_url)

@app.route('/login/steam')
def login_steam():
    steam_auth_url = f"https://steamcommunity.com/openid/login"
    return redirect(steam_auth_url)

@app.route('/discord/callback')
def discord_callback():
    code = request.args.get('code')
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI
    }
    
    # Exchange code for Discord access token
    token_response = requests.post('https://discord.com/api/oauth2/token', data=data)
    token_json = token_response.json()
    access_token = token_json['access_token']

    # Fetch user info from Discord
    user_response = requests.get('https://discord.com/api/users/@me', headers={
        'Authorization': f'Bearer {access_token}'
    })
    discord_user = user_response.json()

    discord_id = discord_user['id']
    
    session['discord_id'] = discord_id
    
    # Check if user exists in database
    cursor.execute("SELECT * FROM users WHERE discord_id=%s", (discord_id,))
    result = cursor.fetchone()

    if result:
        return "Discord account already linked."
    elif 'steam_id' in session:
        # Link Discord ID with the existing Steam ID
        steam_id = session['steam_id']
        cursor.execute("INSERT INTO users (discord_id, steam_id) VALUES (%s, %s)", (discord_id, steam_id))
        db.commit()
        return "Successfully linked Discord and Steam!"
    else:
        return "Discord login successful. Now link your Steam account <a href='/login/steam'>here</a>."

@app.route('/steam/callback')
def steam_callback():
    # Steam OpenID validation flow
    # For simplification purposes, let’s assume we’ve already verified the OpenID response.
    
    steam_id = "user_steam_id_from_openid"
    
    session['steam_id'] = steam_id
    
    # Check if user exists in database
    cursor.execute("SELECT * FROM users WHERE steam_id=%s", (steam_id,))
    result = cursor.fetchone()

    if result:
        return "Steam account already linked."
    elif 'discord_id' in session:
        # Link Steam ID with the existing Discord ID
        discord_id = session['discord_id']
        cursor.execute("INSERT INTO users (discord_id, steam_id) VALUES (%s, %s)", (discord_id, steam_id))
        db.commit()
        return "Successfully linked Steam and Discord!"
    else:
        return "Steam login successful. Now link your Discord account <a href='/login/discord'>here</a>."

# Run Flask App
if __name__ == '__main__':
    app.run(debug=True)
