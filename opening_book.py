"""
opening_book.py
================
Wraps opening.db: looks up book moves for the current position (by UCI
move-sequence prefix) and identifies which named opening (and its
`plan_tag`) the game is following -- so the middlegame stage can keep using
the right strategic plan even after the engine has left "book".
"""

import sqlite3
import random
from .db_setup import OPENING_DB


class OpeningBook:
    def __init__(self, db_path=OPENING_DB):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)

    def general_principles(self):
        cur = self._conn.execute("SELECT category, principle FROM general_principles")
        return cur.fetchall()

    def _all_openings(self):
        cur = self._conn.execute(
            "SELECT eco, name, moves_uci, plan_tag, notes, popularity FROM openings"
        )
        return cur.fetchall()

    def identify_opening(self, played_uci_moves):
        """Return (eco, name, plan_tag, notes) for the longest stored line
        that is a prefix-match of the moves played so far, or None."""
        played = list(played_uci_moves)
        best = None
        best_len = 0
        for eco, name, moves_uci, plan_tag, notes, _ in self._all_openings():
            book_moves = moves_uci.split()
            match_len = 0
            for a, b in zip(played, book_moves):
                if a != b:
                    break
                match_len += 1
            if match_len > 0 and match_len > best_len:
                best_len = match_len
                best = (eco, name, plan_tag, notes)
        return best

    def get_book_move(self, played_uci_moves):
        """Return a recommended next move (uci string) if the current
        position is still inside one of the stored lines, chosen by a
        popularity-weighted random pick. Returns None once out of book."""
        played = list(played_uci_moves)
        ply = len(played)
        candidates = []
        for eco, name, moves_uci, plan_tag, notes, popularity in self._all_openings():
            book_moves = moves_uci.split()
            if len(book_moves) <= ply:
                continue
            if book_moves[:ply] == played:
                candidates.append((book_moves[ply], popularity))
        if not candidates:
            return None
        moves, weights = zip(*candidates)
        return random.choices(moves, weights=weights, k=1)[0]

    def close(self):
        self._conn.close()
