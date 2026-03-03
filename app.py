from flask import Flask, request, jsonify
from textblob import TextBlob
import re
import json
import os

app = Flask(__name__)

ANALYTICS_FILE = "analytics_data.json"

# ---------------- LOAD ANALYTICS ----------------
if os.path.exists(ANALYTICS_FILE):
    with open(ANALYTICS_FILE, "r") as f:
        data = json.load(f)
        total_messages = data.get("total_messages", 0)
        toxic_messages = data.get("toxic_messages", 0)
        blocked_messages = data.get("blocked_messages", 0)
        word_frequency = data.get("word_frequency", {})
        user_stats = data.get("user_stats", {})
else:
    total_messages = 0
    toxic_messages = 0
    blocked_messages = 0
    word_frequency = {}
    user_stats = {}

def save_analytics():
    with open(ANALYTICS_FILE, "w") as f:
        json.dump({
            "total_messages": total_messages,
            "toxic_messages": toxic_messages,
            "blocked_messages": blocked_messages,
            "word_frequency": word_frequency,
            "user_stats": user_stats
        }, f)

# ---------------- WORD LISTS ----------------

MILD_WORDS = [
    "stupid","destroy","eradicate","decimate","idiot","fool","dumb","useless","loser","crazy","mad","annoying","irritating",
    "nonsense","pathetic","ridiculous","lazy","selfish","arrogant","childish","clown","fake","shameless",
    "ignorant","weak","boring","rude","immature","silly","awkward","embarrassing","lame","trash",
    "worthless","hopeless","brainless","careless","clueless","disgusting","unbelievable","horrible","terrible","bad",
    "mean","jealous","dramatic","overreacting","stubborn","moody","messy","unreliable","slow","weird"
]

EXTREME_WORDS = [
    "fuck","fucker","motherfucker","fucking","shit","bullshit","bitch","bastard","asshole","dickhead",
    "piss","slut","whore","cunt","retard","moron","jackass","scumbag","dipshit","jerk",
    "wtf","stfu","suck","freak","nutcase","psycho","pervert","crap","douche","scum",
    "filthy","garbage","kill you","shut up","get lost","piece of shit","son of a","dirty pig","ugly pig","low life",
    "cheap trash","filthy animal","worthless trash","rotten","damn you","bloody hell","hate you","go to hell","screw you","trash bag"
]

# ---------------- NORMALIZATION ----------------

def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z\s]', '', text)
    return text

# ---------------- ANALYZE ROUTE ----------------

@app.route("/analyze", methods=["POST"])
def analyze():
    global total_messages, toxic_messages, blocked_messages
    global word_frequency, user_stats

    data = request.json
    message = data.get("message", "")
    username = data.get("username", "Unknown")

    if username not in user_stats:
        user_stats[username] = {
            "total": 0,
            "toxic": 0,
            "blocked": 0
        }

    total_messages += 1
    user_stats[username]["total"] += 1

    clean = normalize_text(message)

    mild_detected = [word for word in MILD_WORDS if word in clean]
    extreme_detected = [word for word in EXTREME_WORDS if word in clean]

    polarity = TextBlob(message).sentiment.polarity

    # -------- EXTREME AUTO BLOCK --------
    if extreme_detected:
        blocked_messages += 1
        toxic_messages += 1

        user_stats[username]["toxic"] += 1
        user_stats[username]["blocked"] += 1

        for word in extreme_detected:
            word_frequency[word] = word_frequency.get(word, 0) + 1

        save_analytics()

        return jsonify({
            "toxic": True,
            "score": -1.0,
            "suggestion": "BLOCKED"
        })

    # -------- MILD / SENTIMENT --------
    toxic = bool(mild_detected) or polarity < -0.3

    if toxic:
        toxic_messages += 1
        user_stats[username]["toxic"] += 1

        for word in mild_detected:
            word_frequency[word] = word_frequency.get(word, 0) + 1

    save_analytics()

    suggestion = (
        "Please express this message politely."
        if toxic else message
    )

    return jsonify({
        "toxic": toxic,
        "score": polarity,
        "suggestion": suggestion
    })

# ---------------- ANALYTICS ROUTE ----------------

@app.route("/analytics", methods=["GET"])
def analytics():
    toxicity_percentage = (
        (toxic_messages / total_messages) * 100
        if total_messages > 0 else 0
    )

    return jsonify({
        "total_messages": total_messages,
        "toxic_messages": toxic_messages,
        "blocked_messages": blocked_messages,
        "toxicity_percentage": round(toxicity_percentage, 2),
        "word_frequency": word_frequency,
        "user_stats": user_stats
    })

# ---------------- RESET ROUTE ----------------

@app.route("/reset", methods=["GET"])
def reset():
    global total_messages, toxic_messages, blocked_messages
    global word_frequency, user_stats

    total_messages = 0
    toxic_messages = 0
    blocked_messages = 0
    word_frequency = {}
    user_stats = {}

    save_analytics()

    return jsonify({
        "status": "Analytics reset successful"
    })

# ---------------- RUN APP ----------------

if __name__ == "__main__":
    app.run()
