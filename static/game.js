// FILE: static/game.js

let currentPuzzle = null;
let currentGameType = null;
let score = 0;
let streak = 0;
let solved = 0;
let puzzleStartTime = null;
let timerInterval = null;
let currentUsername = null;

const monsters = ['👾', '👽', '🛸', '🤖', '👹', '🦖', '🐲'];
const aliens = ['👽', '🛸', '🌟', '⭐', '✨', '💫'];

// Number pad functions
function addNumber(num) {
    const answerInput = document.getElementById('answer');
    const currentValue = answerInput.value;
    
    // Limit to reasonable length
    if (currentValue.length < 4) {
        answerInput.value = currentValue + num;
    }
}

function deleteNumber() {
    const answerInput = document.getElementById('answer');
    answerInput.value = answerInput.value.slice(0, -1);
}

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
                currentUsername = data.username;
                showGameSelect(data.username);
            }
        })
        .catch(err => console.error('Session check failed:', err));
});

function generatePuzzle() {
    console.log('=== GENERATE PUZZLE CALLED ===');
    
    if (currentGameType === 'missing_number') {
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
    } else if (currentGameType === 'more_or_less') {
        const questionTypes = [
            'more_than',      // "2 more than 15" = 17
            'less_than',      // "3 less than 20" = 17
            'is_more_than'    // "18 is 2 more than ?" = 16
        ];
        
        const type = questionTypes[Math.floor(Math.random() * questionTypes.length)];
        let baseNum, difference, answer, questionText;
        
        if (type === 'more_than') {
            // "X more than Y" = Y + X
            baseNum = Math.floor(Math.random() * 15) + 5;  // 5-19
            difference = Math.floor(Math.random() * 5) + 1;  // 1-5
            answer = baseNum + difference;
            questionText = `${difference} more than ${baseNum}`;
        } else if (type === 'less_than') {
            // "X less than Y" = Y - X
            baseNum = Math.floor(Math.random() * 15) + 10;  // 10-24
            difference = Math.floor(Math.random() * 5) + 1;  // 1-5
            answer = baseNum - difference;
            questionText = `${difference} less than ${baseNum}`;
        } else {
            // "X is Y more/less than ?" 
            const isMore = Math.random() > 0.5;
            const resultNum = Math.floor(Math.random() * 15) + 10;  // 10-24
            difference = Math.floor(Math.random() * 5) + 1;  // 1-5
            
            if (isMore) {
                answer = resultNum - difference;
                questionText = `${resultNum} is ${difference} more than`;
            } else {
                answer = resultNum + difference;
                questionText = `${resultNum} is ${difference} less than`;
            }
        }
        
        currentPuzzle = {
            answer,
            questionText
        };
    } else if (currentGameType === 'part_whole') {
        // Generate part-whole puzzle
        // Whole = Part1 + Part2
        const whole = Math.floor(Math.random() * 15) + 6;  // 6-20
        const part1 = Math.floor(Math.random() * (whole - 1)) + 1;  // 1 to whole-1
        const part2 = whole - part1;
        
        // Randomly decide which number is missing (0=whole, 1=part1, 2=part2)
        const missingPosition = Math.floor(Math.random() * 3);
        
        let topValue, leftValue, rightValue, answer, questionText;
        
        if (missingPosition === 0) {
            // Missing whole
            topValue = '?';
            leftValue = part1;
            rightValue = part2;
            answer = whole;
            questionText = `Find the whole`;
        } else if (missingPosition === 1) {
            // Missing part1
            topValue = whole;
            leftValue = '?';
            rightValue = part2;
            answer = part1;
            questionText = `Find the missing part`;
        } else {
            // Missing part2
            topValue = whole;
            leftValue = part1;
            rightValue = '?';
            answer = part2;
            questionText = `Find the missing part`;
        }
        
        currentPuzzle = {
            answer,
            questionText,
            topValue,
            leftValue,
            rightValue
        };
    }
    
    console.log('Puzzle created:', currentPuzzle);
    
    // Update UI
    const monsterEl = document.getElementById('monster');
    const alienEl = document.getElementById('alien');
    const equationEl = document.getElementById('puzzle-equation');
    const partWholeDiagram = document.getElementById('part-whole-diagram');
    
    console.log('Equation element:', equationEl);
    console.log('Part-whole diagram:', partWholeDiagram);
    console.log('Current game type:', currentGameType);
    
    if (currentGameType === 'part_whole') {
        // Show diagram, hide equation text
        console.log('Setting up part-whole diagram...');
        if (equationEl) {
            equationEl.classList.add('hidden');
            console.log('Equation hidden');
        }
        if (partWholeDiagram) {
            partWholeDiagram.classList.remove('hidden');
            console.log('Diagram shown');
            document.getElementById('top-circle-text').textContent = currentPuzzle.topValue;
            document.getElementById('left-circle-text').textContent = currentPuzzle.leftValue;
            document.getElementById('right-circle-text').textContent = currentPuzzle.rightValue;
            console.log('Circle values set:', currentPuzzle.topValue, currentPuzzle.leftValue, currentPuzzle.rightValue);
        } else {
            console.error('Part-whole diagram element not found!');
        }
    } else {
        // Show equation text, hide diagram
        console.log('Setting up text equation...');
        if (partWholeDiagram) {
            partWholeDiagram.classList.add('hidden');
        }
        if (equationEl) {
            equationEl.classList.remove('hidden');
            equationEl.textContent = currentPuzzle.questionText;
        }
    }
    
    if (monsterEl && alienEl) {
        monsterEl.textContent = monsters[Math.floor(Math.random() * monsters.length)];
        alienEl.textContent = aliens[Math.floor(Math.random() * aliens.length)];
    }
    
    console.log('UI Updated successfully!');
    
    // Start timer for this puzzle
    startTimer();
}

