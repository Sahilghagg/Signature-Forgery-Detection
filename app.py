from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
import os
import numpy as np
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image
import mysql.connector
import hashlib

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'pass#Sahil2004',
    'database': 'signature_forgery'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Load model
model = load_model('signature_forgery_detector.h5')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/index.html')
def index():
    return redirect(url_for('home'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error', 'danger')
            return redirect(url_for('signup'))
        
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        
        if user:
            flash('Username already exists!', 'danger')
            conn.close()
            return redirect(url_for('signup'))
        
        cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', 
                      (username, email, hashed_password))
        conn.commit()
        conn.close()

        flash('You have successfully signed up!', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = get_db_connection()
        if conn is None:
            flash('Database connection error', 'danger')
            return redirect(url_for('login'))
        
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', 
                      (username, hashed_password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['username'] = username
            session['email'] = user[2]
            flash('Login successful', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('email', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'username' in session:
        return render_template('profile.html', username=session['username'], email=session['email'])
    return redirect(url_for('login'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only image files (PNG, JPG, JPEG) are allowed'})

    try:
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        img = image.load_img(filepath, target_size=(150, 150), color_mode='grayscale')
        img_array = image.img_to_array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        
        prediction = model.predict(img_array)
        confidence = float(prediction[0][0])
        
        if confidence > 0.5:
            result = "Genuine"
            confidence_pct = confidence * 100
        else:
            result = "Forged"
            confidence_pct = (1 - confidence) * 100
        
        return jsonify({
            'result': result,
            'confidence': f"{confidence_pct:.1f}%",
            'image_path': filepath
        })
        
    except Exception as e:
        return jsonify({'error': f'Error processing image: {str(e)}'})

@app.route('/check_connectivity')
def check_connectivity():
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)