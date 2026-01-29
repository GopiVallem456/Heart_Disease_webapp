from flask import Flask, render_template, request, redirect, url_for, session, flash
import joblib
from pymongo import MongoClient
from datetime import datetime
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


def get_db_collections():
    """Initialize MongoDB connection on first use"""
    global client, users_collection, predictions_collection

    if users_collection is None:
        if not MONGO_URI:
            print("⚠️ MONGO_URI not set - check your .env file")
            return None, None

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
            error_msg = str(e)
            print(f"⚠️ MongoDB connection error: {error_msg}")
            print(f"Full error: {traceback.format_exc()}")
            # Don't set collections to None permanently - allow retry
            client = None
            return None, None

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
