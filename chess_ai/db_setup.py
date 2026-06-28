"""
db_setup.py
============
Creates and seeds three separate SQLite databases used by the engine:

1. opening.db     -> general chess principles + a small named-opening book
2. middlegame.db  -> middlegame plans, linked to openings via `plan_tag`
3. endgame.db     -> endgame principles, linked to material signatures

Run this file once (or after editing the data below) to (re)build the DBs:
    python -m chess_ai.db_setup

These are deliberately small "seed" datasets that show the structure end
to end. They are easy to extend:
  - add rows to GENERAL_PRINCIPLES / OPENING_LINES for more book moves
  - add rows to MIDDLEGAME_PLANS for more strategic plans
  - add rows to ENDGAME_PRINCIPLES for more endgame technique
You can also write a separate loader that imports a PGN database or an
ECO file and INSERTs many more rows into the same tables.
"""

import sqlite3
import os
import json

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

OPENING_DB = os.path.join(DATA_DIR, "opening.db")
MIDDLEGAME_DB = os.path.join(DATA_DIR, "middlegame.db")
ENDGAME_DB = os.path.join(DATA_DIR, "endgame.db")


# ---------------------------------------------------------------------------
# 1. OPENING DATABASE
# ---------------------------------------------------------------------------

GENERAL_PRINCIPLES = [
    ("development", "Develop knights and bishops before moving the same piece twice."),
    ("development", "Knights are usually best developed toward the centre before bishops."),
    ("center", "Fight for control of the centre (d4/d5/e4/e5) with pawns and pieces."),
    ("center", "Occupying the centre with pawns is good, but only if it can be supported."),
    ("king_safety", "Castle early, ideally before move 10, to get the king to safety and connect rooks."),
    ("king_safety", "Avoid unnecessary pawn moves in front of your own king once castled."),
    ("queen", "Do not bring the queen out early where it can be harassed and lose tempo."),
    ("rooks", "Place rooks on open or half-open files; doubling rooks increases pressure."),
    ("pawns", "Avoid weakening pawn moves without a concrete reason."),
    ("pawns", "Isolated and backward pawns are long-term weaknesses; avoid creating them unnecessarily."),
    ("tempo", "Every opening move should develop a piece, contest the centre, or improve king safety."),
    ("material", "Do not grab material at the cost of huge development lag unless the refutation is concrete."),
    ("space", "Convert a space advantage by restricting the opponent's piece mobility."),
    ("exchange", "Trade pieces when ahead in material or when it relieves a cramped position."),
    ("initiative", "A tempo gained in the opening is often worth more than a small pawn weakness."),
    ("general", "Look for tactics (forks, pins, skewers, discovered attacks) at every move."),
    ("general", "A bad plan executed energetically is often better than no plan, but a good plan is best."),
]

