import os
import json
import numpy as np

from vision.embeddings import FaceEmbedder
from database.database import Database
from paths import data_root


LEGACY_JSON_PATH = os.path.join(data_root(), "identities.json")

# SFace's cosine-similarity threshold as published by the OpenCV Zoo
# benchmark (~0.363 at a 1e-3 false-positive rate on their test set).
# This is a starting point, not something we've measured ourselves —
# we'll revisit it once we have real accept/reject data from this laptop's
# camera (see Settings checkpoint for where this should become tunable).
DEFAULT_THRESHOLD = 0.363


class IdentityStore:
    """Persists one averaged embedding per enrolled identity in SQLite and
    matches a live embedding against all of them."""

    def __init__(self, db=None, threshold=DEFAULT_THRESHOLD):

        self.db = db if db is not None else Database()
        self.threshold = threshold
        self.identities = {}

        self._migrate_legacy_json()
        self._load()

    def _migrate_legacy_json(self):
        """One-time import: earlier checkpoints stored identities in
        data/identities.json. If that file exists and the database is
        still empty, pull it in instead of forcing a re-enrollment."""

        if not os.path.exists(LEGACY_JSON_PATH):
            return

        if self.db.user_count() > 0:
            return

        with open(LEGACY_JSON_PATH, "r") as f:
            raw = json.load(f)

        for name, entry in raw.items():
            self.db.upsert_user(
                name,
                entry["embedding"],
                entry.get("sample_count", 0)
            )

        migrated_path = LEGACY_JSON_PATH + ".migrated"
        os.replace(LEGACY_JSON_PATH, migrated_path)

        print(
            f"[Veylance] Migrated {len(raw)} identity(ies) from "
            f"identities.json into the database."
        )

    def _load(self):

        self.identities = {
            row["name"]: {
                "embedding": np.array(row["embedding"], dtype=np.float32),
                "sample_count": row["sample_count"],
                "enrolled_at": row["enrolled_at"]
            }
            for row in self.db.get_all_users()
        }

    def enroll(self, name, embeddings):
        """embeddings: list of (1, 128) or (128,) L2-normalized vectors
        captured during enrollment. Stores their mean, re-normalized."""

        if not embeddings:
            raise ValueError("No embeddings were captured for this enrollment.")

        stacked = np.stack([e.flatten() for e in embeddings], axis=0)
        mean_embedding = stacked.mean(axis=0)

        norm = np.linalg.norm(mean_embedding)
        if norm > 0:
            mean_embedding = mean_embedding / norm

        self.db.upsert_user(name, mean_embedding.tolist(), len(embeddings))
        self._load()

    def identify(self, embedding):
        """Returns (name, similarity) for the best match, or (None, best_similarity)
        if nothing clears the threshold. Returns (None, 0.0) if nothing is enrolled."""

        if not self.identities:
            return None, 0.0

        best_name = None
        best_score = -1.0

        for name, entry in self.identities.items():
            score = FaceEmbedder.cosine_similarity(embedding, entry["embedding"])
            if score > best_score:
                best_score = score
                best_name = name

        if best_score >= self.threshold:
            return best_name, best_score

        return None, best_score

    def has_identity(self, name):
        return name in self.identities

    def remove(self, name):
        if name in self.identities:
            self.db.delete_user(name)
            self._load()
