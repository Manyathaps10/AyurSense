import os
from textwrap import dedent
import google.generativeai as genai
import json
import joblib
import pickle
import sqlite3

DB_NAME = "ayursense.db"

# conn = sqlite3.connect("responses.db")
# c = conn.cursor()

# # jo id delete karni hai wo yaha likh
# c.execute("DELETE FROM responses WHERE id=2")

# conn.commit()
# conn.close()

# print("Deleted successfully ✅")
quiz_model = None
model = None
vectorizer = None
df = None

def get_quiz_model():
    global quiz_model
    if quiz_model is None:
        try:
            quiz_model = joblib.load("quiz_model.pkl")
            print("quiz_model loaded ✅")
        except Exception as e:
            print("quiz_model error ❌", e)
            return None
    return quiz_model


def get_model():
    global model
    if model is None:
        try:
            model = pickle.load(open("model.pkl", "rb"))
            print("model loaded ✅")
        except Exception as e:
            print("model error ❌", e)
            return None
    return model


def get_vectorizer():
    global vectorizer
    if vectorizer is None:
        try:
            vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
            print("vectorizer loaded ✅")
        except Exception as e:
            print("vectorizer error ❌", e)
            return None
    return vectorizer


def get_df():
    global df
    if df is None:
        try:
            import pandas as pd
            df = pd.read_excel("AyurGenixAI_Dataset.xlsx")
            print("dataset loaded ✅")
        except Exception as e:
            print("dataset error ❌", e)
            return None
    return df


try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import sqlite3
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, make_response, g,jsonify,abort
)

# 🔥 Extract all symptoms from dataset
all_symptoms = set()

df_local = get_df()

if df_local is not None:
    for s in df_local["Symptoms"].dropna():
        for item in s.split(","):
            all_symptoms.add(item.strip().lower())

all_symptoms = sorted(all_symptoms)

from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import secrets

_LAST_AI_ERROR = None  

def _offline_plan(dosha: str) -> str:
    d = (dosha or "Balanced").strip().lower()
    if d == "vata":
        return dedent("""Day 1
• Morning: 10 min warm stretches + 5 min Anulom Vilom
• Breakfast: Moong dal cheela + ghee
• Lunch: Khichdi + sautéed veggies
• Dinner: Veg stew + jeera rice
• Evening: Warm milk + nutmeg, light reading

Day 2
• Morning: 8 rounds Surya Namaskar (slow) + sesame abhyanga
• Breakfast: Oats porridge with dates
• Lunch: Dal + lauki sabzi + roti
• Dinner: Tomato soup + soft paneer bhurji
• Evening: Screen-off 1 hr before bed, 4-7-8 breathing

Day 3
• Morning: Cat–Cow, Child’s pose, gentle forward fold
• Breakfast: Poha (warm) with peanuts
• Lunch: Rice + spinach dal + ghee
• Dinner: Carrot-ginger soup + millet roti
• Evening: Foot soak, gratitude journaling""").strip()
    if d == "pitta":
        return dedent("""Day 1
• Morning: Moon salutations + 5 min Sheetali
• Breakfast: Curd rice + cucumber
• Lunch: Jeera rice + lauki dal + mint salad
• Dinner: Veg pulao (mild) + raita
• Evening: Cool shower, light walk

Day 2
• Morning: Gentle Hatha 10 min (no overheat)
• Breakfast: Seasonal fruit + soaked almonds
• Lunch: Phulka + tur dal + tinda
• Dinner: Lemon-coriander soup + steamed veg
• Evening: Mint tea, digital sunset

Day 3
• Morning: Box breathing 4-4-4-4 + neck mobility
• Breakfast: Sabudana khichdi (light) + buttermilk
• Lunch: Rice + moong dal + cucumber salad
• Dinner: Paneer/Tofu tikka (air-fried) + quinoa
• Evening: 10-min journaling, early lights-out""").strip()
    if d == "kapha":
        return dedent("""Day 1
• Morning: Brisk walk 20 min + gentle Kapalbhati
• Breakfast: Veg upma + ginger tea
• Lunch: Bajra roti + chana masala + kachumber
• Dinner: Clear veg soup + sautéed greens
• Evening: 15-min walk after dinner

Day 2
• Morning: 12 rounds Surya Namaskar (steady)
• Breakfast: Besan chilla + small dahi
• Lunch: Brown rice + rajma + salad
• Dinner: Stir-fried veg + tofu
• Evening: Warm water, no late snacking

Day 3
• Morning: Skipping/step-ups 10 min + breath focus
• Breakfast: Sprouts chaat + lemon
• Lunch: Jowar roti + mixed veg + dal
• Dinner: Tomato-pepper soup + roasted veg
• Evening: Screens off by 10 pm""").strip()
    return dedent("""Day 1
• Morning: 10 min mobility + calm breathing
• Breakfast: Idli + sambar
• Lunch: Dal + roti + seasonal sabzi
• Dinner: Veg khichdi + ghee
• Evening: Short walk, light reading

Day 2
• Morning: 8 rounds Surya Namaskar (moderate)
• Breakfast: Poha + peanuts
• Lunch: Rice + moong dal + salad
• Dinner: Millet roti + paneer bhurji
• Evening: Herbal tea, 5-min journal

Day 3
• Morning: Yoga mix (balances/forward folds) 12 min
• Breakfast: Oats + fruit
• Lunch: Quinoa + chole + greens
• Dinner: Tomato/carrot soup + sautéed veg
• Evening: 4-7-8 breath, early lights-out""").strip()

