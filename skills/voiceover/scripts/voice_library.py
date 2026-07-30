"""Read and write the persistent voice library shared by all voice-over runs.

Recurring people — a prime minister, a channel's regular host — turn up across
many videos. Cutting a fresh reference clip for each run gives them a different
German voice every time and costs a rate measurement every time. The library
stores what F5-TTS actually needs, so the second video reuses the first video's
work:

    ref_file   the clip itself, already 24 kHz mono, ready to hand to F5-TTS
    ref_text   its wording
    rate       the measured clone rate, so measure_rate.py can be skipped
    embedding  the ECAPA centroid, so the person can be recognised again

The embedding is what makes this automatic. Without it the library would be a
list you have to match by hand; with it, match_voices.py compares the centroid
of every cluster in the new video against every stored voice.

Layout, next to the skill and travelling with it:

    voices/index.json
    voices/<id>.wav

This module holds only what both match_voices.py and add_voice.py need.
"""

import json
import os
import re
import unicodedata

import numpy as np

# Same as diarize_ecapa.py: what F5-TTS resamples to internally.
REF_RATE = 24000
DIMS = 192

# Both centroids compared here are L2-normalised, so a dot product is the cosine.
# Measured across three recordings of the same people: the same person scored 0.64
# to 0.99 depending on how far apart the two recordings were, different people 0.05
# to 0.37.
#
# The thresholds sit low in that gap on purpose, because the two ways of being
# wrong do not cost the same. A missed match sends the speaker back to a clip cut
# from the current video, which on poor material means artefacts, filler words and
# a wrong speaking rate. A false match gives them a clean, rate-measured voice that
# merely belongs to someone else — and since the clone does not reproduce the
# original voice anyway (see "Der Klon trennt Sprecher"), that costs far less than
# it sounds. Being tolerant is the cheaper error here.
#
# The one exception is enforced in match_voices.py: two speakers of the same video
# must never end up on the same stored voice, because that destroys the separation
# the whole pipeline exists for.
MATCH_SURE = 0.45
MATCH_MAYBE = 0.30


def default_dir() -> str:
    """The library that ships with the skill, regardless of the working folder."""
    return os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "voices")


def index_path(library: str) -> str:
    return os.path.join(library, "index.json")


def load(library: str) -> dict:
    """Read the index, returning an empty one if the library does not exist yet."""
    path = index_path(library)
    if not os.path.exists(path):
        return {"model": None, "voices": []}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save(library: str, index: dict) -> None:
    os.makedirs(library, exist_ok=True)
    with open(index_path(library), "w", encoding="utf-8") as handle:
        json.dump(index, handle, ensure_ascii=False, indent=1)


def embedding_of(entry: dict) -> np.ndarray:
    vector = np.asarray(entry["embedding"], dtype=np.float32)
    return vector / max(float(np.linalg.norm(vector)), 1e-9)


def centroid(embeddings: np.ndarray, indices) -> np.ndarray:
    """Average the unit embeddings of one speaker into a single direction.

    The centroid over many utterances is a far steadier fingerprint than any one
    clip: single units scattered down to 0.49 against their own centroid in the
    reference run, while the centroid of one half of a speaker's units matched
    the other half at 0.99.
    """
    vector = np.asarray(embeddings)[list(indices)].mean(axis=0)
    return vector / max(float(np.linalg.norm(vector)), 1e-9)


def clip_path(library: str, entry: dict) -> str:
    """Absolute, because the path is written into a speakers.json that later
    steps read from whatever folder they happen to run in."""
    return os.path.abspath(os.path.join(library, entry["audio"]))


def count(number: int) -> str:
    return "eine Stimme" if number == 1 else f"{number} Stimmen"


def slug(name: str) -> str:
    """A file-safe id from a person's name: 'Király Tamás' -> 'kiraly-tamas'."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", plain.lower())).strip("-")
