"""
search.py
==========
Alpha-beta (negamax) search with:
  - iterative deepening, so the engine always has a move ready within a
    time budget even if a deeper search doesn't finish
  - a transposition table keyed by Zobrist hash, to avoid re-searching
    positions reached by a different move order
  - MVV-LVA capture ordering, two killer-move slots per ply, and a
    transposition-table best-move hint, all used to order moves so that
    alpha-beta cuts off as much of the tree as possible
  - a quiescence search (captures only) at the leaves, to avoid the
    "horizon effect" where a tactic is missed just because it's one ply
    past the search limit
"""

import time
import chess
import chess.polyglot

EXACT, LOWER, UPPER = 0, 1, 2
MATE_SCORE = 999000


class SearchTimeout(Exception):
    pass


class AlphaBetaSearch:
    def __init__(self, evaluate_fn, weights=None, max_depth=4, time_limit=5.0):
        """
        evaluate_fn : function(board, weights) -> centipawn score, White's perspective
        weights     : evaluation-weight dict biasing the static eval (supplied by the
                      opening/middlegame/endgame databases + attack/defence posture)
        max_depth   : hard ceiling on iterative deepening
        time_limit  : seconds before the search must return its best move so far
        """
        self.evaluate_fn = evaluate_fn
        self.weights = weights
        self.max_depth = max_depth
        self.time_limit = time_limit
        self.tt = {}
        self.killers = {}
        self._deadline = None
        self.nodes = 0

    def search(self, board: chess.Board):
        """Iterative deepening driver. Returns (best_move, score_cp, depth_reached).

        Operates on a private COPY of the board. This is essential: if a
        search is interrupted mid-recursion by SearchTimeout, any push()
        without its matching pop() must never leak back into the caller's
        real game board."""
        board = board.copy()
        self._deadline = time.time() + self.time_limit
        self.nodes = 0
        best_move, best_score, reached_depth = None, 0, 0

        for depth in range(1, self.max_depth + 1):
            try:
                score, move = self._root(board, depth)
                if move is not None:
                    best_move, best_score, reached_depth = move, score, depth
            except SearchTimeout:
                break
            if time.time() >= self._deadline:
                break

        if best_move is None:
            legal = list(board.legal_moves)
            best_move = legal[0] if legal else None
        return best_move, best_score, reached_depth

    # -- internals ----------------------------------------------------------

    def _check_time(self):
        self.nodes += 1
        if self.nodes % 2048 == 0 and time.time() >= self._deadline:
            raise SearchTimeout()

    def _root(self, board, depth):
        best_move, best_score = None, -float("inf")
        alpha, beta = -float("inf"), float("inf")
        sign = 1 if board.turn == chess.WHITE else -1

        for move in self._ordered_moves(board, 0):
            board.push(move)
            try:
                score = -self._negamax(board, depth - 1, -beta, -alpha, 1)
            finally:
                board.pop()
            if score > best_score:
                best_score, best_move = score, move
            alpha = max(alpha, score)

        return sign * best_score, best_move

    def _negamax(self, board, depth, alpha, beta, ply):
        self._check_time()

        key = chess.polyglot.zobrist_hash(board)
        tt_entry = self.tt.get(key)
        if tt_entry and tt_entry[0] >= depth:
            tt_depth, tt_score, tt_flag, tt_move = tt_entry
            if tt_flag == EXACT:
                return tt_score
            if tt_flag == LOWER:
                alpha = max(alpha, tt_score)
            elif tt_flag == UPPER:
                beta = min(beta, tt_score)
            if alpha >= beta:
                return tt_score

        if board.is_checkmate():
            return -MATE_SCORE + ply
        if board.is_stalemate() or board.is_insufficient_material():
            return 0

        if depth <= 0:
            return self._quiescence(board, alpha, beta, ply)

        best_score, best_move = -float("inf"), None
        original_alpha = alpha

        for move in self._ordered_moves(board, ply):
            board.push(move)
            try:
                score = -self._negamax(board, depth - 1, -beta, -alpha, ply + 1)
            finally:
                board.pop()

            if score > best_score:
                best_score, best_move = score, move
            alpha = max(alpha, score)
            if alpha >= beta:
                self._store_killer(ply, move)
                break

        flag = EXACT
        if best_score <= original_alpha:
            flag = UPPER
        elif best_score >= beta:
            flag = LOWER
        self.tt[key] = (depth, best_score, flag, best_move)
        return best_score

    def _quiescence(self, board, alpha, beta, ply, qdepth=0):
        self._check_time()
        sign = 1 if board.turn == chess.WHITE else -1
        stand_pat = sign * self.evaluate_fn(board, self.weights)

        if stand_pat >= beta:
            return stand_pat
        alpha = max(alpha, stand_pat)

        if qdepth >= 6:
            return stand_pat

        for move in self._ordered_moves(board, ply, captures_only=True):
            board.push(move)
            try:
                score = -self._quiescence(board, -beta, -alpha, ply + 1, qdepth + 1)
            finally:
                board.pop()
            if score >= beta:
                return score
            alpha = max(alpha, score)

        return alpha

    def _store_killer(self, ply, move):
        slots = self.killers.setdefault(ply, [])
        if move not in slots:
            slots.insert(0, move)
            del slots[2:]

    def _ordered_moves(self, board, ply, captures_only=False):
        moves = list(board.legal_moves)
        if captures_only:
            moves = [m for m in moves if board.is_capture(m)]

        killers = self.killers.get(ply, [])
        tt_move = None
        if not captures_only:
            key = chess.polyglot.zobrist_hash(board)
            entry = self.tt.get(key)
            if entry:
                tt_move = entry[3]

        def score_move(m):
            if m == tt_move:
                return 10000
            if board.is_capture(m):
                victim = board.piece_at(m.to_square)
                attacker = board.piece_at(m.from_square)
                victim_val = victim.piece_type if victim else 0
                attacker_val = attacker.piece_type if attacker else 0
                return 1000 + victim_val * 10 - attacker_val
            if m in killers:
                return 500
            if m.promotion:
                return 800
            return 0

        moves.sort(key=score_move, reverse=True)
        return moves
