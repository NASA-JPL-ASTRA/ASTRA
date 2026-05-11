"""
AiSTRA Channel Search — TF-IDF over the channel dictionary.

Lifted from telemetry/channel_search.py (unchanged behavior).
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

CHANNEL_DICTIONARY = {
    "motors.motor1_current":     "motor 1 current draw amperes",
    "motors.motor2_current":     "motor 2 current draw amperes",
    "motors.motor3_current":     "motor 3 current draw amperes",
    "motors.motor4_current":     "motor 4 current draw amperes rear right wheel",
    "motors.motor1_speed":       "motor 1 speed rpm rotation",
    "motors.motor2_speed":       "motor 2 speed rpm rotation",
    "motors.motor3_speed":       "motor 3 speed rpm rotation",
    "motors.motor4_speed":       "motor 4 speed rpm rotation rear right wheel",
    "motors.motor1_temperature": "motor 1 temperature thermal degrees celsius heat",
    "motors.motor2_temperature": "motor 2 temperature thermal degrees celsius heat",
    "motors.motor3_temperature": "motor 3 temperature thermal degrees celsius heat",
    "motors.motor4_temperature": "motor 4 temperature thermal degrees celsius heat rear right wheel",
    "imu.accel_x":               "imu accelerometer x axis lateral acceleration",
    "imu.accel_y":               "imu accelerometer y axis forward acceleration",
    "imu.accel_z":               "imu accelerometer z axis vertical acceleration gravity",
    "nav.position_x":            "navigation position x lateral location meters",
    "nav.position_y":            "navigation position y forward distance traveled meters",
    "nav.position_z":            "navigation position z altitude height elevation meters",
    "system.fault_code":         "fault code error status system health hex",
}

_channel_names = list(CHANNEL_DICTIONARY.keys())
_descriptions = list(CHANNEL_DICTIONARY.values())

_vectorizer = TfidfVectorizer(
    analyzer="word",
    ngram_range=(1, 2),
    lowercase=True,
)
_tfidf_matrix = _vectorizer.fit_transform(_descriptions)


def search_channel(query: str, top_k: int = 3) -> list:
    query_vec = _vectorizer.transform([query.lower()])
    scores = cosine_similarity(query_vec, _tfidf_matrix).flatten()
    top_indices = np.argsort(scores)[::-1][:top_k]

    return [
        {"channel": _channel_names[i], "score": round(float(scores[i]), 4)}
        for i in top_indices
        if scores[i] > 0.0
    ]
