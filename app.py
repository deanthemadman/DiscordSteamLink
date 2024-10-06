from flask import Flask, redirect, url_for, session, flash, render_template
from flask_dance.contrib.discord import make_discord_blueprint, discord
from flask_dance.contrib.steam import make_steam_blueprint, steam
from sqlalchemy import create_engine, Column, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

database_pass = os.getenv("DATABASE_PASS")
database_host = "hostname"
database_user = "rootuser"
database_name = "root"

# Database setup with MySQL
DATABASE_URL = f'mysql+mysqlconnector://{database_user}:{database_pass}@{database_host}/{database_name}'
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = SessionLocal()

# Define User model for MySQL
class User(Base):
    __tablename__ = 'users'
    discord_id = Column(String, primary_key=True, index=True)
    steam_id = Column(String, index=True)

# Create the tables if they don't exist yet
Base.metadata.create_all(bind=engine)

# Discord OAuth2 setup
discord_blueprint = make_discord_blueprint(
    client_id=os.getenv("DISCORD_CLIENT_ID"),
    client_secret=os.getenv("DISCORD_CLIENT_SECRET"),
    redirect_to="discord_login"
)
app.register_blueprint(discord_blueprint, url_prefix="/discord_login")

# Steam OAuth2 setup
steam_blueprint = make_steam_blueprint(
    api_key=os.getenv("STEAM_API_KEY"),
    redirect_to="steam_login"
)
app.register_blueprint(steam_blueprint, url_prefix="/steam_login")

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/discord_login")
def discord_login():
    if not discord.authorized:
        return redirect(url_for("discord.login"))
    
    discord_info = discord.get("/api/users/@me").json()
    discord_id = discord_info["id"]

    # Check if the Discord ID is already in the database
    user = db_session.query(User).filter_by(discord_id=discord_id).first()
    if user:
        # Notify the user that their Discord account has already been registered
        flash("This Discord account is already registered.")
        return render_template('already_registered.html')
    
    # If the user is not in the database, create a new entry for them
    new_user = User(discord_id=discord_id)
    db_session.add(new_user)
    db_session.commit()

    return redirect(url_for("steam_login"))

@app.route("/steam_login")
def steam_login():
    # Check if the user has logged into Discord
    if not discord.authorized:
        # If not, redirect them to Discord login
        return redirect(url_for("discord.login"))

    # If the user is logged in to Discord, proceed with Steam login
    if not steam.authorized:
        return redirect(url_for("steam.login"))
    
    steam_info = steam.get("/ISteamUser/GetPlayerSummaries/v0002").json()
    steam_id = steam_info["response"]["players"][0]["steamid"]

    # Ensure the session stores the user's Discord ID
    discord_info = discord.get("/api/users/@me").json()
    discord_id = discord_info["id"]

    # Store Steam ID in the database
    user = db_session.query(User).filter_by(discord_id=discord_id).first()
    if user:
        user.steam_id = steam_id
        db_session.commit()

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
