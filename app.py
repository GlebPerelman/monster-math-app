# Monster Math Game - Full Stack Application
# This includes both backend (Flask) and frontend (HTML/JS)

# ============================================
# BACKEND - app.py
# ============================================

from flask import Flask, render_template_string, request, jsonify, session
from flask_cors import CORS
import sqlite3
import hashlib
import secrets
from datetime import datetime
import json

app = Flask(__name__)
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
    
    # Puzzle attempts table - stores each individual puzzle attempt
    c.execute('''CREATE TABLE IF NOT EXISTS puzzle_attempts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  timestamp_utc TIMESTAMP NOT NULL,
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
    return render_template_string(HTML_TEMPLATE)

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
    question = data.get('question')
    time_taken = data.get('time_taken_seconds')
    solved_correctly = data.get('solved_correctly')
    
    if question is None or time_taken is None or solved_correctly is None:
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # Use UTC timestamp
    timestamp_utc = datetime.utcnow().isoformat()
    
    c.execute('''INSERT INTO puzzle_attempts 
                 (user_id, timestamp_utc, question, time_taken_seconds, solved_correctly)
                 VALUES (?, ?, ?, ?, ?)''',
              (session['user_id'], timestamp_utc, question, time_taken, solved_correctly))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conn = get_db()
    c = conn.cursor()
    
    # Get overall stats
    c.execute('''SELECT 
                    COUNT(*) as total_attempts,
                    SUM(CASE WHEN solved_correctly = 1 THEN 1 ELSE 0 END) as correct_attempts,
                    AVG(time_taken_seconds) as avg_time,
                    MIN(time_taken_seconds) as best_time
                 FROM puzzle_attempts WHERE user_id = ?''',
              (session['user_id'],))
    stats = dict(c.fetchone())
    
    # Calculate accuracy
    if stats['total_attempts'] > 0:
        stats['accuracy'] = (stats['correct_attempts'] / stats['total_attempts'] * 100)
    else:
        stats['accuracy'] = 0
    
    # Get recent attempts
    c.execute('''SELECT question, time_taken_seconds, solved_correctly, timestamp_utc
                 FROM puzzle_attempts WHERE user_id = ?
                 ORDER BY timestamp_utc DESC LIMIT 20''',
              (session['user_id'],))
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


# ============================================
# FRONTEND - HTML Template
# ============================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monster Math Game</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            position: relative;
            overflow-x: hidden;
        }

        .stars {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
        }

        .star {
            position: absolute;
            color: white;
            font-size: 20px;
            animation: twinkle 3s infinite;
            opacity: 0.3;
        }

        @keyframes twinkle {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 0.8; }
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-10px); }
        }

        .container {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 600px;
            width: 90%;
            position: relative;
            z-index: 10;
            max-height: 90vh;
            overflow-y: auto;
        }

        h1 {
            text-align: center;
            color: #667eea;
            margin-bottom: 10px;
            font-size: 2.5em;
        }

        h2 {
            color: #667eea;
            margin-bottom: 20px;
        }

        .monster-header {
            text-align: center;
            font-size: 3em;
            margin-bottom: 20px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: bold;
        }

        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #667eea;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }

        input:focus {
            outline: none;
            border-color: #764ba2;
        }

        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
            margin-top: 10px;
        }

        button:hover {
            transform: scale(1.05);
        }

        button:active {
            transform: scale(0.95);
        }

        .error {
            color: #e74c3c;
            margin-top: 10px;
            text-align: center;
            font-weight: bold;
        }

        .success {
            color: #27ae60;
            margin-top: 10px;
            text-align: center;
            font-weight: bold;
        }

        .game-area {
            display: none;
        }
        
        .game-area:not(.hidden) {
            display: block !important;
        }

        .puzzle-box {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            margin: 20px 0;
            color: white;
        }

        .puzzle-equation {
            font-size: 3em;
            font-weight: bold;
            margin: 20px 0;
        }

        .monster-display {
            font-size: 3em;
            margin-bottom: 10px;
            animation: bounce 2s infinite;
        }

        .score-board {
            display: flex;
            justify-content: space-around;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .score-item {
            background: #667eea;
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            font-weight: bold;
            margin: 5px;
        }

        .timer {
            background: #f39c12;
            color: white;
            padding: 10px 20px;
            border-radius: 10px;
            font-weight: bold;
            font-size: 1.2em;
            text-align: center;
            margin-bottom: 10px;
        }

        .stats-area {
            display: none;
        }
        
        .stats-area:not(.hidden) {
            display: block !important;
        }

        .stats-table {
            width: 100%;
            margin-top: 20px;
            border-collapse: collapse;
            font-size: 14px;
        }

        .stats-table th,
        .stats-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }

        .stats-table th {
            background: #667eea;
            color: white;
        }

        .correct-row {
            background-color: #d4edda;
        }

        .incorrect-row {
            background-color: #f8d7da;
        }

        .toggle-link {
            text-align: center;
            margin-top: 15px;
            color: #667eea;
            cursor: pointer;
            text-decoration: underline;
        }

        .hidden {
            display: none !important;
        }

        .logout-btn {
            background: #e74c3c;
            margin-top: 20px;
        }

        .nav-buttons {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }

        .nav-buttons button {
            flex: 1;
        }
    </style>
</head>
<body>
    <div class="stars" id="stars"></div>

    <div class="container">
        <!-- Login/Register Area -->
        <div id="auth-area">
            <div class="monster-header">👾 👽 🛸</div>
            <h1>Monster Math</h1>
            <p style="text-align: center; color: #666; margin-bottom: 20px;">Login or Register to Play!</p>
            
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" placeholder="Enter username">
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" placeholder="Enter password">
            </div>
            
            <button onclick="login()">Login</button>
            <button onclick="register()">Register</button>
            
            <div id="auth-message"></div>
        </div>

        <!-- Game Area -->
        <div id="game-area" class="game-area hidden">
            <h1>Monster Math</h1>
            <p style="text-align: center; color: #666; margin-bottom: 10px;">Welcome, <span id="player-name"></span>!</p>
            
            <div class="timer">Time: <span id="timer">0.0</span>s</div>
            
            <div class="score-board">
                <div class="score-item">Score: <span id="score">0</span></div>
                <div class="score-item">Streak: <span id="streak">0</span></div>
                <div class="score-item">Solved: <span id="solved">0</span></div>
            </div>

            <div class="puzzle-box">
                <div class="monster-display">
                    <span id="monster">👾</span>
                    <span id="alien">👽</span>
                </div>
                <div class="puzzle-equation" id="puzzle-equation">
                    Loading...
                </div>
            </div>

            <div class="form-group">
                <input type="number" id="answer" placeholder="Enter your answer" onkeypress="handleKeyPress(event)">
            </div>

            <button onclick="checkAnswer()">Check Answer! 🚀</button>
            
            <div id="game-message"></div>

            <div class="nav-buttons">
                <button onclick="saveAndShowStats()">View Stats</button>
                <button onclick="logout()" class="logout-btn">Logout</button>
            </div>
        </div>

        <!-- Stats Area -->
        <div id="stats-area" class="stats-area hidden">
            <h2>Your Stats</h2>
            <div id="stats-content"></div>
            <button onclick="backToGame()">Back to Game</button>
        </div>
    </div>

    <script>
        let currentPuzzle = null;
        let score = 0;
        let streak = 0;
        let solved = 0;
        let puzzleStartTime = null;
        let timerInterval = null;

        const monsters = ['👾', '👽', '🛸', '🤖', '👹', '🦖', '🐲'];
        const aliens = ['👽', '🛸', '🌟', '⭐', '✨', '💫'];

        // Create stars
        function createStars() {
            const starsContainer = document.getElementById('stars');
            for (let i = 0; i < 20; i++) {
                const star = document.createElement('div');
                star.className = 'star';
                star.textContent = '⭐';
                star.style.left = Math.random() * 100 + '%';
                star.style.top = Math.random() * 100 + '%';
                star.style.animationDelay = Math.random() * 3 + 's';
                starsContainer.appendChild(star);
            }
        }

        createStars();

        // Timer functions
        function startTimer() {
            puzzleStartTime = Date.now();
            if (timerInterval) clearInterval(timerInterval);
            
            timerInterval = setInterval(() => {
                const elapsed = (Date.now() - puzzleStartTime) / 1000;
                document.getElementById('timer').textContent = elapsed.toFixed(1);
            }, 100);
        }

        function stopTimer() {
            if (timerInterval) {
                clearInterval(timerInterval);
                timerInterval = null;
            }
        }

        function getElapsedTime() {
            if (puzzleStartTime) {
                return (Date.now() - puzzleStartTime) / 1000;
            }
            return 0;
        }

        // Check session on load
        window.addEventListener('load', function() {
            fetch('/api/check_session')
                .then(r => r.json())
                .then(data => {
                    if (data.authenticated) {
                        showGame(data.username);
                    }
                })
                .catch(err => console.error('Session check failed:', err));
        });

        function generatePuzzle() {
            console.log('=== GENERATE PUZZLE CALLED ===');
            
            const operations = ['+', '-'];
            const op = operations[Math.floor(Math.random() * operations.length)];
            let num1, answer, result;

            if (op === '+') {
                result = Math.floor(Math.random() * 15) + 6;
                num1 = Math.floor(Math.random() * (result - 1)) + 1;
                answer = result - num1;
            } else {
                num1 = Math.floor(Math.random() * 15) + 6;
                answer = Math.floor(Math.random() * num1);
                result = num1 - answer;
            }

            currentPuzzle = { 
                num1, 
                op, 
                result, 
                answer,
                questionText: `${num1} ${op} ? = ${result}`
            };
            
            console.log('Puzzle created:', currentPuzzle);
            
            // Update UI
            const monsterEl = document.getElementById('monster');
            const alienEl = document.getElementById('alien');
            const equationEl = document.getElementById('puzzle-equation');
            
            console.log('Monster element:', monsterEl);
            console.log('Alien element:', alienEl);
            console.log('Equation element:', equationEl);
            
            if (monsterEl && alienEl && equationEl) {
                monsterEl.textContent = monsters[Math.floor(Math.random() * monsters.length)];
                alienEl.textContent = aliens[Math.floor(Math.random() * aliens.length)];
                equationEl.textContent = currentPuzzle.questionText;
                console.log('UI Updated successfully!');
                console.log('Monster:', monsterEl.textContent);
                console.log('Alien:', alienEl.textContent);
                console.log('Equation:', equationEl.textContent);
            } else {
                console.error('ERROR: One or more UI elements not found!');
                console.error('Missing elements:', {
                    monster: !monsterEl,
                    alien: !alienEl,
                    equation: !equationEl
                });
            }
            
            // Start timer for this puzzle
            startTimer();
            console.log('Timer started');
        }

        async function saveAttempt(question, timeTaken, solvedCorrectly) {
            try {
                await fetch('/api/save_attempt', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question: question,
                        time_taken_seconds: timeTaken,
                        solved_correctly: solvedCorrectly
                    })
                });
            } catch (err) {
                console.error('Failed to save attempt:', err);
            }
        }

        async function register() {
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            
            if (!username || !password) {
                showAuthMessage('Please enter username and password', 'error');
                return;
            }
            
            try {
                const response = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showAuthMessage('Registration successful!', 'success');
                    setTimeout(() => showGame(data.username), 500);
                } else {
                    showAuthMessage(data.error, 'error');
                }
            } catch (err) {
                showAuthMessage('Registration failed. Please try again.', 'error');
                console.error('Registration error:', err);
            }
        }

        async function login() {
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            
            if (!username || !password) {
                showAuthMessage('Please enter username and password', 'error');
                return;
            }
            
            try {
                const response = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showAuthMessage('Login successful!', 'success');
                    setTimeout(() => showGame(data.username), 500);
                } else {
                    showAuthMessage(data.error, 'error');
                }
            } catch (err) {
                showAuthMessage('Login failed. Please try again.', 'error');
                console.error('Login error:', err);
            }
        }

        function showAuthMessage(message, type) {
            const msgDiv = document.getElementById('auth-message');
            msgDiv.className = type;
            msgDiv.textContent = message;
        }

        function showGame(username) {
            console.log('=== SHOW GAME CALLED ===');
            console.log('Username:', username);
            
            const authArea = document.getElementById('auth-area');
            const gameArea = document.getElementById('game-area');
            const statsArea = document.getElementById('stats-area');
            
            console.log('Auth area:', authArea);
            console.log('Game area:', gameArea);
            console.log('Stats area:', statsArea);
            
            if (!gameArea) {
                console.error('ERROR: game-area element not found!');
                return;
            }
            
            authArea.classList.add('hidden');
            gameArea.classList.remove('hidden');
            statsArea.classList.add('hidden');
            
            console.log('Game area display:', window.getComputedStyle(gameArea).display);
            
            document.getElementById('player-name').textContent = username;
            
            // Reset game state
            score = 0;
            streak = 0;
            solved = 0;
            updateScoreBoard();
            
            console.log('About to generate puzzle...');
            // Generate first puzzle
            setTimeout(() => {
                console.log('Generating puzzle now...');
                generatePuzzle();
                const answerInput = document.getElementById('answer');
                console.log('Answer input:', answerInput);
                if (answerInput) {
                    answerInput.focus();
                }
            }, 100);
        }

        async function checkAnswer() {
            if (!currentPuzzle) {
                console.error('No puzzle generated!');
                return;
            }
            
            const answerInput = document.getElementById('answer');
            const userAnswer = parseInt(answerInput.value);
            
            if (isNaN(userAnswer)) {
                return;
            }
            
            // Stop timer and get elapsed time
            stopTimer();
            const timeTaken = getElapsedTime();
            
            const msgDiv = document.getElementById('game-message');
            const isCorrect = (userAnswer === currentPuzzle.answer);
            
            // Save attempt to database
            await saveAttempt(currentPuzzle.questionText, timeTaken, isCorrect);
            
            if (isCorrect) {
                score += 10;
                streak++;
                solved++;
                msgDiv.className = 'success';
                msgDiv.textContent = `🎉 Awesome! You got it in ${timeTaken.toFixed(1)}s!`;
                
                updateScoreBoard();
                
                setTimeout(() => {
                    answerInput.value = '';
                    msgDiv.textContent = '';
                    generatePuzzle();
                    answerInput.focus();
                }, 1500);
            } else {
                streak = 0;
                msgDiv.className = 'error';
                msgDiv.textContent = '😅 Oops! Try again!';
                updateScoreBoard();
                
                setTimeout(() => {
                    msgDiv.textContent = '';
                    startTimer(); // Restart timer for retry
                }, 1500);
            }
        }

        function updateScoreBoard() {
            document.getElementById('score').textContent = score;
            document.getElementById('streak').textContent = streak;
            document.getElementById('solved').textContent = solved;
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                checkAnswer();
            }
        }

        async function saveAndShowStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                const statsContent = document.getElementById('stats-content');
                const stats = data.stats;
                
                statsContent.innerHTML = `
                    <div class="score-board">
                        <div class="score-item">Total Attempts: ${stats.total_attempts || 0}</div>
                        <div class="score-item">Correct: ${stats.correct_attempts || 0}</div>
                        <div class="score-item">Accuracy: ${(stats.accuracy || 0).toFixed(1)}%</div>
                    </div>
                    <div class="score-board">
                        <div class="score-item">Avg Time: ${(stats.avg_time || 0).toFixed(1)}s</div>
                        <div class="score-item">Best Time: ${(stats.best_time || 0).toFixed(1)}s</div>
                    </div>
                    <h3 style="margin-top: 20px; color: #667eea;">Recent Attempts</h3>
                    <table class="stats-table">
                        <tr>
                            <th>Question</th>
                            <th>Time</th>
                            <th>Result</th>
                            <th>Timestamp</th>
                        </tr>
                        ${data.recent_attempts.map(attempt => `
                            <tr class="${attempt.solved_correctly ? 'correct-row' : 'incorrect-row'}">
                                <td>${attempt.question}</td>
                                <td>${attempt.time_taken_seconds.toFixed(1)}s</td>
                                <td>${attempt.solved_correctly ? '✅' : '❌'}</td>
                                <td>${new Date(attempt.timestamp_utc).toLocaleString()}</td>
                            </tr>
                        `).join('')}
                    </table>
                `;
                
                stopTimer(); // Stop timer when viewing stats
                document.getElementById('game-area').classList.add('hidden');
                document.getElementById('stats-area').classList.remove('hidden');
            } catch (err) {
                console.error('Failed to load stats:', err);
                alert('Failed to load statistics. Please try again.');
            }
        }

        function backToGame() {
            document.getElementById('stats-area').classList.add('hidden');
            document.getElementById('game-area').classList.remove('hidden');
            generatePuzzle();
            document.getElementById('answer').focus();
        }

        async function logout() {
            try {
                stopTimer();
                await fetch('/api/logout', { method: 'POST' });
                location.reload();
            } catch (err) {
                console.error('Logout failed:', err);
                location.reload();
            }
        }
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    print("Starting Monster Math Game Server...")
    print("Open your browser to: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)