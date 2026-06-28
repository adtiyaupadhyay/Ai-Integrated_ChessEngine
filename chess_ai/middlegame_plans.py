"""
middlegame_plans.py
====================
Wraps middlegame.db: given a `plan_tag` (looked up from the opening that was
played), returns the strategic plan text plus an evaluation-weight dict that
the engine uses to bias its evaluation function while still in the
middlegame phase tied to that opening.
"""

import sqlite3
import json
from .db_setup import MIDDLEGAME_DB

DEFAULT_WEIGHTS = {
    "material": 1.0,
    "center_control": 1.0,
    "king_safety": 1.0,
    "piece_activity": 1.0,
    "pawn_structure": 1.0,
    "space": 1.0,
    "pawn_storm_kingside": 1.0,
    "king_activity": 1.0,
    "passed_pawn": 1.0,
    "rook_activity": 1.0,
    "bishop_activity": 1.0,
    "knight_activity": 1.0,
    "queen_activity": 1.0,
}


class MiddlegamePlans:
    def __init__(self, db_path=MIDDLEGAME_DB):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)

    def get_plan(self, plan_tag):
        if not plan_tag:
            return None
        cur = self._conn.execute(
            "SELECT title, description, weights_json FROM plans WHERE plan_tag = ?",
            (plan_tag,),
        )
        row = cur.fetchone()
        if not row:
            return None
        title, description, weights_json = row
        weights = dict(DEFAULT_WEIGHTS)
        weights.update(json.loads(weights_json))
        return {"title": title, "description": description, "weights": weights}

    def close(self):
        self._conn.close()
