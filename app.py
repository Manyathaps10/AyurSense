import os
from textwrap import dedent
import google.generativeai as genai
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import sqlite3
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, make_response, g
)
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import secrets

_LAST_AI_ERROR = None  # optional debug flag

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
DB_NAME = "users.db"

# -------------------- DATABASE SETUP --------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS remember_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            device_info TEXT,
            revoked INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def init_quiz_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            category_a TEXT NOT NULL,
            category_b TEXT NOT NULL,
            category_c TEXT NOT NULL,
            category_d TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_option TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(question_id) REFERENCES quiz_questions(id)
        )
    """)
    conn.commit()
    conn.close()


def seed_quiz_questions():
    """Run once to seed questions."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM quiz_questions")
    questions = [
        ("How would you describe your body type?",
         "Lean and slender", "Medium build, athletic", "Sturdy and broad", "Well-balanced mix",
         "vata", "pitta", "kapha", "balanced"),
        ("Your skin usually feels —",
         "Dry or rough", "Warm, sometimes red or sensitive", "Oily and smooth", "Normal and clear",
         "vata", "pitta", "kapha", "balanced"),
        ("Your sleep pattern —",
         "Light and easily disturbed", "Moderate and refreshing", "Deep and long", "Balanced and regular",
         "vata", "pitta", "kapha", "balanced"),
        ("How do you respond to stress?",
         "Anxious or overthinking", "Irritable or angry", "Withdrawn or sluggish", "Stay calm",
         "vata", "pitta", "kapha", "balanced"),
        ("Your digestion feels —",
         "Irregular or variable", "Strong and quick", "Slow and heavy", "Consistent and normal",
         "vata", "pitta", "kapha", "balanced"),
        ("What best describes your energy levels?",
         "Comes in bursts, inconsistent", "High and intense", "Slow but steady", "Even and stable",
         "vata", "pitta", "kapha", "balanced"),
        ("Your mood changes —",
         "Quickly and unpredictably", "Based on control and goals", "Rarely, generally calm", "Balanced and centered",
         "vata", "pitta", "kapha", "balanced"),
        ("Your memory is —",
         "Quick to learn but forgets easily", "Sharp and precise", "Slow to grasp but retains long", "Consistent recall",
         "vata", "pitta", "kapha", "balanced"),
        ("Which weather suits you best?",
         "Warm and humid", "Cool and dry", "Dry and warm", "All seasons equally",
         "vata", "pitta", "kapha", "balanced"),
        ("Your appetite —",
         "Irregular — sometimes strong, sometimes none", "Strong, can’t skip meals", "Slow or heavy", "Steady and mild",
         "vata", "pitta", "kapha", "balanced"),
        ("In a group setting, you are —",
         "Talkative and creative", "Confident and assertive", "Calm and peaceful", "Adaptable and balanced",
         "vata", "pitta", "kapha", "balanced"),
        ("Your usual emotional tendency —",
         "Worry or nervousness", "Anger or frustration", "Attachment or laziness", "Composed and forgiving",
         "vata", "pitta", "kapha", "balanced"),
        ("Preferred food texture —",
         "Warm and moist meals", "Cool and less spicy food", "Light and dry food", "Any seasonal food",
         "vata", "pitta", "kapha", "balanced"),
        ("Your pace of working —",
         "Fast but inconsistent", "Driven and focused", "Slow and steady", "Consistent and smooth",
         "vata", "pitta", "kapha", "balanced"),
        ("How do you usually feel in the morning?",
         "Energetic but anxious", "Focused and ready", "Lazy or heavy", "Fresh and balanced",
         "vata", "pitta", "kapha", "balanced"),
    ]
    for q in questions:
        cursor.execute("""
            INSERT INTO quiz_questions (
                question, option_a, option_b, option_c, option_d,
                category_a, category_b, category_c, category_d
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, q)
    conn.commit()
    conn.close()
    print("✅ AyurSense quiz questions seeded successfully!")


# Initialize DBs
init_db()
init_quiz_db()
seed_quiz_questions()   # uncomment once if needed


# -------------------- HELPERS --------------------
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
    return render_template('index.html')


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
            if remember:
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
        # custom "please login" page instead of redirect
        return render_template("please_login.html"), 401

    user_id = get_user_id(session['user'])
    if not user_id:
        # session corrupt/expired → also show plz.html
        return render_template("please_login.html"), 401

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quiz_questions")
    questions = cursor.fetchall()
    conn.close()

    if request.method == 'POST':
        answers = {}
        for key, val in request.form.items():
            if not key.isdigit():
                continue
            qid = int(key)
            selected_option = val.strip().upper()
            if selected_option in ('A', 'B', 'C', 'D'):
                answers[qid] = selected_option

        if not answers:
            flash("No answers submitted. Please answer the questions.", "warning")
            return redirect(url_for('quiz'))

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM quiz_answers WHERE user_id = ?", (user_id,))
        for qid, option in answers.items():
            cursor.execute("""
                INSERT INTO quiz_answers (user_id, question_id, selected_option)
                VALUES (?, ?, ?)
            """, (user_id, qid, option))
        conn.commit()
        conn.close()
        return redirect(url_for('result'))

    return render_template('quiz.html', questions=questions)


@app.route('/result')
def result():
    if 'user' not in session:
        return render_template("please_login.html"), 401

    user_id = get_user_id(session['user'])
    if not user_id:
        return render_template("please_login.html"), 401

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.id, q.question, q.option_a, q.option_b, q.option_c, q.option_d,
               q.category_a, q.category_b, q.category_c, q.category_d, a.selected_option
        FROM quiz_answers a
        JOIN quiz_questions q ON a.question_id = q.id
        WHERE a.user_id = ?
        ORDER BY q.id ASC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()

    # Counts & insights
    detailed_suggestions = []
    category_count = {"vata": 0, "pitta": 0, "kapha": 0, "balanced": 0}

    cat_icon = {"vata": "🌿", "pitta": "🔥", "kapha": "💧", "balanced": "🌸"}

    question_tips = {
        1: {"vata":"Lean build points to Vata — add grounding: warm meals, strength work, regular sleep.",
            "pitta":"Athletic frame shows Pitta — cool it with cucumbers, mint, and evening wind-downs.",
            "kapha":"Broader build leans Kapha — prioritise daily movement and lighter dinners.",
            "balanced":"Well-balanced frame — maintain mixed workouts and seasonal food."},
        2: {"vata":"Dry/rough skin → hydrate inside-out: ghee, sesame oil abhyanga, and warm water.",
            "pitta":"Warm/red skin → avoid chilies; add aloe/coriander; practise cooling breath (Sheetali).",
            "kapha":"Oily skin → favour steamed veg + spices (turmeric/black pepper); skip heavy dairy.",
            "balanced":"Normal/clear — keep simple skincare and steady hydration."},
        3: {"vata":"Light/disturbed sleep → no screens post-9pm, warm milk with nutmeg, gentle stretches.",
            "pitta":"Moderate sleep — keep room cool; finish dinner 3 hrs before bed.",
            "kapha":"Very deep sleep — earlier wake time + brisk morning walk for spark.",
            "balanced":"Regular sleep — keep consistent lights-out and wake windows."},
        4: {"vata":"Anxious/overthinking → journal 5 mins + 4-7-8 breath; stabilise mealtimes.",
            "pitta":"Irritable/angry → pause rule: sip water, 10 cool breaths, step out for air.",
            "kapha":"Withdrawn/sluggish — rhythm reset with 15-min sunlight walk after meals.",
            "balanced":"Stay-calm response — keep micro-mindfulness breaks."},
        5: {"vata":"Irregular digestion → ginger-lime pinch before meals; eat at fixed hours.",
            "pitta":"Strong/quick → smaller, frequent cooling meals; avoid acidic foods.",
            "kapha":"Slow/heavy → cumin-fennel-ginger tea; prefer dry/roasted textures.",
            "balanced":"Steady digestion — continue fibre + water balance."},
        6: {"vata":"Burst energy → plan buffer breaks; avoid caffeine spikes late evening.",
            "pitta":"High/intense → schedule wind-down blocks; protect lunch hour.",
            "kapha":"Slow/steady → morning cardio + upbeat music to lift momentum.",
            "balanced":"Even energy — protein at breakfast, light dinners."},
        7: {"vata":"Mood swings fast → 5 mindful breaths before reacting; warm comfort meals help.",
            "pitta":"Goal-driven emotions → add empathy check-ins; avoid late-night competition.",
            "kapha":"Generally calm — add stimulating tasks to stay enthusiastic.",
            "balanced":"Centered — keep gratitude journaling nightly."},
        8: {"vata":"Quick to learn/forget → spaced repetition + sesame oil head massage support memory.",
            "pitta":"Sharp/precise — protect from burnout: screen breaks + evening leisure.",
            "kapha":"Slow to grasp/long retention — learn by teaching + short movement breaks.",
            "balanced":"Consistent recall — continue mixed study styles."},
        9: {"vata":"Warm & humid suits you — guard against cold/dry with scarves and soups.",
            "pitta":"Cool & dry suits you — avoid noon heat; hydrate with coconut water.",
            "kapha":"Dry & warm suits you — keep air light; morning sun salutations boost.",
            "balanced":"All seasons okay — follow seasonal produce."},
        10: {"vata":"Irregular appetite — don’t skip breakfast; add stewed fruits or porridge.",
             "pitta":"Strong appetite — structured mealtimes; include cooling raita/salads.",
             "kapha":"Slow appetite — warm water with lemon; avoid late-night snacking.",
             "balanced":"Steady appetite — maintain portion awareness."},
        11: {"vata":"Talkative/creative — anchor with to-do lists; single-tasking helps.",
             "pitta":"Confident/assertive — add empathy pauses in meetings to soften edge.",
             "kapha":"Calm/peaceful — take initiative slots to keep pace lively.",
             "balanced":"Adaptable — continue balanced roles in groups."},
        12: {"vata":"Worry/nervousness — limit doom-scrolling; evening chamomile helps.",
             "pitta":"Anger/frustration — cooling pranayama + evening stretches.",
             "kapha":"Attachment/laziness — 20-min rule: start small, momentum follows.",
             "balanced":"Composed/forgiving — keep reflection habit."},
        13: {"vata":"Warm & moist meals suit — keep soups/stews as staples.",
             "pitta":"Cool/less spicy — add mint/coriander chutneys.",
             "kapha":"Light/dry foods — prefer roasting/air-frying over deep-fry.",
             "balanced":"Seasonal foods — rotate grains/veggies monthly."},
        14: {"vata":"Fast but inconsistent — time-box tasks + 5-min wrap-ups to close loops.",
             "pitta":"Driven/focused — schedule recovery blocks; delegate perfection.",
             "kapha":"Slow/steady — set mini-deadlines and accountability check-ins.",
             "balanced":"Consistent/smooth — keep weekly review ritual."},
        15: {"vata":"Energetic yet anxious — start with grounding breath + warm breakfast.",
             "pitta":"Focused/ready — plan first, then execute; avoid email first thing.",
             "kapha":"Lazy/heavy — sunlight + upbeat walk before screens.",
             "balanced":"Fresh/balanced — maintain gentle AM routine."},
    }

    for idx, row in enumerate(rows, start=1):
        (qid, question, a, b, c, d,
         cat_a, cat_b, cat_c, cat_d, selected) = row

        selected = selected.upper()
        if selected == "A":
            category, answer_text = cat_a.lower(), a
        elif selected == "B":
            category, answer_text = cat_b.lower(), b
        elif selected == "C":
            category, answer_text = cat_c.lower(), c
        else:
            category, answer_text = cat_d.lower(), d

        category_count[category] += 1

        tip = question_tips.get(idx, {}).get(category)
        if not tip:
            generic = {
                "vata": "Balance Vata with warmth, routine, and oils.",
                "pitta": "Calm Pitta with cooling foods and pauses.",
                "kapha": "Lighten Kapha with movement and light meals.",
                "balanced": "You’re balanced — maintain mindful habits."
            }
            tip = generic.get(category, "")

        detailed_suggestions.append({
            "qnum": idx,
            "question": question,
            "answer": answer_text,
            "category": category,
            "icon": cat_icon.get(category, "✨"),
            "suggestion": tip
        })

    
    total = category_count["vata"] + category_count["pitta"] + category_count["kapha"]
    if total > 0:
        vata_percent = round((category_count["vata"] / total) * 100, 1)
        pitta_percent = round((category_count["pitta"] / total) * 100, 1)
        kapha_percent = round((category_count["kapha"] / total) * 100, 1)
    else:
        vata_percent = pitta_percent = kapha_percent = 0.0

    # Dominant dosha
    dosha_map = {'Vata': vata_percent, 'Pitta': pitta_percent, 'Kapha': kapha_percent}
    dominant_dosha = max(dosha_map, key=dosha_map.get)
    if (abs(vata_percent - pitta_percent) < 10 and
        abs(pitta_percent - kapha_percent) < 10 and
        abs(vata_percent - kapha_percent) < 10):
        dominant_dosha = "Balanced"

    remedies = {
        "Vata": "Ground yourself with warm meals, sesame oil massages, and a consistent routine. Avoid cold and dry foods.",
        "Pitta": "Stay cool with calming practices, coconut water, and avoid spicy or oily foods.",
        "Kapha": "Energize with light, dry foods, regular movement, and avoid heavy dairy or sweets.",
        "Balanced": "Maintain mindfulness, regular sleep, and balanced meals to stay aligned."
    }
    yoga_suggestions = {
        "Vata": "Do gentle grounding yoga — Hatha or Yin Yoga. Try Child’s Pose, Mountain Pose, and Forward Fold.",
        "Pitta": "Choose cooling yoga — Moon Salutations, Pranayama (Sheetali breath), and restorative poses.",
        "Kapha": "Go for energizing yoga — Surya Namaskar, Warrior series, and backbends to boost vitality.",
        "Balanced": "Maintain a mixed practice of strength, flexibility, and relaxation."
    }
    diet_suggestions = {
        "Vata": "Prefer warm, moist foods — soups, stews, ghee, cooked grains, and herbal teas. Avoid cold salads or dry snacks.",
        "Pitta": "Favor cooling foods — cucumbers, melons, mint, rice, and milk. Avoid spicy, fried, or acidic items.",
        "Kapha": "Choose light, warm meals — steamed veggies, lentils, and herbal teas with ginger or pepper. Avoid sweets and excess oil.",
        "Balanced": "Eat seasonal, fresh foods in moderation and stay hydrated mindfully."
    }

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
        ai_plan=ai_plan,     # << pass to template
    )


# -------------------- OTHER ROUTES --------------------
@app.route('/blog')
def blog():
    return render_template("blog.html")


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



@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        print(f"New Contact Message:\nName: {name}\nEmail: {email}\nMessage: {message}\n")
        flash(f"Thank you, {name}! Your message has been received.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


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
def remedies():
    return render_template("remedies.html")

@app.route("/dosha/<dosha>")
def dosha_article(dosha):

    data = {
        "vata": {
            "title": "Vata Dosha Complete Guide",
            "content": "Vata controls movement, breathing, nervous system. Imbalance causes anxiety, dryness and insomnia. Balance Vata with warm food, oil massage and routine."
        },
        "pitta": {
            "title": "Pitta Dosha Complete Guide",
            "content": "Pitta controls digestion and metabolism. Imbalance causes acidity, anger and inflammation. Balance Pitta with cooling food, coconut water and meditation."
        },
        "kapha": {
            "title": "Kapha Dosha Complete Guide",
            "content": "Kapha controls body structure and immunity. Imbalance causes weight gain and low energy. Balance Kapha with exercise, light food and spices."
        }
    }

    article = data.get(dosha.lower())

    return render_template("article.html", article=article)
    
@app.route("/disease/<disease>")
def disease_article(disease):

    data = {
        "stress": {
            "title": "Stress & Anxiety Natural Healing",
            "content": """
Stress Ayurvedic View:
Stress increases Vata and Pitta dosha.

Natural Remedies:
• Ashwagandha powder with milk at night
• Brahmi tea for brain calmness
• Daily meditation 10 min
• Warm oil head massage weekly

Lifestyle Tips:
• Avoid late night screen
• Sleep before 11 PM
• Practice deep breathing
"""
        },

        "digestion": {
            "title": "Digestive Healing Ayurveda",
            "content": """
Digestive Problems come from weak Agni (digestive fire).

Natural Remedies:
• Jeera water morning
• Ginger + black salt before meals
• Triphala at night

Lifestyle Tips:
• Eat warm fresh food
• Avoid cold drinks
• Fixed meal timing
"""
        },

        "sleep": {
            "title": "Sleep Recovery Ayurveda",
            "content": """
Sleep imbalance happens due to Vata disturbance.

Natural Remedies:
• Nutmeg milk before sleep
• Chamomile tea
• Foot oil massage

Lifestyle Tips:
• No phone 1 hour before sleep
• Meditation before bed
"""
        },

        "immunity": {
            "title": "Immunity Boost Ayurveda",
            "content": """
Weak immunity linked to Kapha imbalance.

Natural Remedies:
• Turmeric milk daily
• Tulsi tea
• Amla juice morning

Lifestyle Tips:
• Morning sunlight
• Daily yoga
"""
        }
    }

    article = data.get(disease.lower())

    return render_template("article.html", article=article)

@app.route("/yoga_exercises")
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

@app.route("/diet-suggestions")
def diet_suggestions():
    return render_template("diet_suggestions.html")

@app.route("/diet/<condition>")
def diet_article(condition):

    return render_template("diet_article.html", condition=condition)

@app.route("/condition/<name>")
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



if __name__ == '__main__':
    app.run(debug=True)
