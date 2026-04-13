import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

# 🔹 Load dataset
df = pd.read_csv("quiz_dataset.csv")

# 🔹 Features (q1–q15)
X = df.iloc[:, :-1]

# 🔹 Target (dosha)
y = df["dosha"]

# 🔹 Train model
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=5,
    random_state=42
)

model.fit(X, y)

# 🔹 Save model
joblib.dump(model, "quiz_model.pkl")

print("✅ quiz_model.pkl created successfully")

# 🔹 Accuracy check (optional but good)
print("Accuracy:", model.score(X, y))
sample = [[0,1,2,0,1,2,0,1,2,0,1,2,0,1,2]]
print(model.predict(sample))