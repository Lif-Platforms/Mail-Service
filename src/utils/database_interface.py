import yaml
import sqlite3

# Loads Config
with open("config.yml", "r") as config:
    configuration = yaml.safe_load(config)

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