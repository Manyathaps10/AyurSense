import pandas as pd
import pickle

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier

# 🔥 LOAD DATASET
df = pd.read_excel("AyurGenixAI_Dataset.xlsx")

# 🔥 CLEAN DATA (important)
df["Symptoms"] = df["Symptoms"].fillna("")
df["Stress Levels"] = df["Stress Levels"].fillna("")
df["Sleep Patterns"] = df["Sleep Patterns"].fillna("")

# 🔥 MULTI FEATURE INPUT (MAIN LOGIC 🚀)
X = (
    df["Symptoms"] + " " +
    df["Stress Levels"] + " " +
    df["Sleep Patterns"]
)

# 🔥 TARGET
y = df["Disease"]

# 🔥 VECTORIZE
vectorizer = TfidfVectorizer(stop_words='english')
X_vec = vectorizer.fit_transform(X)

# 🔥 MODEL
model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X_vec, y)

# 🔥 SAVE FILES
pickle.dump(model, open("model.pkl", "wb"))
pickle.dump(vectorizer, open("vectorizer.pkl", "wb"))

print("✅ Model trained with Symptoms + Stress + Sleep!")