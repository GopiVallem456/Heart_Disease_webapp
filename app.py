from flask import Flask, render_template, request, redirect, url_for, session, flash
import joblib
from pymongo import MongoClient
from datetime import datetime
from pathlib import Path
import json
import copy
import os

# -------------------- LOAD ENV --------------------
from dotenv import load_dotenv
load_dotenv()

# -------------------- APP CONFIG --------------------
app = Flask(
    __name__,
    template_folder="templates",   # ✅ FIXED
    static_folder="static"         # ✅ FIXED
)

app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")


# -------------------- MONGODB CONFIG --------------------
MONGO_URI = os.environ.get("MONGO_URI")

client = None
users_collection = None
predictions_collection = None
local_db = None


class LocalCursor:
    def __init__(self, documents):
        self._documents = documents

    def sort(self, key, direction=-1):
        reverse = direction < 0
        return LocalCursor(sorted(self._documents, key=lambda item: item.get(key), reverse=reverse))

    def __iter__(self):
        return iter(self._documents)


class LocalCollection:
    def __init__(self, database, name):
        self.database = database
        self.name = name

    def create_index(self, *args, **kwargs):
        return None

    def find_one(self, query):
        for document in self.database.read()[self.name]:
            if all(document.get(key) == value for key, value in query.items()):
                return copy.deepcopy(document)
        return None

    def insert_one(self, document):
        stored_document = self.database.prepare_for_save(document)
        data = self.database.read()
        data[self.name].append(stored_document)
        self.database.write(data)
        return stored_document

    def update_one(self, query, update):
        data = self.database.read()
        for document in data[self.name]:
            if all(document.get(key) == value for key, value in query.items()):
                if "$set" in update:
                    for key, value in update["$set"].items():
                        document[key] = self.database.prepare_value_for_save(key, value)
                    self.database.write(data)
                return document
        return None

    def find(self, query):
        matched = [
            copy.deepcopy(document)
            for document in self.database.read()[self.name]
            if all(document.get(key) == value for key, value in query.items())
        ]
        return LocalCursor(matched)


class LocalDatabase:
    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file()

    def _ensure_file(self):
        if not self.file_path.exists():
            self.write({"users": [], "predictions": []})

    def read(self):
        self._ensure_file()
        with self.file_path.open("r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        data.setdefault("users", [])
        data.setdefault("predictions", [])

        for collection_name in ("users", "predictions"):
            for document in data[collection_name]:
                timestamp = document.get("timestamp")
                if isinstance(timestamp, str):
                    try:
                        document["timestamp"] = datetime.fromisoformat(timestamp)
                    except ValueError:
                        pass
        return data

    def write(self, data):
        serializable = copy.deepcopy(data)
        for collection_name in ("users", "predictions"):
            for document in serializable[collection_name]:
                timestamp = document.get("timestamp")
                if isinstance(timestamp, datetime):
                    document["timestamp"] = timestamp.isoformat()

        with self.file_path.open("w", encoding="utf-8") as file_handle:
            json.dump(serializable, file_handle, indent=2)

    def prepare_value_for_save(self, key, value):
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def prepare_for_save(self, document):
        stored_document = copy.deepcopy(document)
        for key, value in stored_document.items():
            stored_document[key] = self.prepare_value_for_save(key, value)
        return stored_document

    def collection(self, name):
        return LocalCollection(self, name)


def get_db_collections():
    """Initialize MongoDB connection on first use"""
    global client, users_collection, predictions_collection, local_db

    if users_collection is None:
        if not MONGO_URI:
            print("⚠️ MONGO_URI not set - using local JSON storage fallback")
            local_db = LocalDatabase(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "local_db.json"))
            users_collection = local_db.collection("users")
            predictions_collection = local_db.collection("predictions")
            return users_collection, predictions_collection

        try:
            # Increase timeout and add connection options for better reliability
            client = MongoClient(
                MONGO_URI, 
                serverSelectionTimeoutMS=10000,  # 10 seconds timeout
                connectTimeoutMS=10000,
                socketTimeoutMS=10000
            )
            # Test connection
            client.admin.command("ping")
            
            db = client["heart_app"]
            users_collection = db["users"]
            predictions_collection = db["predictions"]

            # Create index if it doesn't exist
            try:
                users_collection.create_index("username", unique=True)
            except Exception:
                pass  # Index might already exist
            
            print("✅ MongoDB connected successfully")

        except Exception as e:
            import traceback

            print("\n========== MONGODB ERROR ==========")
            print("Error:", e)
            traceback.print_exc()
            print("===================================\n")

            client = None
            local_db = LocalDatabase(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "local_db.json")
            )
            users_collection = local_db.collection("users")
            predictions_collection = local_db.collection("predictions")
            return users_collection, predictions_collection

    return users_collection, predictions_collection