async function saveAttempt(question, timeTaken, solvedCorrectly) {
    try {
        await fetch('/api/save_attempt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                game_type: currentGameType,
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
            currentUsername = data.username;
            setTimeout(() => showGameSelect(data.username), 500);
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
            currentUsername = data.username;
            setTimeout(() => showGameSelect(data.username), 500);
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

function showGameSelect(username) {
    console.log('=== SHOW GAME SELECT CALLED ===');
    console.log('Username:', username);
    
    const authArea = document.getElementById('auth-area');
    const gameSelectArea = document.getElementById('game-select-area');
    const gameArea = document.getElementById('game-area');
    const statsArea = document.getElementById('stats-area');
    
    console.log('Auth area:', authArea);
    console.log('Game select area:', gameSelectArea);
    console.log('Game area:', gameArea);
    console.log('Stats area:', statsArea);
    
    if (!gameSelectArea) {
        console.error('ERROR: game-select-area not found!');
        return;
    }
    
    authArea.classList.add('hidden');
    gameSelectArea.classList.remove('hidden');
    gameArea.classList.add('hidden');
    statsArea.classList.add('hidden');
    
    console.log('Game select display:', window.getComputedStyle(gameSelectArea).display);
    console.log('Game select visibility:', window.getComputedStyle(gameSelectArea).visibility);
    
    const playerNameEl = document.getElementById('select-player-name');
    if (playerNameEl) {
        playerNameEl.textContent = username;
        console.log('Player name set:', username);
    } else {
        console.error('ERROR: select-player-name element not found!');
    }
}

function startGame(gameType) {
    console.log('Starting game:', gameType);
    currentGameType = gameType;
    
    document.getElementById('game-select-area').classList.add('hidden');
    document.getElementById('game-area').classList.remove('hidden');
    document.getElementById('stats-area').classList.add('hidden');
    
    // Reset game state
    score = 0;
    streak = 0;
    solved = 0;
    updateScoreBoard();
    
    // Generate first puzzle
    setTimeout(() => {
        generatePuzzle();
        // Don't focus on input since we're using number pad
    }, 100);
}

function backToGameSelect() {
    stopTimer();
    document.getElementById('game-area').classList.add('hidden');
    document.getElementById('game-select-area').classList.remove('hidden');
}

async function checkAnswer() {
    if (!currentPuzzle) {
        console.error('No puzzle generated!');
        return;
    }
    
    const answerInput = document.getElementById('answer');
    const userAnswer = parseInt(answerInput.value);
    
    if (isNaN(userAnswer) || answerInput.value === '') {
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
        msgDiv.textContent = `🎉 Correct in ${timeTaken.toFixed(1)}s!`;
        
        updateScoreBoard();
        
        setTimeout(() => {
            answerInput.value = '';
            msgDiv.textContent = '';
            generatePuzzle();
        }, 1500);
    } else {
        streak = 0;
        msgDiv.className = 'error';
        msgDiv.textContent = '😅 Try again!';
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
    } else if (event.key >= '0' && event.key <= '9') {
        addNumber(parseInt(event.key));
        event.preventDefault();
    } else if (event.key === 'Backspace' || event.key === 'Delete') {
        deleteNumber();
        event.preventDefault();
    }
}

async function saveAndShowStats() {
    try {
        const response = await fetch(`/api/stats?game_type=${currentGameType || 'all'}`);
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
                    <th>Game Type</th>
                    <th>Question</th>
                    <th>Time</th>
                    <th>Result</th>
                </tr>
                ${data.recent_attempts.map(attempt => `
                    <tr class="${attempt.solved_correctly ? 'correct-row' : 'incorrect-row'}">
                        <td>${attempt.game_type}</td>
                        <td>${attempt.question}</td>
                        <td>${attempt.time_taken_seconds.toFixed(1)}s</td>
                        <td>${attempt.solved_correctly ? '✅' : '❌'}</td>
                    </tr>
                `).join('')}
            </table>
        `;
        
        stopTimer();
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
}

// Add keyboard support
document.addEventListener('keydown', function(event) {
    // Only handle keys when in game area and not in an input field
    const gameArea = document.getElementById('game-area');
    if (!gameArea.classList.contains('hidden') && 
        document.activeElement.tagName !== 'INPUT') {
        
        if (event.key >= '0' && event.key <= '9') {
            addNumber(parseInt(event.key));
            event.preventDefault();
        } else if (event.key === 'Backspace' || event.key === 'Delete') {
            deleteNumber();
            event.preventDefault();
        } else if (event.key === 'Enter') {
            checkAnswer();
            event.preventDefault();
        }
    }
});

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