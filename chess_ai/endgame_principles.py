"""
endgame_principles.py
======================
Wraps endgame.db. Given the current board, works out a rough "material
signature" (KPK, KRK, rook_endgame, opposite_bishops, ...) and returns the
matching endgame principles plus a recommended extra search-depth bonus
(endgames have few pieces, so searching deeper is cheap and accuracy
matters a lot there).
"""

import sqlite3
import json
import chess
from .db_setup import ENDGAME_DB


def _square_color(square: int) -> int:
    """0 or 1, consistent enough to tell same/opposite coloured squares apart."""
    return (chess.square_file(square) + chess.square_rank(square)) % 2


class EndgamePrinciples:
    def __init__(self, db_path=ENDGAME_DB):
        self._conn = sqlite3.connect(db_path, check_same_thread=False)

    @staticmethod
    def classify(board: chess.Board):
        """Rough material-signature classifier used to pick rows from
        endgame_principles. Returns candidate signature strings, most
        specific first; 'general_endgame' is always included as a fallback."""
        piece_map = board.piece_map()
        counts = {}
        for p in piece_map.values():
            sym = p.symbol().upper()
            if sym != "K":
                counts[sym] = counts.get(sym, 0) + 1

        non_king_total = sum(counts.values())
        signatures = []

        if non_king_total == 1 and counts.get("P", 0) == 1:
            signatures.append("KPK")
        if non_king_total == 1 and counts.get("R", 0) == 1:
            signatures.append("KRK")
        if counts.get("R", 0) >= 1:
            signatures.append("rook_endgame")
        if non_king_total == 2 and counts.get("B", 0) == 1 and counts.get("N", 0) == 1:
            signatures.append("KBNK")

        bishop_squares_by_color = {chess.WHITE: [], chess.BLACK: []}
        for sq, p in piece_map.items():
            if p.piece_type == chess.BISHOP:
                bishop_squares_by_color[p.color].append(sq)
        if len(bishop_squares_by_color[chess.WHITE]) == 1 and len(bishop_squares_by_color[chess.BLACK]) == 1 \
                and counts.get("N", 0) == 0 and counts.get("R", 0) == 0 and counts.get("Q", 0) == 0:
            wcolor = _square_color(bishop_squares_by_color[chess.WHITE][0])
            bcolor = _square_color(bishop_squares_by_color[chess.BLACK][0])
            signatures.append("opposite_bishops" if wcolor != bcolor else "same_bishops")

        if counts.get("Q", 0) >= 1:
            signatures.append("queen_endgame")
        if counts.get("N", 0) >= 1 and counts.get("B", 0) == 0 and counts.get("R", 0) == 0 \
                and counts.get("Q", 0) == 0:
            signatures.append("knight_endgame")
        if non_king_total == counts.get("P", 0) and non_king_total > 0:
            signatures.append("pawn_endgame")

        signatures.append("general_endgame")
        return signatures

    def get_principles(self, board: chess.Board):
        sigs = self.classify(board)
        results = []
        seen = set()
        for sig in sigs:
            if sig in seen:
                continue
            seen.add(sig)
            cur = self._conn.execute(
                "SELECT title, description, depth_bonus, weights_json "
                "FROM endgame_principles WHERE material_signature = ?",
                (sig,),
            )
            row = cur.fetchone()
            if row:
                title, description, depth_bonus, weights_json = row
                results.append({
                    "signature": sig,
                    "title": title,
                    "description": description,
                    "depth_bonus": depth_bonus,
                    "weights": json.loads(weights_json),
                })
        return results

    def close(self):
        self._conn.close()