def _call_ai(prompt: str) -> str | None:
    import google.generativeai as genai

    global _LAST_AI_ERROR
    _LAST_AI_ERROR = None

    api_key = os.getenv("GEMINI_API_KEY")
    print("🔎 GEMINI_API_KEY present:", bool(api_key))

    if not api_key:
        _LAST_AI_ERROR = "missing_gemini_key"
        return None

    genai.configure(api_key=api_key)

    MODEL = "gemini-2.5-pro"


    try:
        print("🚀 Calling Gemini Model:", MODEL)

        model = genai.GenerativeModel(MODEL)

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.9,
                "max_output_tokens": 900
            }
        )

        text = ""

        if hasattr(response, "text") and response.text:
            text += response.text

        if getattr(response, "candidates", None):
            for c in response.candidates:
                if getattr(c, "content", None):
                    for p in getattr(c.content, "parts", []):
                        if hasattr(p, "text"):
                            text += p.text

        text = text.strip()

        if text:
            print("✅ Gemini Response Success")
            return text

        raise Exception("Empty AI response")

    except Exception as e:
        print("❌ Gemini Error:", e)
        _LAST_AI_ERROR = str(e)
        return None



def generate_ai_plan(dosha: str, vata: float, pitta: float, kapha: float) -> str:
    """
    Try Gemini first; if any error/missing key/quota → always return solid offline plan (NO placeholder).
    """

    prompt = dedent(f"""
You are a senior Ayurvedic doctor, nutritionist, and holistic lifestyle coach.

You are creating a PREMIUM personalized wellness plan for a real user.

USER AYURVEDIC PROFILE:
Dominant Dosha: {dosha}
Dosha Breakdown:
Vata: {vata}%
Pitta: {pitta}%
Kapha: {kapha}%

GOAL:
Create a plan that feels deeply personalized, practical, and realistic for Indian daily life.

OUTPUT STRUCTURE (FOLLOW EXACTLY):

🌿 DAY 1 – Reset & Balance
Morning Routine:
- Yoga poses
- Breathing practice
- One lifestyle habit

Breakfast:
- Real Indian meal suggestion
- Why it helps this dosha

Lunch:
- Balanced Ayurvedic meal
- Dosha reasoning

Dinner:
- Light digestible dinner
- Digestion support logic

Evening Self-Care:
- Mental or emotional wellness habit

🌿 DAY 2 – Strength & Stability
(Same structure but DIFFERENT meals + yoga)

🌿 DAY 3 – Recovery & Long-Term Balance
(Same structure but DIFFERENT meals + yoga)

CONTENT RULES:
- Use realistic Indian foods (dal, khichdi, roti, sabzi, etc.)
- Do NOT repeat same meals daily
- Add Ayurvedic reasoning naturally
- Include lifestyle + food + mind wellness mix
- Make plan feel warm and human, not robotic
- Avoid medical claims
- Avoid generic advice like "eat healthy"
- Write 300–450 words
- Do NOT give summary
- Do NOT stop early
- Complete ALL 3 days

TONE:
Supportive, calming, premium wellness app style.

Make it feel like a real Ayurvedic expert wrote it personally for the user.
"""
).strip()

    text = _call_ai(prompt)

    if text:
        return text

    print(f"💡 Offline fallback used. Reason: {_LAST_AI_ERROR}")
    return _offline_plan(dosha)

# ---------- end AI helper ----------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret_key")

