import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import label_binarize
from sklearn.metrics import roc_curve, auc, accuracy_score

# 📥 Load dataset
data = pd.read_excel("AyurGenixAI_dataset.xlsx")

# 🎯 Use only required columns
data = data[["Symptoms", "Disease"]]
data = data.dropna()

# 🔤 Text → numeric
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(data["Symptoms"])
y = data["Disease"]

# 🔀 Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 🤖 Model
model = RandomForestClassifier()
model.fit(X_train, y_train)

# 🔥 Classes
classes = model.classes_

# 🔁 Binarize
y_test_bin = label_binarize(y_test, classes=classes)

# 📊 Probabilities
y_scores = model.predict_proba(X_test)

# 📈 Plot
plt.figure(figsize=(10, 7))

# ✅ Show only top 5 classes (clean graph)
top_n = 5

for i in range(min(top_n, len(classes))):

    # skip empty classes
    if i >= y_test_bin.shape[1] or sum(y_test_bin[:, i]) == 0:
        continue

    fpr, tpr, _ = roc_curve(y_test_bin[:, i], y_scores[:, i])
    roc_auc = auc(fpr, tpr)

    plt.plot(fpr, tpr, label=f"{classes[i]} (AUC={roc_auc:.2f})")

# 🔥 Micro-average ROC
fpr_micro, tpr_micro, _ = roc_curve(
    y_test_bin.ravel(), y_scores.ravel()
)
roc_auc_micro = auc(fpr_micro, tpr_micro)

plt.plot(
    fpr_micro,
    tpr_micro,
    color="black",
    linewidth=3,
    label=f"Micro-average ROC (AUC={roc_auc_micro:.2f})"
)

# random line
plt.plot([0, 1], [0, 1], linestyle='--')

plt.xlabel("False Positive Rate")
plt.ylabel("True Positive Rate")
plt.title("ROC Curve - AyurSense Disease Prediction")
plt.legend()

plt.savefig("roc_graph.png")
plt.show()
