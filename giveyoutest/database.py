# database.py

import sqlite3
import random
import string

def get_connection():
    conn = sqlite3.connect('database.db')
    return conn

def setup_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            first_name TEXT,
            last_name TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS items (
            uuid TEXT PRIMARY KEY,
            name TEXT,
            creator_id INTEGER,
            owner_id INTEGER,
            FOREIGN KEY (creator_id) REFERENCES users(user_id),
            FOREIGN KEY (owner_id) REFERENCES users(user_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT,
            sender_id INTEGER,
            receiver_id INTEGER,
            status TEXT,
            timestamp DATETIME,
            FOREIGN KEY (uuid) REFERENCES items(uuid),
            FOREIGN KEY (sender_id) REFERENCES users(user_id),
            FOREIGN KEY (receiver_id) REFERENCES users(user_id)
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, username, first_name, last_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name))
    cursor.execute('''
        UPDATE users SET username = ?, first_name = ?, last_name = ? WHERE user_id = ?
    ''', (username, first_name, last_name, user_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_username(username):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def generate_unique_item_id():
    conn = get_connection()
    cursor = conn.cursor()
    while True:
        letters = ''.join(random.choices(string.ascii_uppercase, k=5))
        digits = ''.join(random.choices(string.digits, k=5))
        unique_id = letters + digits
        cursor.execute('SELECT uuid FROM items WHERE uuid = ?', (unique_id,))
        if not cursor.fetchone():
            break  # Уникальный ID найден
    conn.close()
    return unique_id

def add_item(item_name, creator_id, owner_id):
    conn = get_connection()
    cursor = conn.cursor()
    item_uuid = generate_unique_item_id()
    cursor.execute('INSERT INTO items (uuid, name, creator_id, owner_id) VALUES (?, ?, ?, ?)', (item_uuid, item_name, creator_id, owner_id))
    conn.commit()
    conn.close()
    return item_uuid

def get_user_items(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT uuid, name FROM items WHERE owner_id = ?', (user_id,))
    items = cursor.fetchall()
    conn.close()
    return items

def get_created_items(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT i.uuid, i.name, u.username
        FROM items i
        JOIN users u ON i.owner_id = u.user_id
        WHERE i.creator_id = ?
    ''', (user_id,))
    items = cursor.fetchall()
    conn.close()
    return items

def get_item(uuid):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM items WHERE uuid = ?', (uuid,))
    item = cursor.fetchone()
    conn.close()
    return item

def transfer_item(uuid, sender_id, receiver_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO transfers (uuid, sender_id, receiver_id, status, timestamp) VALUES (?, ?, ?, ?, datetime("now"))', (uuid, sender_id, receiver_id, 'Pending Acceptance'))
    transfer_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return transfer_id

def get_pending_transfers(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.id, i.name, u.username, t.timestamp
        FROM transfers t
        JOIN items i ON t.uuid = i.uuid
        JOIN users u ON t.sender_id = u.user_id
        WHERE t.receiver_id = ? AND t.status = "Pending Acceptance"
    ''', (user_id,))
    transfers = cursor.fetchall()
    conn.close()
    return transfers

def update_transfer_status(transfer_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE transfers SET status = ? WHERE id = ?', (status, transfer_id))
    conn.commit()
    conn.close()

def get_sent_transfers(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.id, t.uuid, i.name, u.username, t.status, t.timestamp
        FROM transfers t
        JOIN items i ON t.uuid = i.uuid
        JOIN users u ON t.receiver_id = u.user_id
        WHERE t.sender_id = ?
    ''', (user_id,))
    transfers = cursor.fetchall()
    conn.close()
    return transfers

def get_received_transfers(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.id, t.uuid, i.name, u.username, t.status, t.timestamp
        FROM transfers t
        JOIN items i ON t.uuid = i.uuid
        JOIN users u ON t.sender_id = u.user_id
        WHERE t.receiver_id = ?
    ''', (user_id,))
    transfers = cursor.fetchall()
    conn.close()
    return transfers

def get_history(uuid):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.status, t.timestamp
        FROM transfers t
        WHERE t.uuid = ?
        ORDER BY t.timestamp ASC
    ''', (uuid,))
    history = cursor.fetchall()
    conn.close()
    return history

def get_recent_contacts(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT u.user_id, u.username, u.first_name
        FROM (
            SELECT receiver_id AS contact_id, MAX(timestamp) AS last_interaction
            FROM transfers
            WHERE sender_id = ?
            GROUP BY receiver_id
            UNION
            SELECT sender_id AS contact_id, MAX(timestamp) AS last_interaction
            FROM transfers
            WHERE receiver_id = ?
            GROUP BY sender_id
        ) AS contacts
        JOIN users u ON u.user_id = contacts.contact_id
        WHERE u.username IS NOT NULL AND u.user_id != ?
        ORDER BY contacts.last_interaction DESC
        LIMIT 3
    ''', (user_id, user_id, user_id))
    contacts = cursor.fetchall()
    conn.close()
    return contacts