bcrypt = Bcrypt(app)
questions = [
        (1, "How would you describe your body structure?",
         "Thin, light, difficulty gaining weight",
         "Moderate, muscular, well-proportioned",
         "Broad, heavy, gains weight easily",
         "Balanced and average"),

        (2, "How does your skin usually feel?",
         "Dry, rough, or cracked",
         "Warm, sensitive, prone to redness",
         "Oily, smooth, thick",
         "Normal and clear"),

        (3, "How is your sleep pattern?",
         "Light sleeper, easily disturbed",
         "Moderate and refreshing",
         "Deep and long sleep",
         "Balanced and consistent"),

        (4, "How do you react to stress?",
         "Anxiety, worry, overthinking",
         "Anger, frustration, irritation",
         "Withdrawal, low motivation",
         "Calm and composed"),

        (5, "How is your digestion?",
         "Irregular",
         "Strong digestion",
         "Slow digestion",
         "Balanced digestion"),

        (6, "Your energy levels are:",
         "Fluctuating",
         "High and intense",
         "Low but steady",
         "Balanced"),

        (7, "Your mood tends to:",
         "Change quickly",
         "Intense",
         "Calm",
         "Balanced"),

        (8, "Your memory is:",
         "Forget easily",
         "Sharp",
         "Long retention",
         "Balanced"),

        (9, "Which weather do you prefer?",
         "Warm",
         "Cool",
         "Dry",
         "All"),

        (10, "Your appetite is:",
         "Irregular",
         "Very strong",
         "Slow",
         "Balanced"),

        (11, "In social situations you are:",
         "Talkative",
         "Leader",
         "Quiet",
         "Balanced"),

        (12, "Your emotional tendency is:",
         "Anxious",
         "Angry",
         "Lazy",
         "Stable"),

        (13, "Your food preference is:",
         "Warm food",
         "Cool food",
         "Light food",
         "Anything"),

        (14, "Your working style is:",
         "Fast",
         "Focused",
         "Slow",
         "Balanced"),

        (15, "How do you feel in the morning?",
         "Anxious",
         "Active",
         "Lazy",
         "Fresh")
    ]
question_tips = {
    1: {
        "vata": "Your lean body suggests Vata dominance — focus on strength and warm meals.",
        "pitta": "Your athletic build reflects Pitta — maintain balance with cooling foods.",
        "kapha": "Your sturdy build reflects Kapha — stay active to maintain balance.",
        "balanced": "Your body is naturally balanced — maintain your lifestyle."
    },
    2: {
        "vata": "Dry skin indicates Vata — hydration and oils will help.",
        "pitta": "Sensitive skin shows Pitta — avoid heat and spicy food.",
        "kapha": "Oily skin reflects Kapha — keep diet light.",
        "balanced": "Your skin is well balanced."
    },
    3: {
        "vata": "Light sleep shows Vata imbalance — improve routine.",
        "pitta": "Moderate sleep is healthy for Pitta.",
        "kapha": "Deep sleep reflects Kapha dominance.",
        "balanced": "Balanced sleep pattern."
    },
    4: {
        "vata": "Stress causes anxiety — typical Vata trait.",
        "pitta": "Stress leads to anger — Pitta trait.",
        "kapha": "Stress causes withdrawal — Kapha trait.",
        "balanced": "You handle stress well."
    },
    5: {
        "vata": "Irregular digestion = Vata imbalance.",
        "pitta": "Strong digestion = Pitta dominance.",
        "kapha": "Slow digestion = Kapha trait.",
        "balanced": "Healthy digestion."
    },
    6: {
        "vata": "Energy fluctuations = Vata.",
        "pitta": "High energy = Pitta.",
        "kapha": "Low steady energy = Kapha.",
        "balanced": "Stable energy."
    },
    7: {
        "vata": "Mood swings = Vata.",
        "pitta": "Intense mood = Pitta.",
        "kapha": "Calm mood = Kapha.",
        "balanced": "Balanced mood."
    },
    8: {
        "vata": "Quick learning but forgetful = Vata.",
        "pitta": "Sharp memory = Pitta.",
        "kapha": "Long memory = Kapha.",
        "balanced": "Balanced memory."
    },
    9: {
        "vata": "Prefers warmth = Vata.",
        "pitta": "Prefers cool = Pitta.",
        "kapha": "Prefers dry = Kapha.",
        "balanced": "Adaptable."
    },
    10: {
        "vata": "Irregular appetite = Vata.",
        "pitta": "Strong appetite = Pitta.",
        "kapha": "Slow appetite = Kapha.",
        "balanced": "Balanced appetite."
    },
    11: {
        "vata": "Talkative = Vata.",
        "pitta": "Leader = Pitta.",
        "kapha": "Quiet = Kapha.",
        "balanced": "Adaptable."
    },
    12: {
        "vata": "Anxiety = Vata.",
        "pitta": "Anger = Pitta.",
        "kapha": "Laziness = Kapha.",
        "balanced": "Stable emotions."
    },
    13: {
        "vata": "Prefers warm food = Vata.",
        "pitta": "Prefers cool food = Pitta.",
        "kapha": "Prefers light food = Kapha.",
        "balanced": "Balanced diet."
    },
    14: {
        "vata": "Fast but inconsistent = Vata.",
        "pitta": "Focused = Pitta.",
        "kapha": "Slow steady = Kapha.",
        "balanced": "Balanced work style."
    },
    15: {
        "vata": "Anxious mornings = Vata.",
        "pitta": "Active mornings = Pitta.",
        "kapha": "Lazy mornings = Kapha.",
        "balanced": "Fresh mornings."
    }
}

