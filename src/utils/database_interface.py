import sqlite3
import mysql.connector
from mysql.connector.constants import ClientFlag

global configuration
configuration = None

# Allow main script to set config
def set_config(config):
    global configuration
    configuration = config

async def connect_to_database():
    # async Define configurations
    mysql_configs = {
        "host": configuration['mysql-host'],
        "port": configuration['mysql-port'],
        "user": configuration['mysql-user'],
        "password": configuration['mysql-password'],
        "database": configuration['mysql-database'], 
    }

    # Check if SSL is enabled
    if configuration['mysql-ssl']:
        # Add ssl configurations to connection
        mysql_configs['client_flags'] = [ClientFlag.SSL]
        mysql_configs['ssl_ca'] = configuration['mysql-cert-path']

    conn = mysql.connector.connect(**mysql_configs)

    return conn

def add_to_ringer_waitlist(email: str):
    # Connects to database
    conn = sqlite3.connect(configuration['Path-To-Database'])
    c = conn.cursor()

    # Execute a SELECT query to check if the entry exists
    c.execute("SELECT * FROM Ringer WHERE email = ?", (email,))
    result = c.fetchone()

    if result == None:
        conn.execute("INSERT INTO Ringer (email) VALUES (?)", (email,))

    conn.commit()
    conn.close()

    return "OK"

def fetch_all_ringer_waitlist():
    # Connects to database
    conn = sqlite3.connect(configuration['Path-To-Database'])
    c = conn.cursor()

    # Gets all data from the database
    c.execute("SELECT * FROM Ringer")
    items = c.fetchall()

    return items

class credentials:
    async def create_credentials(name: str, client_id: str, client_secret_hash: str, secret_salt: str):
        conn = await connect_to_database()
        cursor = conn.cursor()

        # Add credentials to database
        cursor.execute(
            "INSERT INTO credentials (name, client_id, client_secret, secret_salt) VALUES (%s, %s, %s, %s);", 
            (name, client_id, client_secret_hash, secret_salt)
        )
        conn.commit()
        conn.close()

    async def remove_credentials(client_id: str):
        conn = await connect_to_database()
        cursor = conn.cursor()

        # Delete credentials
        cursor.execute("DELETE FROM credentials WHERE client_id = %s;", (client_id,))

        # Delete all permissions associated with those credentials
        cursor.execute("DELETE FROM permissions WHERE client_id = %s;", (client_id,))

        conn.commit()
        conn.close()

    async def get_credentials(client_id):
        conn = await connect_to_database()
        cursor = conn.cursor()

        cursor.execute("SELECT name, client_id, client_secret, secret_salt FROM credentials WHERE client_id = %s;",
                       (client_id,))
        data = cursor.fetchone()
        conn.close()

        if data:
            return {
                "name": data[0],
                "client_id": data[1],
                "client_secret_hash": data[2],
                "secret_salt": data[3]
            }
        else:
            return None

class permissions:
    async def add_permissions(permissions: list, client_id: str):
        conn = await connect_to_database()
        cursor = conn.cursor()

        for permission in permissions:
            cursor.execute("INSERT INTO permissions (client_id, permission_node) VALUES (%s, %s);",
                           (client_id, permission))
        conn.commit()
        conn.close()

    async def remove_permissions(permissions: list, client_id: str):
        conn = await connect_to_database()
        cursor = conn.cursor()

        for permission in permissions:
            cursor.execute("DELETE FROM permissions WHERE client_id = %s AND permission_node = %s;",
                           (client_id, permission))
        conn.commit()
        conn.close()

    async def get_permissions(client_id: str):
        conn = await connect_to_database()
        cursor = conn.cursor()

        cursor.execute("SELECT permission_node FROM permissions WHERE client_id = %s;",
                       (client_id,))
        data = cursor.fetchall()
        conn.close()

        format_data = []

        for node in data:
            format_data.append(node[0])

        return format_data