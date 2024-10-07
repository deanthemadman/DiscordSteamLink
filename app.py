from flask import Flask, redirect, request, jsonify
from flask_openid import OpenID
import mysql.connector

app = Flask(__name__)
oid = OpenID(app)

# MySQL configurations
app.config['MYSQL_HOST'] = 'your_mysql_host'
app.config['MYSQL_USER'] = 'your_mysql_user'
app.config['MYSQL_PASSWORD'] = os.getenv("DATABASE_PASSWORD")
app.config['MYSQL_DB'] = 'your_database_name'

# Database connection function
def get_db_connection():
    connection = mysql.connector.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB']
    )
    return connection

@app.before_first_request
def initialize_database():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_links (
            discord_uuid VARCHAR(255) PRIMARY KEY,
            steam_id VARCHAR(255) UNIQUE
        )
    """)
    connection.commit()
    cursor.close()
    connection.close()

@app.route('/link/discord', methods=['GET'])
def link_discord():
    discord_uuid = request.args.get('discord_uuid')
    steam_id = request.args.get('steam_id')

    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Check if the discord_uuid is already linked
    cursor.execute("SELECT * FROM user_links WHERE discord_uuid = %s OR steam_id = %s", (discord_uuid, steam_id))
    existing_link = cursor.fetchone()
    if existing_link:
        cursor.close()
        connection.close()
        return jsonify({"error": "Either the Discord account or Steam account is already linked."}), 400

    # Link the accounts
    cursor.execute("INSERT INTO user_links (discord_uuid, steam_id) VALUES (%s, %s)", (discord_uuid, steam_id))
    connection.commit()
    cursor.close()
    connection.close()
    
    return jsonify({"message": "Accounts linked successfully."}), 200

@app.route('/link/steam', methods=['GET'])
@oid.loginhandler
def link_steam():
    discord_uuid = request.args.get('discord_uuid')

    # Use OpenID to verify Steam account
    return oid.try_login("https://steamcommunity.com/openid/login", ask=True)

@oid.after_login
def after_login(response):
    steam_id = response.identity_url.split('/')[-1]  # Get Steam ID from URL
    discord_uuid = request.args.get('discord_uuid')

    connection = get_db_connection()
    cursor = connection.cursor()
    
    # Check if the steam_id is already linked
    cursor.execute("SELECT * FROM user_links WHERE discord_uuid = %s OR steam_id = %s", (discord_uuid, steam_id))
    existing_link = cursor.fetchone()
    if existing_link:
        cursor.close()
        connection.close()
        return jsonify({"error": "Either the Discord account or Steam account is already linked."}), 400

    # Link the accounts
    cursor.execute("INSERT INTO user_links (discord_uuid, steam_id) VALUES (%s, %s)", (discord_uuid, steam_id))
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({"message": "Accounts linked successfully."}), 200

@app.route('/unlink', methods=['POST'])
def unlink_account():
    discord_uuid = request.json.get('discord_uuid')
    steam_id = request.json.get('steam_id')

    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM user_links WHERE discord_uuid = %s OR steam_id = %s", (discord_uuid, steam_id))
    connection.commit()
    cursor.close()
    connection.close()

    return jsonify({"message": "Accounts unlinked successfully."}), 200

if __name__ == '__main__':
    app.run(ssl_context=('path/to/ssl/cert.pem', 'path/to/ssl/key.pem'), debug=True)
