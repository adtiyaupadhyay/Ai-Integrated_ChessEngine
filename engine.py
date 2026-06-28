"""
engine.py
==========
ChessAI: the main class that ties the three knowledge databases (opening,
middlegame, endgame) together with the alpha-beta search, and decides, move
by move, whether to:

  1. play a known book move straight from the opening database,
  2. search with evaluation weights biased by the current opening's
     middlegame plan,
  3. or search with evaluation weights biased by endgame technique --

while tracking a running "advantage score" (its own evaluation, from its
own side's perspective) to choose an ATTACK / DEFENSE / BALANCED posture
and nudge the evaluation weights accordingly.
"""

import chess

from .opening_book import OpeningBook
from .middlegame_plans import MiddlegamePlans
from .endgame_principles import EndgamePrinciples
from .evaluation import evaluate, game_phase
from .search import AlphaBetaSearch

ATTACK, DEFENSE, BALANCED = "ATTACK", "DEFENSE", "BALANCED"

# Centipawn thresholds (from the engine's own perspective) that decide posture.
ATTACK_THRESHOLD = 150     # comfortably ahead -> press the advantage
DEFENSE_THRESHOLD = -150   # comfortably behind -> consolidate / complicate


class ChessAI:
    def __init__(self, color=chess.WHITE, max_depth=4, time_limit=5.0):
        self.color = color
        self.max_depth = max_depth
        self.time_limit = time_limit

        self.opening_book = OpeningBook()
        self.middlegame_plans = MiddlegamePlans()
        self.endgame_principles = EndgamePrinciples()

        self._played_uci = []         # full move history, for opening-book lookup
        self._current_opening = None  # (eco, name, plan_tag, notes)
        self.last_info = {}           # populated after each get_move() call, for UI/debugging

    # -- public API -----------------------------------------------------

    def reset(self):
        self._played_uci = []
        self._current_opening = None

    def note_move_played(self, move: chess.Move):
        """Call this for every move played in the game, by either side, so
        the engine's move-history / opening-recognition stays in sync even
        when the opponent (not the AI) is the one moving."""
        self._played_uci.append(move.uci())

    def get_move(self, board: chess.Board) -> chess.Move:
        phase = game_phase(board)

        identified = self.opening_book.identify_opening(self._played_uci)
        if identified:
            self._current_opening = identified

        # OPENING: prefer a book move if this exact position is in the DB.
        if phase == "opening":
            book_move_uci = self.opening_book.get_book_move(self._played_uci)
            if book_move_uci:
                move = chess.Move.from_uci(book_move_uci)
                if move in board.legal_moves:
                    self.last_info = {
                        "source": "opening_book",
                        "opening": self._current_opening,
                        "phase": phase,
                    }
                    return move

        weights, extra_depth, info_extra = self._weights_for_phase(board, phase)
        posture, advantage = self._posture(board, weights)
        weights = self._apply_posture(weights, posture)

        depth = self.max_depth + extra_depth
        searcher = AlphaBetaSearch(
            evaluate_fn=evaluate,
            weights=weights,
            max_depth=depth,
            time_limit=self.time_limit,
        )
        best_move, score, reached_depth = searcher.search(board)

        self.last_info = {
            "source": "search",
            "phase": phase,
            "opening": self._current_opening,
            "posture": posture,
            "advantage_cp": advantage,
            "depth_reached": reached_depth,
            "score_cp": score,
            "nodes": searcher.nodes,
            **info_extra,
        }
        return best_move

    # -- internals --------------------------------------------------------

    def _weights_for_phase(self, board, phase):
        info = {}
        if phase in ("opening", "middlegame") and self._current_opening:
            _, _, plan_tag, _ = self._current_opening
            plan = self.middlegame_plans.get_plan(plan_tag)
            if plan:
                info["plan_title"] = plan["title"]
                info["plan_description"] = plan["description"]
                return plan["weights"], 0, info

        if phase == "endgame":
            principles = self.endgame_principles.get_principles(board)
            if principles:
                merged, depth_bonus, titles = {}, 0, []
                for p in reversed(principles):  # most specific applied last == wins ties
                    merged.update(p["weights"])
                    depth_bonus = max(depth_bonus, p["depth_bonus"])
                    titles.append(p["title"])
                info["endgame_principles"] = titles
                return merged, depth_bonus, info

        return None, 0, info

    def _posture(self, board, weights):
        """Evaluate the position from the engine's own side's perspective to
        decide a posture. The margin (not just the sign) drives the choice,
        so the AI only commits to all-out attack when genuinely ahead, and
        only turns defensive when genuinely worse off."""
        raw_score = evaluate(board, weights)  # White's perspective, centipawns
        advantage = raw_score if self.color == chess.WHITE else -raw_score

        if advantage >= ATTACK_THRESHOLD:
            return ATTACK, advantage
        if advantage <= DEFENSE_THRESHOLD:
            return DEFENSE, advantage
        return BALANCED, advantage

    @staticmethod
    def _apply_posture(weights, posture):
        w = dict(weights) if weights else {}
        if posture == ATTACK:
            w["piece_activity"] = w.get("piece_activity", 1.0) * 1.2
            w["pawn_storm_kingside"] = w.get("pawn_storm_kingside", 1.0) * 1.2
            w["king_safety"] = w.get("king_safety", 1.0) * 0.9
        elif posture == DEFENSE:
            w["king_safety"] = w.get("king_safety", 1.0) * 1.3
            w["pawn_structure"] = w.get("pawn_structure", 1.0) * 1.2
            w["piece_activity"] = w.get("piece_activity", 1.0) * 0.9
        return w

    def close(self):
        self.opening_book.close()
        self.middlegame_plans.close()
        self.endgame_principles.close()