# -------------------- HELPERS --------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    # REMEMBER TOKEN TABLE (important for login)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS remember_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        token TEXT,
        expires_at TEXT,
        device_info TEXT,
        revoked INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        vata INTEGER,
        pitta INTEGER,
        kapha INTEGER,
        dominant TEXT,
        date TEXT
    ) 
    """)

    conn.commit()
    conn.close()

    print("✅ Database & Tables Ready")
def verify_password(hashed_pw, password_input):
    return bcrypt.check_password_hash(hashed_pw, password_input)


def create_remember_token(user_id, days_valid=365*5):
    token = secrets.token_urlsafe(64)
    expires_at = (datetime.utcnow() + timedelta(days=days_valid)).isoformat(sep=' ')
    device_info = request.headers.get('User-Agent', '')[:512]
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO remember_tokens (user_id, token, expires_at, device_info)
        VALUES (?, ?, ?, ?)
    """, (user_id, token, expires_at, device_info))
    conn.commit()
    conn.close()
    return token, expires_at


def revoke_token(token):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE remember_tokens SET revoked = 1 WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def find_user_by_token(token):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.name, u.email, t.expires_at
        FROM users u
        JOIN remember_tokens t ON u.id = t.user_id
        WHERE t.token = ? AND t.revoked = 0
    """, (token,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    expires_at = datetime.fromisoformat(row[3])
    if expires_at < datetime.utcnow():
        return None
    return {'id': row[0], 'name': row[1], 'email': row[2]}


def get_user_id(username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE name = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

from functools import wraps
from flask import redirect, url_for, session

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_disease_info(name):
    df = get_df()

    result = df[
        (df["Disease"].str.lower() == name.lower()) |
        (df["Hindi Name"] == name)
    ]

    return result

def predict_disease(data):

    text = (
        data.get("symptoms","") + " " +
        data.get("stress","") + " " +
        data.get("sleep","") + " " +
        data.get("diet","") + " " +
        data.get("activity","")
    )

    model = get_model()
    vectorizer = get_vectorizer()

    if model is None or vectorizer is None:
       return "Model not available"

    vec = vectorizer.transform([text])
    return model.predict(vec)[0]

def get_full_details(disease):

    row = df[df["Disease"] == disease].iloc[0]

    return {
        "Disease": row["Disease"],
        "Symptoms": row["Symptoms"],
        "Tests": row["Diagnosis & Tests"],
        "Severity": row["Symptom Severity"],
        "Duration": row["Duration of Treatment"],
        "Risk": row["Risk Factors"],
        "Environmental": row["Environmental Factors"],
        "Herbs": row["Ayurvedic Herbs"],
        "Remedies": row["Herbal/Alternative Remedies"],
        "Formulation": row["Formulation"],
        "Diet": row["Diet and Lifestyle Recommendations"],
        "Prevention": row["Prevention"],
        "Prognosis": row["Prognosis"],
        "Complications": row["Complications"],
        "Patient": row["Patient Recommendations"]
    }

def handle_user(disease=None, data=None):

    # Case 1: disease diya
    if disease:
        result = get_disease_info(disease)
        if not result.empty:
            return get_full_details(result.iloc[0]["Disease"])

    # Case 2: multi-feature prediction
    if data:
        predicted = predict_disease(data)
        return get_full_details(predicted)

    return {"message": "Please provide input"}

def smart_diagnose(data):

    symptoms = [s.strip().lower() for s in data.get("symptoms","").split(",")]
    stress = data.get("stress","").lower()
    sleep = data.get("sleep","").lower()

    scores = {}
    df = get_df()

    for _, row in df.iterrows():

        score = 0
        row_symptoms = row["Symptoms"].lower()

        # 🔥 better symptom matching
        for s in symptoms:
            if s and any(word in row_symptoms for word in s.split()):
                score += 2

        # stress
        if stress and stress in row["Stress Levels"].lower():
            score += 1

        # sleep
        if sleep and sleep in row["Sleep Patterns"].lower():
            score += 1

        scores[row["Disease"]] = score

    # 🔥 remove zero score diseases
    filtered = {k:v for k,v in scores.items() if v > 0}

    sorted_scores = sorted(filtered.items(), key=lambda x: x[1], reverse=True)

    return sorted_scores[:3]
def get_confidence(score):
    if score >= 6:
        return "High"
    elif score >= 3:
        return "Medium"
    else:
        return "Low"

import sqlite3

def init_responses_db():
    conn = sqlite3.connect("responses.db")
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS responses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        message TEXT,
        type TEXT
    )
    ''')

    conn.commit()
    conn.close()

init_responses_db()

# -------------------- LOAD USER BEFORE EACH REQUEST --------------------
@app.before_request
def load_user_from_token():
    g.user = session.get('user')
    if g.user:
        return
    token = request.cookies.get('remember_token')
    if not token:
        return
    user = find_user_by_token(token)
    if user:
        session['user'] = user['name']
        g.user = user['name']


# -------------------- ROUTES --------------------
@app.route('/')
def index():
    conn = sqlite3.connect("responses.db")
    c = conn.cursor()

    c.execute("SELECT name, email, message, type FROM responses ORDER BY id DESC")
    data = c.fetchall()

    conn.close()

    return render_template("index.html", testimonials=data)


@app.route('/about')
def about():
    return render_template("about.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if len(password) < 8:
            flash("Password must be at least 8 characters long!", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("register"))

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            flash("Email already registered. Please log in.", "warning")
            conn.close()
            return redirect(url_for("login"))

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        cursor.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                       (name, email, hashed_pw))
        conn.commit()
        conn.close()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password_input = request.form.get('password')
        remember = request.form.get('remember')

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, password FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and verify_password(user[3], password_input):
            session['user'] = user[1]
            resp = make_response(redirect(url_for('index')))
            if remember == "1":
                token, expires_at = create_remember_token(user[0])
                expires_dt = datetime.fromisoformat(expires_at)
                resp.set_cookie(
                    'remember_token', token,
                    expires=expires_dt, httponly=True, samesite='Lax', secure=False
                )
            flash('Login successful!', 'success')
            return resp
        else:
            flash('Invalid email or password!', 'danger')

    return render_template('login.html')


# -------------------- QUIZ --------------------
@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if 'user' not in session:
        return render_template("please_login.html"), 401


    if request.method == 'POST':

        inputs = []

        for i in range(1, 16):
            val = request.form.get(str(i))
            session[f"q{i}"] = request.form.get(str(i))

            if val == "A":
                inputs.append(0)
            elif val == "B":
                inputs.append(1)
            elif val == "C":
                inputs.append(2)
            elif val == "D":
                inputs.append(3)

        # 👉 ML prediction
        quiz_model = get_quiz_model()

        if quiz_model is None:
            return "Quiz model not available", 500

        prediction = quiz_model.predict([inputs])[0]

        # 👉 Percent
        vata_percent = round((inputs.count(0) / 15) * 100)
        pitta_percent = round((inputs.count(1) / 15) * 100)
        kapha_percent = round((inputs.count(2) / 15) * 100)

        session["vata_percent"] = vata_percent
        session["pitta_percent"] = pitta_percent
        session["kapha_percent"] = kapha_percent

        session["ml_result"] = prediction

        return redirect(url_for('result'))
    return render_template('quiz.html', questions=questions)

@app.route('/result')
def result():
    if 'user' not in session:
        return render_template("please_login.html"), 401

    # 👉 ML result
    ml_prediction = session.get("ml_result", "Balanced")
    print("ML RESULT:", ml_prediction)

    dominant_dosha = ml_prediction.capitalize()

    # 👉 percentages
    vata_percent = session.get("vata_percent", 0)
    pitta_percent = session.get("pitta_percent", 0)
    kapha_percent = session.get("kapha_percent", 0)
    detailed_suggestions = []


    for i in range(1, 16):
        val = session.get(f"q{i}")

        if val == "A":
            category = "vata"
            answer = "Option A"
        elif val == "B":
            category = "pitta"
            answer = "Option B"
        elif val == "C":
            category = "kapha"
            answer = "Option C"
        elif val == "D":
            category = "balanced"
            answer = "Option D"
        else:
            category = "balanced"
            answer = "Not answered"

        tip = question_tips.get(i, {}).get(category, "No suggestion available")

        detailed_suggestions.append({
            "qnum": i,
            "question": questions[i-1][1],
            "answer": answer,
            "suggestion": tip,
            "category": category,
            "icon": "🌿"
        })

# ✅ loop ke bahar
    print("TOTAL ITEMS:", len(detailed_suggestions))
    print("FULL LIST:", detailed_suggestions)


# 👉 Suggestions
    remedies = {
        "Vata": "Ground yourself with warm meals, sesame oil massages, and a consistent routine.",
        "Pitta": "Stay cool with calming practices and avoid spicy foods.",
        "Kapha": "Energize with light food and regular exercise.",
        "Balanced": "Maintain a balanced lifestyle."
    }

    yoga_suggestions = {
        "Vata": "Gentle yoga like Child Pose, Forward Fold.",
        "Pitta": "Cooling yoga like Moon Salutations.",
        "Kapha": "Active yoga like Surya Namaskar.",
        "Balanced": "Mixed yoga routine."
    }

    diet_suggestions = {
        "Vata": "Warm, moist foods.",
        "Pitta": "Cooling foods.",
        "Kapha": "Light, dry foods.",
        "Balanced": "Seasonal balanced diet."
   }
    
    user_id = get_user_id(session['user'])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO history (user_id, vata, pitta, kapha, dominant, date)
    VALUES (?, ?, ?, ?, ?, datetime('now'))
    """, (user_id, vata_percent, pitta_percent, kapha_percent, dominant_dosha))

    conn.commit()
    conn.close()

