"""
evaluation.py
==============
Static evaluation function for the engine.

Combines:
  - material balance
  - classic piece-square tables (separate king table for the endgame)
  - mobility
  - king safety (pawn shield + open files near the king)
  - pawn structure (doubled / isolated / passed pawns)
  - centre control, king activity, kingside pawn storms, per-piece activity

All terms are computed once and combined through a *weights* dict, so the
opening/middlegame/endgame databases (and the engine's attack/defence
posture) can bias the evaluation toward whatever matters for the position
at hand without duplicating the whole function per opening.
"""

import chess

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

# Piece-square tables, White's perspective, index 0 = a1 ... 63 = h8.
PAWN_TABLE = [
    0, 0, 0, 0, 0, 0, 0, 0,
    5, 10, 10, -20, -20, 10, 10, 5,
    5, -5, -10, 0, 0, -10, -5, 5,
    0, 0, 0, 20, 20, 0, 0, 0,
    5, 5, 10, 25, 25, 10, 5, 5,
    10, 10, 20, 30, 30, 20, 10, 10,
    50, 50, 50, 50, 50, 50, 50, 50,
    0, 0, 0, 0, 0, 0, 0, 0,
]
KNIGHT_TABLE = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20, 0, 5, 5, 0, -20, -40,
    -30, 5, 10, 15, 15, 10, 5, -30,
    -30, 0, 15, 20, 20, 15, 0, -30,
    -30, 5, 15, 20, 20, 15, 5, -30,
    -30, 0, 10, 15, 15, 10, 0, -30,
    -40, -20, 0, 0, 0, 0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]
BISHOP_TABLE = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10, 5, 0, 0, 0, 0, 5, -10,
    -10, 10, 10, 10, 10, 10, 10, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 5, 10, 10, 5, 0, -10,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]
ROOK_TABLE = [
    0, 0, 0, 5, 5, 0, 0, 0,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    5, 10, 10, 10, 10, 10, 10, 5,
    0, 0, 0, 0, 0, 0, 0, 0,
]
QUEEN_TABLE = [
    -20, -10, -10, -5, -5, -10, -10, -20,
    -10, 0, 5, 0, 0, 0, 0, -10,
    -10, 5, 5, 5, 5, 5, 0, -10,
    0, 0, 5, 5, 5, 5, 0, -5,
    -5, 0, 5, 5, 5, 5, 0, -5,
    -10, 0, 5, 5, 5, 5, 0, -10,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -20, -10, -10, -5, -5, -10, -10, -20,
]
KING_MIDGAME_TABLE = [
    20, 30, 10, 0, 0, 10, 30, 20,
    20, 20, 0, 0, 0, 0, 20, 20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
]
KING_ENDGAME_TABLE = [
    -50, -30, -30, -30, -30, -30, -30, -50,
    -30, -30, 0, 0, 0, 0, -30, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 30, 40, 40, 30, -10, -30,
    -30, -10, 20, 30, 30, 20, -10, -30,
    -30, -20, -10, 0, 0, -10, -20, -30,
    -50, -40, -30, -20, -20, -30, -40, -50,
]

PST = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
}

# 2N+2B+2R+1Q per side at the start of the game, used as a phase reference.
STARTING_NON_PAWN_MATERIAL = 2 * (2 * 320 + 2 * 330 + 2 * 500 + 900)

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


