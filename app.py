from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret_key")  

# Dummy user database (for testing)
users = {}

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# About page
@app.route('/about')
def about():
    return render_template("about.html")

# Register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash('Username already exists!')
        else:
            users[username] = password
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
    return render_template('register.html')

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if users.get(username) == password:
            session['user'] = username
            return redirect(url_for('quiz'))
        else:
            flash('Invalid credentials!')
    return render_template('login.html')

# Quiz page
@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'user' not in session:
        # Instead of redirect to login, show a nice message page
        return render_template('please_login.html')

    if request.method == 'POST':
        answers = request.form
        return redirect(url_for('result'))

    return render_template('quiz.html')


# Result page
@app.route('/result')
def result():
    if 'user' not in session:
        return redirect(url_for('login'))
    # Render result page (can pass actual results later)
    return render_template('result.html')

#Blog
@app.route('/blog')
def blog():
    return render_template("blog.html")

# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