# Each line: (eco, name, moves_uci, plan_tag, notes, popularity)
OPENING_LINES = [
    ("C50", "Italian Game: Giuoco Piano",
     "e2e4 e7e5 g1f3 b8c6 f1c4 f8c5 c2c3 g8f6 d2d3",
     "italian_giuoco",
     "Classical development, fight for the centre, prepare d4 or castle and look for kingside chances.",
     5),

    ("C60", "Ruy Lopez: Closed Defence",
     "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1 f8e7 f1e1 b7b5 a4b3 d7d6",
     "ruy_lopez_closed",
     "Slow manoeuvring battle; White aims for d4 and central space, Black counters with ...b5/...c5.",
     5),

    ("B90", "Sicilian Defence: Najdorf",
     "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 a7a6",
     "sicilian_najdorf",
     "Black accepts a flexible structure, plans ...e5 or ...b5, fights for the centre with pieces.",
     5),

    ("B70", "Sicilian Defence: Dragon",
     "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 g7g6",
     "sicilian_dragon",
     "Black fianchettoes to g7, aims for ...d5 or queenside counterplay; sharp opposite-side races.",
     4),

    ("C00", "French Defence: Classical",
     "e2e4 e7e6 d2d4 d7d5 b1c3 g8f6 c1g5 f8e7",
     "french_classical",
     "Black accepts a solid, slightly passive structure, targets d4 and queenside expansion with ...c5.",
     4),

    ("B18", "Caro-Kann Defence: Classical",
     "e2e4 c7c6 d2d4 d7d5 b1c3 d5e4 c3e4",
     "caro_kann",
     "Solid pawn structure, avoids the French's bad-bishop problem, slower but resilient game.",
     3),

    ("B07", "Pirc Defence",
     "e2e4 d7d6 d2d4 g8f6 b1c3 g7g6",
     "pirc_kid_setup",
     "Hypermodern setup; Black lets White claim the centre then strikes back with ...e5 or ...c5.",
     3),

    ("E60", "King's Indian Defence",
     "d2d4 g8f6 c2c4 g7g6 b1c3 f8g7 e2e4 d7d6",
     "kings_indian",
     "Black fianchettoes and prepares ...e5/...c5 counterstrikes, often castling into a kingside attack.",
     4),

    ("E20", "Nimzo-Indian Defence",
     "d2d4 g8f6 c2c4 e7e6 b1c3 f8b4",
     "nimzo_indian",
     "Black pins the knight to disrupt White's centre and fight for e4.",
     4),

    ("D30", "Queen's Gambit Declined",
     "d2d4 d7d5 c2c4 e7e6 b1c3 g8f6 c1g5 f8e7",
     "qgd",
     "Solid classical structure; Black aims to free the position with ...c5 or ...dxc4 then ...c5.",
     4),

    ("D20", "Queen's Gambit Accepted",
     "d2d4 d7d5 c2c4 d5c4 g1f3 g8f6 e2e3",
     "qga",
     "Black grabs the c4 pawn temporarily and plays for fast development or to hold the extra pawn.",
     3),

    ("A10", "English Opening: Reversed Sicilian",
     "c2c4 e7e5 b1c3 g8f6 g1f3 b8c6",
     "english_reversed_sicilian",
     "Flexible flank opening, often transposes into reversed-Sicilian structures.",
     3),

    ("B01", "Scandinavian Defence",
     "e2e4 d7d5 e4d5 d8d5 b1c3 d5a5",
     "scandinavian",
     "Black trades the centre early for quick development; the queen must dodge tempo-loss tricks.",
     2),

    ("D02", "London System",
     "d2d4 d7d5 g1f3 g8f6 c1f4",
     "london_system",
     "Simple, solid setup for White: bishop out before e3, then steady piece play.",
     4),

    ("C30", "King's Gambit",
     "e2e4 e7e5 f2f4",
     "kings_gambit",
     "Romantic, sharp gambit; White trades a pawn for rapid development and open lines.",
     2),
]