# ===== AI PLAN =====
    ai_plan = generate_ai_plan(dominant_dosha, vata_percent, pitta_percent, kapha_percent)

    return render_template(
        "result.html",
         vata_percent=vata_percent,
         pitta_percent=pitta_percent,
         kapha_percent=kapha_percent,
        dominant_dosha=dominant_dosha,
        remedy=remedies[dominant_dosha],
        yoga=yoga_suggestions[dominant_dosha],
        diet=diet_suggestions[dominant_dosha],
        detailed_suggestions=detailed_suggestions,
        ai_plan=ai_plan,
        ml_prediction=ml_prediction
   )


# -------------------- OTHER ROUTES --------------------
@app.route('/blog')
@login_required
def blog():
    return render_template("blog.html")

@app.route("/blog/<slug>")
def blog_detail(slug):
    try:
        return render_template(f"blogs/{slug}.html")
    except:
        return "Blog not found", 404


@app.route('/logout')
def logout():
    token = request.cookies.get('remember_token')
    if token:
        revoke_token(token)
    session.pop('user', None)

    resp = make_response(redirect(url_for('index')))
    resp.delete_cookie('remember_token', path='/', samesite='Lax', secure=False)
    flash('Logged out successfully.', 'info')
    return resp



@app.route("/contact")
def contact():
    conn = sqlite3.connect("responses.db")
    c = conn.cursor()

    c.execute("SELECT name, email, message, type FROM responses ORDER BY id DESC")
    data = c.fetchall()

    conn.close()

    return render_template("contact.html", testimonials=data)


