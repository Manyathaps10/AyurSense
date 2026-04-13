import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib

data = pd.read_csv("quiz_dataset.csv")

# 🔥 FIX
data = data.dropna()

X = data.drop("dosha", axis=1)
y = data["dosha"]

model = RandomForestClassifier()
model.fit(X, y)

joblib.dump(model, "quiz_model.pkl")

print("✅ Model retrained successfully!")