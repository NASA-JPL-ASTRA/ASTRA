"""
AiSTRA Channel Search

TF-IDF fuzzy search over a channel name dictionary.
Lets the LLM resolve natural language like "bus voltage" or "front motor temp"
to an exact channel name like "motors.motor1_current".

Usage:
    from channel_search import search_channel
    results = search_channel("motor temperature", top_k=3)
    # [{"channel": "motors.motor1_temperature", "score": 0.82}, ...]
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# ── Channel dictionary ────────────────────────────────────────────────────────
# Each entry is: exact_channel_name -> human description
# The description is what gets indexed for search — so write it the way an
# operator would naturally describe the channel in speech.
#
# In production this would be loaded from the AMPCS channel dictionary export.
# For the prototype it covers all channels from the telemetry generator.

CHANNEL_DICTIONARY = {
    # Motor currents
    "motors.motor1_current":     "motor 1 current draw amperes",
    "motors.motor2_current":     "motor 2 current draw amperes",
    "motors.motor3_current":     "motor 3 current draw amperes",
    "motors.motor4_current":     "motor 4 current draw amperes rear right wheel",

    # Motor speeds
    "motors.motor1_speed":       "motor 1 speed rpm rotation",
    "motors.motor2_speed":       "motor 2 speed rpm rotation",
    "motors.motor3_speed":       "motor 3 speed rpm rotation",
    "motors.motor4_speed":       "motor 4 speed rpm rotation rear right wheel",

    # Motor temperatures
    "motors.motor1_temperature": "motor 1 temperature thermal degrees celsius heat",
    "motors.motor2_temperature": "motor 2 temperature thermal degrees celsius heat",
    "motors.motor3_temperature": "motor 3 temperature thermal degrees celsius heat",
    "motors.motor4_temperature": "motor 4 temperature thermal degrees celsius heat rear right wheel",

    # IMU
    "imu.accel_x":               "imu accelerometer x axis lateral acceleration",
    "imu.accel_y":               "imu accelerometer y axis forward acceleration",
    "imu.accel_z":               "imu accelerometer z axis vertical acceleration gravity",

    # Navigation / position
    "nav.position_x":            "navigation position x lateral location meters",
    "nav.position_y":            "navigation position y forward distance traveled meters",
    "nav.position_z":            "navigation position z altitude height elevation meters",

    # System
    "system.fault_code":         "fault code error status system health hex",
}

# ── Build the TF-IDF index at import time ─────────────────────────────────────
# This runs once when the module is first imported. The vectorizer is then
# reused for every search query — no recomputation on each call.

_channel_names = list(CHANNEL_DICTIONARY.keys())
_descriptions  = list(CHANNEL_DICTIONARY.values())

_vectorizer = TfidfVectorizer(
    analyzer  = "word",
    ngram_range = (1, 2),   # match single words and two-word phrases
    lowercase = True,
)
_tfidf_matrix = _vectorizer.fit_transform(_descriptions)


def search_channel(query: str, top_k: int = 3) -> list:
    """
    Return the top_k channel names that best match a natural language query.

    Args:
        query   Natural language description, e.g. "motor temperature" or "position y"
        top_k   Number of results to return (default 3)

    Returns:
        List of dicts sorted by score descending:
        [{"channel": "motors.motor1_temperature", "score": 0.82}, ...]

    How it works:
        1. Transform the query into the same TF-IDF vector space as the descriptions
        2. Compute cosine similarity between the query vector and every description
        3. Return the top_k highest-scoring channels
        Cosine similarity ranges from 0.0 (no match) to 1.0 (exact match).
        In practice, scores above 0.3 are usually correct matches.
    """
    query_vec = _vectorizer.transform([query.lower()])
    scores    = cosine_similarity(query_vec, _tfidf_matrix).flatten()
    top_indices = np.argsort(scores)[::-1][:top_k]

    return [
        {"channel": _channel_names[i], "score": round(float(scores[i]), 4)}
        for i in top_indices
        if scores[i] > 0.0   # omit channels with zero relevance
    ]