# ---- Quick env debug ----
@app.route("/envcheck")
def envcheck():
    import sys
    return {
        "cwd": os.getcwd(),
        ".env_exists": os.path.exists(os.path.join(os.getcwd(), ".env")),
        "GEMINI_API_KEY_present": bool(os.getenv("GEMINI_API_KEY")),
        "python": sys.version,
        "sdk": "gemini",
    }

@app.route("/listmodels")
def listmodels():
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

    models = []
    for m in genai.list_models():
        models.append({
            "name": m.name,
            "methods": m.supported_generation_methods
        })

    return {"models": models}

@app.route("/remedies")
@login_required
def remedies():
    return render_template("remedies.html")

@app.route("/yoga_exercises")
@login_required
def yoga_exercises():
    return render_template("yoga_exercises.html")

@app.route("/yoga/<type>")
def yoga_article(type):
    return f"Yoga Article Page: {type}"

@app.route("/exercise/<type>")
def exercise_article(type):
    return f"Exercise Article Page: {type}"

@app.route("/get-yoga-plan", methods=["POST"])
def get_yoga_plan():

    mood = request.form.get("mood")
    energy = request.form.get("energy")
    time = request.form.get("time")

    plan = []

    # ---------------- MOOD BASE ----------------
    if mood == "stress":
        base = [
            "Deep breathing",
            "Child Pose",
            "Forward Fold"
        ]
    elif mood == "tired":
        base = [
            "Gentle stretching",
            "Legs up the wall",
            "Relaxed breathing"
        ]
    else:  # normal
        base = [
            "Sun Salutation",
            "Standing stretch",
            "Balance pose"
        ]

    # ---------------- ENERGY MODIFIER ----------------
    if energy == "low":
        base.append("Slow neck & shoulder release")
    elif energy == "medium":
        base.append("Moderate flow yoga")
    else:  # high
        base.append("Power yoga sequence")

    # ---------------- TIME MODIFIER (IMPORTANT) ----------------
    if time == "short":
        plan = base[:3]  # sirf 3 steps
        plan.append("1–2 min calm breathing")

    elif time == "medium":
        plan = base
        plan.append("5 min mindful breathing")

    else:  # long
        plan = base + [
            "Extended flexibility practice",
            "10 min guided meditation"
        ]

    return {"plan": plan}