def build_opening_db():
    if os.path.exists(OPENING_DB):
        os.remove(OPENING_DB)
    conn = sqlite3.connect(OPENING_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE general_principles (
            id INTEGER PRIMARY KEY,
            category TEXT,
            principle TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE openings (
            id INTEGER PRIMARY KEY,
            eco TEXT,
            name TEXT,
            moves_uci TEXT,
            plan_tag TEXT,
            notes TEXT,
            popularity INTEGER DEFAULT 1
        )
    """)
    cur.executemany(
        "INSERT INTO general_principles (category, principle) VALUES (?, ?)",
        GENERAL_PRINCIPLES,
    )
    cur.executemany(
        "INSERT INTO openings (eco, name, moves_uci, plan_tag, notes, popularity) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        OPENING_LINES,
    )
    conn.commit()
    conn.close()
    print(f"Built {OPENING_DB}: {len(OPENING_LINES)} lines, {len(GENERAL_PRINCIPLES)} principles.")


# ---------------------------------------------------------------------------
# 2. MIDDLEGAME DATABASE
# ---------------------------------------------------------------------------

# Each: (plan_tag, title, description, weight-adjustment dict)
MIDDLEGAME_PLANS = [
    ("italian_giuoco", "Centre break with d4",
     "Aim for d4 at the right moment to open the centre while pieces are well placed; "
     "if Black plays solidly, regroup with Re1/Bb3/Nbd2 and probe on the kingside.",
     {"center_control": 1.2, "piece_activity": 1.1, "king_safety": 1.1}),

    ("ruy_lopez_closed", "Queenside space vs central break",
     "White slowly builds with c3/d4/Nbd2-f1-g3 and looks for a kingside attack once Black's "
     "queenside expansion is contained; Black counters with a timely ...c5 or ...d5.",
     {"space": 1.2, "king_safety": 1.1, "pawn_structure": 1.05}),

    ("sicilian_najdorf", "Queenside expansion / English Attack",
     "Black plays for ...b5-b4 and ...d5 breaks; White often castles queenside and storms the "
     "kingside with f3/g4/h4. Whoever attacks faster usually wins.",
     {"king_safety": 0.9, "piece_activity": 1.25, "pawn_storm_kingside": 1.3}),

    ("sicilian_dragon", "Opposite-side attacking race",
     "White typically castles queenside and pushes h4-h5 against the fianchetto; Black counters "
     "with ...a5/...b5 and a rook lift. Speed matters more than safety.",
     {"king_safety": 0.85, "pawn_storm_kingside": 1.3, "piece_activity": 1.2}),

    ("french_classical", "Pressure on d4, queenside breaks",
     "Black targets d4 and plays ...c5 breaks; White can use the extra central space for a "
     "kingside initiative or restrict Black's pieces with e5/f4.",
     {"center_control": 1.15, "space": 1.1}),

    ("caro_kann", "Solid manoeuvring, minority attack",
     "Both sides manoeuvre to good squares; White often expands with f4/Ne5 or queenside play, "
     "Black looks for ...c5 or ...f6 breaks.",
     {"pawn_structure": 1.1, "piece_activity": 1.05}),

    ("pirc_kid_setup", "Central space vs hypermodern strike",
     "White holds the centre with e4/d4/f3; Black times ...e5 or ...c5 once pieces are ready.",
     {"center_control": 1.15, "king_safety": 1.05}),

    ("kings_indian", "Kingside pawn storm vs queenside play",
     "Classic opposite-wings battle: White expands on the queenside while Black storms the "
     "kingside with ...f5-f4 and piece play around g4/h3.",
     {"pawn_storm_kingside": 1.3, "king_safety": 0.95, "piece_activity": 1.2}),

    ("nimzo_indian", "Bishop pair vs doubled pawns",
     "If White accepts doubled c-pawns, Black plays against them with ...b6/...Ba6; otherwise "
     "the game is more balanced and positional.",
     {"pawn_structure": 1.2, "piece_activity": 1.05}),

    ("qgd", "Minority attack / central break",
     "White can launch a queenside minority attack, or Black frees the game with the thematic "
     "...c5 break once development is complete.",
     {"pawn_structure": 1.15, "space": 1.05}),

    ("qga", "Quick development for the pawn",
     "Black returns or holds the extra pawn while developing quickly; White relies on faster "
     "piece activity and central control to compensate.",
     {"piece_activity": 1.2, "center_control": 1.1}),

    ("english_reversed_sicilian", "Fight for d5/d4",
     "Flexible manoeuvring battle for the key central squares, often mirroring reversed-Sicilian "
     "structures with an extra tempo.",
     {"center_control": 1.1, "space": 1.05}),

    ("scandinavian", "Fast development against an exposed queen",
     "White develops with tempo against Black's queen; Black completes development quickly and "
     "challenges the centre with ...c6/...e6.",
     {"piece_activity": 1.15}),

    ("london_system", "Steady piece play, c3/Qb3 ideas",
     "White builds a solid wall with Bf4/e3/Nbd2/Bd3 and looks for slow pressure once development "
     "is finished.",
     {"pawn_structure": 1.1, "king_safety": 1.05}),

    ("kings_gambit", "Open f-file attack",
     "White trades structure for time, aiming to use the open f-file and quick piece play before "
     "Black finishes development.",
     {"piece_activity": 1.3, "king_safety": 0.85}),
]


def build_middlegame_db():
    if os.path.exists(MIDDLEGAME_DB):
        os.remove(MIDDLEGAME_DB)
    conn = sqlite3.connect(MIDDLEGAME_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE plans (
            id INTEGER PRIMARY KEY,
            plan_tag TEXT,
            title TEXT,
            description TEXT,
            weights_json TEXT
        )
    """)
    cur.executemany(
        "INSERT INTO plans (plan_tag, title, description, weights_json) VALUES (?, ?, ?, ?)",
        [(tag, title, desc, json.dumps(w)) for tag, title, desc, w in MIDDLEGAME_PLANS],
    )
    conn.commit()
    conn.close()
    print(f"Built {MIDDLEGAME_DB}: {len(MIDDLEGAME_PLANS)} plans.")


# ---------------------------------------------------------------------------
# 3. ENDGAME DATABASE
# ---------------------------------------------------------------------------

# Each: (material_signature, title, description, depth_bonus, weights dict)
ENDGAME_PRINCIPLES = [
    ("KPK", "King and pawn vs king",
     "Use the rule of the square and opposition; the defending king must reach the queening "
     "square or get in front of the pawn; the attacker's king should support the pawn.",
     4, {"king_activity": 1.3, "passed_pawn": 1.4}),

    ("KRK", "Rook vs lone king",
     "Drive the enemy king to the edge using the rook to cut off ranks/files and your king to "
     "shoulder it toward a corner, then deliver mate.",
     3, {"king_activity": 1.2, "rook_activity": 1.3}),

    ("rook_endgame", "Rook endgames in general",
     "Activate the rook behind a passed pawn, keep it active rather than passive, and remember "
     "the Lucena (winning) and Philidor (drawing) positions for rook + pawn vs rook.",
     2, {"rook_activity": 1.3, "passed_pawn": 1.2}),

    ("KBNK", "King, bishop and knight vs king",
     "Force the lone king into the corner matching the bishop's colour, using king and knight "
     "together while the bishop controls key squares; precise technique required.",
     5, {"king_activity": 1.2}),

    ("opposite_bishops", "Opposite-coloured bishop endgames",
     "Bishops on opposite colours cannot blockade each other's passed pawns; piece activity and "
     "king position matter more than raw material.",
     2, {"bishop_activity": 1.2, "passed_pawn": 1.2}),

    ("same_bishops", "Same-coloured bishop endgames",
     "The bishop pair on the same colour can fully blockade enemy pawns; the more active bishop "
     "usually carries the advantage.",
     2, {"bishop_activity": 1.2}),

    ("queen_endgame", "Queen endgames",
     "Centralise the queen, watch for perpetual check / stalemate tricks, and remember king "
     "safety still matters with few pieces left.",
     2, {"king_safety": 1.1, "queen_activity": 1.2}),

    ("knight_endgame", "Knight endgames",
     "Knights are poor at stopping passed rook pawns; centralise the knight and aim to create a "
     "second passed pawn or trade into a won pawn endgame.",
     2, {"knight_activity": 1.15, "passed_pawn": 1.25}),

    ("pawn_endgame", "Pure pawn endgames",
     "King activity and the opposition are critical; calculate pawn races precisely and look for "
     "breakthrough sacrifices to create a passed pawn.",
     5, {"king_activity": 1.4, "passed_pawn": 1.4}),

    ("general_endgame", "General endgame principles",
     "Activate the king, push passed pawns, keep rooks active and behind passed pawns, restrict "
     "the opponent's king, and trade pieces (not pawns) when ahead in material.",
     2, {"king_activity": 1.2, "passed_pawn": 1.15}),
]


def build_endgame_db():
    if os.path.exists(ENDGAME_DB):
        os.remove(ENDGAME_DB)
    conn = sqlite3.connect(ENDGAME_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE endgame_principles (
            id INTEGER PRIMARY KEY,
            material_signature TEXT,
            title TEXT,
            description TEXT,
            depth_bonus INTEGER,
            weights_json TEXT
        )
    """)
    cur.executemany(
        "INSERT INTO endgame_principles "
        "(material_signature, title, description, depth_bonus, weights_json) VALUES (?, ?, ?, ?, ?)",
        [(sig, title, desc, bonus, json.dumps(w)) for sig, title, desc, bonus, w in ENDGAME_PRINCIPLES],
    )
    conn.commit()
    conn.close()
    print(f"Built {ENDGAME_DB}: {len(ENDGAME_PRINCIPLES)} endgame principles.")


if __name__ == "__main__":
    build_opening_db()
    build_middlegame_db()
    build_endgame_db()
