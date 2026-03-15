from flask import Flask, render_template, request, jsonify
from groq import Groq
import os
from dotenv import load_dotenv
import sqlite3
from datetime import datetime
from functools import wraps
import time
import random

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Load multiple API keys from environment
API_KEYS = [
    os.getenv('GROQ_API_KEY_1'),
    os.getenv('GROQ_API_KEY_2'),
    os.getenv('GROQ_API_KEY_3'),
]

# Filter out None keys
API_KEYS = [key for key in API_KEYS if key is not None]

if not API_KEYS:
    raise ValueError("No Groq API keys found. Set GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3 in .env")

# Track current key index
current_key_index = 0

def get_groq_client():
    """Get Groq client with current API key"""
    global current_key_index
    api_key = API_KEYS[current_key_index]
    return Groq(api_key=api_key)

def rotate_api_key():
    """Switch to next API key"""
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    print(f"Switched to API key {current_key_index + 1}/{len(API_KEYS)}")

# Database initialization
def init_db():
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS notes
                 (id INTEGER PRIMARY KEY, topic TEXT, level TEXT, program TEXT, 
                  content TEXT, timestamp DATETIME, ip_address TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS requests
                 (ip_address TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

init_db()

# Rate limiting decorator
def rate_limit(max_requests=10, window=3600):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr
            conn = sqlite3.connect('notes.db')
            c = conn.cursor()
            
            # Get requests from this IP in the last hour
            c.execute('SELECT COUNT(*) FROM requests WHERE ip_address = ? AND timestamp > datetime("now", "-1 hour")',
                     (ip,))
            count = c.fetchone()[0]
            
            conn.close()
            
            if count >= max_requests:
                return jsonify({'error': 'Rate limit exceeded. Try again later.'}), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
@rate_limit(max_requests=10, window=3600)
def generate_notes():
    data = request.json
    topic = data.get('topic', '').strip()
    level = data.get('level', '').strip()
    program = data.get('program', '').strip()
    
    # Validate input
    if not topic or not level or not program:
        return jsonify({'error': 'All fields are required'}), 400
    
    if len(topic) > 200:
        return jsonify({'error': 'Topic too long (max 200 characters)'}), 400
    
    # Check cache
    conn = sqlite3.connect('notes.db')
    c = conn.cursor()
    c.execute('SELECT content FROM notes WHERE topic = ? AND level = ? AND program = ?',
             (topic, level, program))
    cached = c.fetchone()
    
    if cached:
        conn.close()
        return jsonify({'notes': cached[0], 'cached': True})
    
    # Generate notes using Groq
    try:
        prompt = f"""Create detailed, exam-ready study notes for {level} {program} students on: {topic}

MANDATORY STRUCTURE - FOLLOW EXACTLY:

## 1. CORE DEFINITIONS & FORMULAS
List ALL mathematical formulas, equations, and definitions relevant to {topic}. Write them clearly with variable explanations.

## 2. WORKED EXAMPLES (MINIMUM 4 COMPLETE EXAMPLES)
For each example:
- State the problem clearly
- Show EVERY calculation step
- Explain the reasoning
- Write the final answer
- Include different difficulty levels (Basic → Advanced)

Example format:
Problem: [Clear problem statement]
Solution:
  Step 1: [First action]
  Step 2: [Second action]
  ...
  Answer: [Final result]

## 3. DETAILED EXPLANATIONS
- Break down how each formula works
- Explain when to use each concept
- Show relationships between concepts

## 4. PRACTICE PROBLEMS WITH SOLUTIONS
Create 8-10 problems:
- Label each as Easy/Medium/Hard
- Provide complete solutions
- Show all working

## 5. COMMON ERRORS & HOW TO AVOID THEM
- List specific mistakes students make
- Explain why they're wrong
- Show correct approach

## 6. REAL-WORLD APPLICATIONS IN {program}
- Concrete examples from industry
- How professionals use this

CRITICAL: Include actual numerical examples, complete calculations, and step-by-step breakdowns. Be specific, not general."""

        client = get_groq_client()
        message = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        notes_content = message.choices[0].message.content
        
        # Save to cache
        ip = request.remote_addr
        c.execute('INSERT INTO notes (topic, level, program, content, timestamp, ip_address) VALUES (?, ?, ?, ?, ?, ?)',
                 (topic, level, program, notes_content, datetime.now(), ip))
        c.execute('INSERT INTO requests (ip_address, timestamp) VALUES (?, ?)',
                 (ip, datetime.now()))
        conn.commit()
        conn.close()
        
        return jsonify({'notes': notes_content, 'cached': False})
    
    except Exception as e:
        conn.close()
        error_str = str(e)
        
        # If it's a rate limit or quota error, rotate to next key
        if 'rate_limit' in error_str.lower() or 'quota' in error_str.lower() or '429' in error_str:
            rotate_api_key()
            return jsonify({'error': 'Current API key limit reached. Trying next key...'}), 429
        
        return jsonify({'error': f'Error generating notes: {error_str}'}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'current_key': current_key_index + 1, 'total_keys': len(API_KEYS)}), 200

if __name__ == '__main__':
    print(f"Loaded {len(API_KEYS)} Groq API keys")
    app.run(debug=True, port=5000)