@app.route("/diet_suggestions")
@login_required
def condition():
    df = get_df()

    diseases = sorted(set(df["Disease"].dropna()))

    return render_template(
        "diet_suggestions.html",
        diseases=diseases,
        symptoms=all_symptoms   
    )

@app.route("/diet/<condition>")
def diet_article(condition):

    return render_template("diet_article.html", condition=condition)

@app.route("/condition/<name>")
@login_required
def condition_article(name):

    file_path = os.path.join("data", f"{name}.json")

    if not os.path.exists(file_path):
        abort(404)

    with open(file_path, "r", encoding="utf-8") as file:
        article = json.load(file)

    return render_template(
        "wellness_article.html",
        article=article
    )

@app.route("/dosha-detail/<name>")
def dosha_detail(name):

    file_path = os.path.join("data", f"{name}.json")

    with open(file_path, "r", encoding="utf-8") as f:
        article = json.load(f)

    return render_template("article.html", article=article,name=name, type='dosha')

@app.route("/disease/<name>")
def disease_article(name):
    import json

    try:
        with open(f"data/{name}.json") as f:
            article = json.load(f)
    except FileNotFoundError:
        return "Disease article not found"

    return render_template("article.html", article=article,name=name, type='disease')

@app.route("/generate-ai-plan")
def generate_ai_plan_route():
    if 'user' not in session:
        return {"plan": "Please login first."}

    dominant_dosha = session.get("ml_result", "Balanced").capitalize()

    vata = session.get("vata_percent", 0)
    pitta = session.get("pitta_percent", 0)
    kapha = session.get("kapha_percent", 0)

    # 🔥 TRY AI
    try:
        ai_plan = generate_ai_plan(dominant_dosha, vata, pitta, kapha)

        if not ai_plan or "error" in ai_plan.lower():
            raise Exception("AI failed")

    except:
        print("⚠️ AI failed → fallback used")
        ai_plan = _offline_plan(dominant_dosha)

    return {"plan": ai_plan}

diet_data = {
    "Vata": """
• Focus on warm, freshly cooked meals.
• Include ghee, soups, khichdi, and root vegetables.
• Avoid cold drinks, dry snacks, and skipping meals.
• Eat at fixed times to stabilize digestion.
""",

    "Pitta": """
• Prefer cooling foods like cucumber, coconut water, and leafy greens.
• Avoid spicy, fried, and overly salty foods.
• Include dairy like milk and ghee in moderation.
• Stay hydrated throughout the day.
""",

    "Kapha": """
• Eat light and warm foods like soups, millets, and steamed vegetables.
• Avoid oily, heavy, and sugary foods.
• Include spices like ginger, black pepper to boost metabolism.
• Avoid overeating and late-night meals.
""",

    "Balanced": """
• Maintain a seasonal and balanced diet.
• Include variety of grains, vegetables, and proteins.
• Avoid excess of any one taste.
• Follow regular meal timing.
"""
}

yoga_data = {
    "Vata": """
• Gentle yoga like Child Pose and Forward Fold.
• Slow Surya Namaskar to build stability.
• Focus on breathing exercises like Anulom Vilom.
• Practice grounding meditation daily.
""",

    "Pitta": """
• Cooling yoga like Moon Salutations.
• Avoid overheating and intense workouts.
• Practice Sheetali and deep breathing.
• Include meditation for emotional balance.
""",

    "Kapha": """
• Active yoga like Surya Namaskar.
• Include cardio-based movements.
• Practice Kapalbhati and energizing breathing.
• Stay physically active daily.
""",

    "Balanced": """
• Mix of strength, flexibility, and breathing yoga.
• Maintain consistency in routine.
• Include meditation and relaxation.
"""
}