def game_phase(board: chess.Board) -> str:
    """Classify the position as 'opening', 'middlegame' or 'endgame' using
    move count plus remaining non-pawn material -- a cheap, standard proxy."""
    non_pawn_material = 0
    for color in (chess.WHITE, chess.BLACK):
        for piece_type in (chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
            non_pawn_material += len(board.pieces(piece_type, color)) * PIECE_VALUES[piece_type]

    if board.fullmove_number <= 10 and non_pawn_material >= 0.85 * STARTING_NON_PAWN_MATERIAL:
        return "opening"
    if non_pawn_material <= 0.35 * STARTING_NON_PAWN_MATERIAL:
        return "endgame"
    return "middlegame"


def _material_and_pst(board: chess.Board, endgame: bool):
    material = 0
    pst_score = 0
    for square, piece in board.piece_map().items():
        sign = 1 if piece.color == chess.WHITE else -1
        material += sign * PIECE_VALUES[piece.piece_type]

        idx = square if piece.color == chess.WHITE else chess.square_mirror(square)
        if piece.piece_type == chess.KING:
            table = KING_ENDGAME_TABLE if endgame else KING_MIDGAME_TABLE
        else:
            table = PST[piece.piece_type]
        pst_score += sign * table[idx]
    return material, pst_score


def _mobility(board: chess.Board) -> int:
    """Legal-move-count difference, computed for both sides regardless of
    whose turn it actually is (temporarily flips board.turn, then restores it)."""
    original_turn = board.turn
    board.turn = chess.WHITE
    white_count = board.legal_moves.count()
    board.turn = chess.BLACK
    black_count = board.legal_moves.count()
    board.turn = original_turn
    return white_count - black_count


def _pawn_structure(board: chess.Board):
    """Returns (structure_score, passed_pawn_score) as two separate terms
    so the caller can weight passed pawns independently (important for
    endgame technique)."""
    structure_score = 0
    passed_score = 0
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color == chess.WHITE else -1
        pawns = board.pieces(chess.PAWN, color)
        files = [chess.square_file(sq) for sq in pawns]
        for f in set(files):
            count = files.count(f)
            if count > 1:
                structure_score -= sign * 12 * (count - 1)
        for sq in pawns:
            f = chess.square_file(sq)
            r = chess.square_rank(sq)
            isolated = not any(nf in files for nf in (f - 1, f + 1))
            if isolated:
                structure_score -= sign * 10

            enemy_pawns = board.pieces(chess.PAWN, not color)
            blocking_files = (f - 1, f, f + 1)
            is_passed = True
            for esq in enemy_pawns:
                ef, er = chess.square_file(esq), chess.square_rank(esq)
                if ef in blocking_files:
                    if (color == chess.WHITE and er > r) or (color == chess.BLACK and er < r):
                        is_passed = False
                        break
            if is_passed:
                advance = r if color == chess.WHITE else 7 - r
                passed_score += sign * (10 + 4 * advance)
    return structure_score, passed_score


def _king_safety(board: chess.Board) -> int:
    score = 0
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color == chess.WHITE else -1
        king_sq = board.king(color)
        if king_sq is None:
            continue
        king_file = chess.square_file(king_sq)
        shield_files = [king_file - 1, king_file, king_file + 1]

        own_pawns = board.pieces(chess.PAWN, color)
        shield = sum(1 for sq in own_pawns if chess.square_file(sq) in shield_files)
        score += sign * shield * 6

        for f in shield_files:
            if f < 0 or f > 7:
                continue
            has_own_pawn = any(chess.square_file(sq) == f for sq in own_pawns)
            if not has_own_pawn:
                score -= sign * 8
    return score


def _center_control(board: chess.Board) -> int:
    score = 0
    for sq in (chess.D4, chess.D5, chess.E4, chess.E5):
        score += (len(board.attackers(chess.WHITE, sq)) - len(board.attackers(chess.BLACK, sq))) * 4
    return score


def _kingside_pawn_storm(board: chess.Board) -> int:
    score = 0
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color == chess.WHITE else -1
        for sq in board.pieces(chess.PAWN, color):
            f, r = chess.square_file(sq), chess.square_rank(sq)
            if f in (5, 6, 7):  # f, g, h files
                advance = (r - 1) if color == chess.WHITE else (6 - r)
                if advance > 0:
                    score += sign * advance * 3
    return score


def _king_activity(board: chess.Board) -> int:
    score = 0
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color == chess.WHITE else -1
        ksq = board.king(color)
        if ksq is None:
            continue
        dist = abs(chess.square_file(ksq) - 3.5) + abs(chess.square_rank(ksq) - 3.5)
        score -= sign * dist * 2
    return score


def _piece_specific_activity(board: chess.Board):
    activity = {"rook_activity": 0, "bishop_activity": 0, "knight_activity": 0, "queen_activity": 0}
    for color in (chess.WHITE, chess.BLACK):
        sign = 1 if color == chess.WHITE else -1
        for sq in board.pieces(chess.ROOK, color):
            activity["rook_activity"] += sign * len(board.attacks(sq))
        for sq in board.pieces(chess.BISHOP, color):
            activity["bishop_activity"] += sign * len(board.attacks(sq))
        for sq in board.pieces(chess.KNIGHT, color):
            activity["knight_activity"] += sign * len(board.attacks(sq))
        for sq in board.pieces(chess.QUEEN, color):
            activity["queen_activity"] += sign * len(board.attacks(sq))
    return activity


def evaluate(board: chess.Board, weights: dict = None) -> float:
    """Static evaluation in centipawns, from White's perspective (positive
    favours White). `weights` overrides DEFAULT_WEIGHTS for specific terms,
    supplied by the opening/middlegame/endgame databases and by the
    engine's attack/defence posture."""
    if board.is_checkmate():
        return -999999 if board.turn == chess.WHITE else 999999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)

    phase = game_phase(board)
    endgame = phase == "endgame"

    material, pst_score = _material_and_pst(board, endgame)
    mobility = _mobility(board)
    structure_score, passed_score = _pawn_structure(board)
    king_safety = _king_safety(board)
    center = _center_control(board)
    storm = _kingside_pawn_storm(board)
    king_act = _king_activity(board)
    activity = _piece_specific_activity(board)

    score = 0.0
    score += w["material"] * material
    score += w["piece_activity"] * (pst_score + 0.5 * mobility)
    score += w["pawn_structure"] * structure_score
    score += w["passed_pawn"] * passed_score
    score += w["king_safety"] * king_safety
    score += w["center_control"] * center
    score += w["pawn_storm_kingside"] * 0.5 * storm
    score += w["king_activity"] * king_act
    score += w["rook_activity"] * 0.3 * activity["rook_activity"]
    score += w["bishop_activity"] * 0.3 * activity["bishop_activity"]
    score += w["knight_activity"] * 0.3 * activity["knight_activity"]
    score += w["queen_activity"] * 0.2 * activity["queen_activity"]

    return score