# -------------------- LOAD ML MODEL --------------------
model = None
model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "heart_disease_model.pkl")

try:
    model = joblib.load(model_path)
    print("✅ ML model loaded")
except Exception as e:
    print(f"⚠️ Model loading failed: {e}")


# -------------------- ROUTES --------------------
@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/home")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", user=session["user"])


# -------------------- LOGIN --------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    users_coll, _ = get_db_collections()

    if "user" in session:
        return redirect(url_for("home"))

    if request.method == "POST":
        # Normalize input to avoid issues with accidental spaces/case
        username = request.form["username"].strip().lower()
        password = request.form["password"]

        if users_coll is None:
            flash("Database unavailable", "danger")
            return render_template("login.html")

        user = users_coll.find_one({"username": username})
        if user and user["password"] == password:
            session["user"] = username
            return redirect(url_for("home"))

        flash("Invalid credentials", "danger")

    return render_template("login.html")


# -------------------- REGISTER --------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    users_coll, _ = get_db_collections()

    if request.method == "POST":
        # Normalize input to keep usernames consistent
        username = request.form["username"].strip().lower()
        password = request.form["password"]

        if users_coll is None:
            flash("Database unavailable", "danger")
            return render_template("register.html")

        existing = users_coll.find_one({"username": username})
        if existing:
            # Treat re-register as password reset for simplicity
            users_coll.update_one(
                {"_id": existing["_id"]},
                {"$set": {"password": password, "updated_at": datetime.now()}}
            )
            flash("User already existed – password updated. Please login.", "info")
            return redirect(url_for("login"))
        else:
            users_coll.insert_one({
                "username": username,
                "password": password,
                "created_at": datetime.now()
            })
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


# -------------------- LOGOUT --------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for("login"))


# -------------------- PREDICT --------------------
@app.route("/predict", methods=["GET", "POST"])
def predict():
    _, pred_coll = get_db_collections()

    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        if model is None:
            flash("Model unavailable", "danger")
            return render_template("predict.html")

        fields = [
            "age", "sex", "cp", "trestbps", "chol",
            "fbs", "restecg", "thalach", "exang",
            "oldpeak", "slope", "ca", "thal"
        ]

        if any(not request.form.get(f) for f in fields):
            flash("Please fill all fields", "danger")
            return render_template("predict.html")

        try:
            features = [float(request.form[f]) for f in fields]
        except ValueError:
            flash("Invalid numeric input", "danger")
            return render_template("predict.html")

        prediction = int(model.predict([features])[0])

        if pred_coll is not None:
            pred_coll.insert_one({
                "username": session["user"],
                "timestamp": datetime.now(),
                "features": dict(zip(fields, features)),
                "prediction_result": prediction
            })

        return render_template("result.html", prediction=prediction)

    return render_template("predict.html")


# -------------------- HISTORY --------------------
@app.route("/history")
def history():
    _, pred_coll = get_db_collections()

    if "user" not in session:
        return redirect(url_for("login"))

    predictions = []
    if pred_coll is not None:
        predictions = list(
            pred_coll.find({"username": session["user"]}).sort("timestamp", -1)
        )

    return render_template("history.html", predictions=predictions)


# -------------------- MODEL PERFORMANCE --------------------
@app.route("/model_performance")
def model_performance():
    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("model_performance.html", user=session["user"])


# -------------------- RISK ANALYSIS --------------------
@app.route("/risk_analysis")
def risk_analysis():
    _, pred_coll = get_db_collections()

    if "user" not in session:
        return redirect(url_for("login"))

    preds = list(pred_coll.find({"username": session["user"]})) if pred_coll is not None else []

    return render_template(
        "risk_analysis.html",
        user=session["user"],
        high_risk_count=sum(p["prediction_result"] == 1 for p in preds),
        low_risk_count=sum(p["prediction_result"] == 0 for p in preds),
        predictions=preds
    )


# -------------------- PROFILE --------------------
@app.route("/profile")
def profile():
    _, pred_coll = get_db_collections()

    if "user" not in session:
        return redirect(url_for("login"))

    preds = list(pred_coll.find({"username": session["user"]})) if pred_coll is not None else []

    return render_template(
        "profile.html",
        user=session["user"],
        total_predictions=len(preds),
        high_risk_count=sum(p["prediction_result"] == 1 for p in preds),
        low_risk_count=sum(p["prediction_result"] == 0 for p in preds)
    )


# -------------------- RUN --------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