def simple_plan(dosha):
    if dosha == "Vata":
        return [
            "Day 1: Warm meals + gentle yoga + early sleep",
            "Day 2: Oil massage + khichdi + breathing",
            "Day 3: Light stretching + routine consistency"
        ]
    elif dosha == "Pitta":
        return [
            "Day 1: Cooling foods + meditation",
            "Day 2: Light yoga + hydration",
            "Day 3: Calm routine + avoid heat"
        ]
    elif dosha == "Kapha":
        return [
            "Day 1: Exercise + light food",
            "Day 2: Active yoga + detox meals",
            "Day 3: Stay active + avoid laziness"
        ]
    else:
        return ["Maintain balanced lifestyle with routine"]


@app.route("/history")
def history():

    if 'user' not in session:
        return render_template("please_login.html"), 401

    user_id = get_user_id(session['user'])

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT vata, pitta, kapha, dominant, date
    FROM history
    WHERE user_id = ?
    ORDER BY date DESC
    """, (user_id,))

    data = cursor.fetchall()
    conn.close()

    return render_template("history.html", data=data)

@app.route("/analyze", methods=["POST"])
def analyze():

    data = request.get_json()

    disease = data.get("disease")

    # 🔥 known disease (same as before)
    if disease:
        return jsonify(get_full_details(disease))

    # 🔥 diagnose mode
    top3 = smart_diagnose(data)

    result = []

    for d, score in top3:
       details = get_full_details(d)
       details["confidence"] = get_confidence(score)
       result.append(details)

    return jsonify({"predictions": result})

@app.route("/pose-detail/<pose>")
def pose_detail(pose):
    import json, os

    path = os.path.join("data/yoga", pose + ".json")

    with open(path) as f:
        pose_data = json.load(f)

    return render_template(
        "pose_detail.html",
        pose=pose_data,
        name=pose   
    )

@app.route("/data/yoga/<pose>.json")
def get_pose_data(pose):
    file_path = os.path.join("data/yoga", pose + ".json")
    
    with open(file_path) as f:
        data = json.load(f)
    
    return data

@app.route("/more_problems")
def more_problems():
    return render_template("more_problems.html")

from flask import request, redirect

@app.route("/submit-form", methods=["POST"])
def submit_form():
    name = request.form["name"]
    email = request.form["email"]
    message = request.form["message"]
    type_ = request.form["type"]

    conn = sqlite3.connect("responses.db")
    c = conn.cursor()

    c.execute("INSERT INTO responses (name, email, message, type) VALUES (?, ?, ?, ?)",
              (name, email, message, type_))

    conn.commit()
    conn.close()

    return redirect("/contact")

@app.route("/testimonials")
def all_testimonials():
    conn = sqlite3.connect("responses.db")
    c = conn.cursor()

    c.execute("SELECT name, email, message, type FROM responses ORDER BY id DESC")
    data = c.fetchall()

    conn.close()

    return render_template("testimonials.html", testimonials=data)

@app.route('/google-login', methods=['POST'])
def google_login():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # check user
    cursor.execute("SELECT id, name FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if not user:
        # new user insert
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, "google_user")
        )
        conn.commit()

    # 🔥 SAME AS YOUR LOGIN
    session['user'] = name

    conn.close()

    flash('Login successful!', 'success')

    return {"success": True}

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user:
            token = secrets.token_urlsafe(32)

            # token store karo (temporary)
            session['reset_token'] = token
            session['reset_email'] = email

            reset_link = f"http://127.0.0.1:5000/reset-password/{token}"

            print("RESET LINK:", reset_link)  

            flash("Reset link sent to your email", "info")
        else:
            flash("Email not found", "danger")

    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):

    if token != session.get('reset_token'):
        return "Invalid or expired token ❌"

    if request.method == 'POST':
        new_password = request.form.get('password')

        hashed_pw = bcrypt.generate_password_hash(new_password).decode("utf-8")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password = ? WHERE email = ?",
            (hashed_pw, session.get('reset_email'))
        )
        conn.commit()
        conn.close()

        flash("Password updated successfully!", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html')

if __name__ == '__main__':
    init_db()   
    app.run(debug=True)
