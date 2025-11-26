from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import sqlite3
import hashlib
import secrets
from datetime import datetime
import os

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.secret_key = secrets.token_hex(32)
CORS(app)

# Database setup
def init_db():
    conn = sqlite3.connect('math_game.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Puzzle attempts table
    c.execute('''CREATE TABLE IF NOT EXISTS puzzle_attempts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  timestamp_utc TIMESTAMP NOT NULL,
                  game_type TEXT NOT NULL,
                  question TEXT NOT NULL,
                  time_taken_seconds REAL NOT NULL,
                  solved_correctly BOOLEAN NOT NULL,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_db():
    conn = sqlite3.connect('math_game.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
init_db()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if len(password) < 4:
        return jsonify({'error': 'Password must be at least 4 characters'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    try:
        c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                  (username, hash_password(password)))
        conn.commit()
        user_id = c.lastrowid
        session['user_id'] = user_id
        session['username'] = username
        return jsonify({'success': True, 'username': username})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT id, username FROM users WHERE username = ? AND password_hash = ?',
              (username, hash_password(password)))
    user = c.fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user['id']
        session['username'] = user['username']
        return jsonify({'success': True, 'username': user['username']})
    else:
        return jsonify({'error': 'Invalid username or password'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/save_attempt', methods=['POST'])
def save_attempt():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    game_type = data.get('game_type')
    question = data.get('question')
    time_taken = data.get('time_taken_seconds')
    solved_correctly = data.get('solved_correctly')
    
    if not game_type or question is None or time_taken is None or solved_correctly is None:
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    timestamp_utc = datetime.utcnow().isoformat()
    
    c.execute('''INSERT INTO puzzle_attempts 
                 (user_id, timestamp_utc, game_type, question, time_taken_seconds, solved_correctly)
                 VALUES (?, ?, ?, ?, ?, ?)''',
              (session['user_id'], timestamp_utc, game_type, question, time_taken, solved_correctly))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    game_type = request.args.get('game_type', 'all')
    
    conn = get_db()
    c = conn.cursor()
    
    if game_type == 'all':
        where_clause = 'WHERE user_id = ?'
        params = (session['user_id'],)
    else:
        where_clause = 'WHERE user_id = ? AND game_type = ?'
        params = (session['user_id'], game_type)
    
    c.execute(f'''SELECT 
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN solved_correctly = 1 THEN 1 ELSE 0 END) as correct_attempts,
                    AVG(time_taken_seconds) as avg_time,
                    MIN(time_taken_seconds) as best_time
                 FROM puzzle_attempts {where_clause}''',
              params)
    stats = dict(c.fetchone())
    
    if stats['total_attempts'] > 0:
        stats['accuracy'] = (stats['correct_attempts'] / stats['total_attempts'] * 100)
    else:
        stats['accuracy'] = 0
    
    c.execute(f'''SELECT game_type, question, time_taken_seconds, solved_correctly, timestamp_utc
                 FROM puzzle_attempts {where_clause}
                 ORDER BY timestamp_utc DESC LIMIT 20''',
              params)
    recent_attempts = [dict(row) for row in c.fetchall()]
    
    conn.close()
    
    return jsonify({
        'stats': stats,
        'recent_attempts': recent_attempts,
        'username': session['username']
    })

@app.route('/api/check_session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({'authenticated': True, 'username': session['username']})
    return jsonify({'authenticated': False})


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)