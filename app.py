"""
app.py  –  Streamlit web UI for ChessAI
Run:  streamlit run app.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import chess
import chess.svg
import streamlit as st
from chess_ai.engine import ChessAI
from chess_ai.db_setup import build_opening_db, build_middlegame_db, build_endgame_db, OPENING_DB, MIDDLEGAME_DB, ENDGAME_DB

# ── Build databases on first run ──────────────────────────────────────────────
for db_path, builder in [
    (OPENING_DB, build_opening_db),
    (MIDDLEGAME_DB, build_middlegame_db),
    (ENDGAME_DB, build_endgame_db),
]:
    if not os.path.exists(db_path):
        builder()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Chess AI",
    page_icon="♟️",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Dark board-room feel */
  [data-testid="stAppViewContainer"] {
      background: #1a1a2e;
  }
  [data-testid="stSidebar"] {
      background: #16213e;
  }
  h1, h2, h3, .stMarkdown p, label {
      color: #e0e0e0 !important;
  }
  /* Move input box */
  .stTextInput > div > div > input {
      background: #0f3460;
      color: #e0e0e0;
      border: 1px solid #e94560;
      border-radius: 6px;
      font-size: 1.1rem;
  }
  /* Buttons */
  .stButton > button {
      background: #e94560;
      color: white;
      border: none;
      border-radius: 6px;
      font-weight: 600;
      transition: opacity .2s;
  }
  .stButton > button:hover { opacity: .85; }

  /* Info/status cards */
  .info-card {
      background: #0f3460;
      border-left: 3px solid #e94560;
      border-radius: 6px;
      padding: 10px 14px;
      margin: 6px 0;
      color: #d0d0d0;
      font-size: .9rem;
  }
  .badge {
      display: inline-block;
      padding: 2px 10px;
      border-radius: 20px;
      font-size: .8rem;
      font-weight: 700;
      margin-right: 6px;
  }
  .badge-attack  { background:#e94560; color:#fff; }
  .badge-defense { background:#4caf50; color:#fff; }
  .badge-balanced{ background:#ff9800; color:#fff; }
  .badge-opening { background:#9c27b0; color:#fff; }
  .badge-mid     { background:#2196f3; color:#fff; }
  .badge-endgame { background:#795548; color:#fff; }

  /* Move history list */
  .move-list {
      max-height: 220px;
      overflow-y: auto;
      background: #0f3460;
      border-radius: 6px;
      padding: 8px 12px;
      font-family: monospace;
      color: #d0d0d0;
      font-size: .85rem;
  }
  /* Chessboard SVG */
  .chess-board svg { border-radius: 8px; box-shadow: 0 4px 24px #0008; }
</style>
""", unsafe_allow_html=True)

# ── Session-state helpers ─────────────────────────────────────────────────────
def init_state(human_color=chess.WHITE, depth=4, time_limit=5.0):
    ai_color = not human_color
    st.session_state.board       = chess.Board()
    st.session_state.ai          = ChessAI(color=ai_color, max_depth=depth, time_limit=time_limit)
    st.session_state.human_color = human_color
    st.session_state.move_log    = []   # list of (move_number, side, san)
    st.session_state.error_msg   = ""
    st.session_state.last_info   = {}
    st.session_state.started     = True

if "started" not in st.session_state:
    init_state()

# ── Sidebar settings ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ♟️  Chess AI")
    st.markdown("---")

    play_as = st.radio("You play as", ["White ♙", "Black ♟"], index=0)
    human_color = chess.WHITE if play_as.startswith("W") else chess.BLACK

    depth = st.slider("AI search depth", 2, 6, 4,
                      help="Higher = stronger but slower. 4 is a good balance.")
    time_limit = st.slider("AI time per move (s)", 1.0, 15.0, 5.0, 0.5)

    st.markdown("---")
    if st.button("🆕  New Game", use_container_width=True):
        if "ai" in st.session_state:
            st.session_state.ai.close()
        init_state(human_color, depth, time_limit)
        st.rerun()

    st.markdown("---")
    st.markdown("""
**How to enter moves**

Type a move in the box below the board using standard chess notation:
- `e4` / `d5` (SAN)
- `e2e4` / `d7d5` (UCI)
- `Nf3` / `O-O` (castling)
""")

# ── Board rendering ───────────────────────────────────────────────────────────
board: chess.Board = st.session_state.board
ai: ChessAI        = st.session_state.ai
human_color        = st.session_state.human_color

def render_board(board, flip=False, last_move=None):
    svg = chess.svg.board(
        board,
        flipped=flip,
        lastmove=last_move,
        size=480,
        colors={
            "square light":        "#f0d9b5",
            "square dark":         "#b58863",
            "square light lastmove": "#cdd26a",
            "square dark lastmove":  "#aaa23a",
        }
    )
    return svg

flip = (human_color == chess.BLACK)
last_move = board.peek() if board.move_stack else None
svg = render_board(board, flip=flip, last_move=last_move)

st.markdown("### Board")
st.markdown(f'<div class="chess-board">{svg}</div>', unsafe_allow_html=True)

# ── Status bar ────────────────────────────────────────────────────────────────
info = st.session_state.last_info

col1, col2 = st.columns(2)
with col1:
    phase = info.get("phase", "—")
    phase_badge = {
        "opening":    '<span class="badge badge-opening">Opening</span>',
        "middlegame": '<span class="badge badge-mid">Middlegame</span>',
        "endgame":    '<span class="badge badge-endgame">Endgame</span>',
    }.get(phase, "")
    st.markdown(f"**Phase:** {phase_badge}", unsafe_allow_html=True)

with col2:
    posture = info.get("posture", "")
    posture_badge = {
        "ATTACK":   '<span class="badge badge-attack">⚔ Attack</span>',
        "DEFENSE":  '<span class="badge badge-defense">🛡 Defense</span>',
        "BALANCED": '<span class="badge badge-balanced">⚖ Balanced</span>',
    }.get(posture, "")
    if posture_badge:
        st.markdown(f"**Posture:** {posture_badge}", unsafe_allow_html=True)

# Opening / plan info
if info.get("opening"):
    eco, name, _, notes = info["opening"]
    st.markdown(f'<div class="info-card">📖 <b>{eco} – {name}</b><br><small>{notes}</small></div>',
                unsafe_allow_html=True)
if info.get("plan_title"):
    st.markdown(f'<div class="info-card">🗺 <b>Plan:</b> {info["plan_title"]}<br>'
                f'<small>{info["plan_description"]}</small></div>',
                unsafe_allow_html=True)
if info.get("endgame_principles"):
    st.markdown(f'<div class="info-card">♟ <b>Endgame:</b> {", ".join(info["endgame_principles"])}</div>',
                unsafe_allow_html=True)

# Search stats
if info.get("score_cp") is not None:
    score_display = f"{info['score_cp']:+.0f} cp"
    depth_display = f"depth {info.get('depth_reached', '?')}"
    nodes_display = f"{info.get('nodes', 0):,} nodes"
    st.markdown(
        f'<div class="info-card">🔍 {score_display} &nbsp;|&nbsp; {depth_display} &nbsp;|&nbsp; {nodes_display}</div>',
        unsafe_allow_html=True
    )

st.markdown("---")

# ── Game-over check ───────────────────────────────────────────────────────────
if board.is_game_over():
    result = board.result()
    reason = ""
    if board.is_checkmate():    reason = "Checkmate!"
    elif board.is_stalemate():  reason = "Stalemate – draw."
    elif board.is_insufficient_material(): reason = "Insufficient material – draw."
    elif board.can_claim_fifty_moves():    reason = "Fifty-move rule – draw."
    else:                       reason = "Draw."

    if result == "1-0":
        winner = "White wins" if human_color == chess.WHITE else "AI wins"
    elif result == "0-1":
        winner = "Black wins" if human_color == chess.BLACK else "AI wins"
    else:
        winner = "Draw"

    st.success(f"🏁 Game over – **{winner}**  ({reason}  Result: {result})")

    if st.button("Play Again"):
        if "ai" in st.session_state:
            st.session_state.ai.close()
        init_state(human_color, depth, time_limit)
        st.rerun()

else:
    whose_turn = "Your turn" if board.turn == human_color else "AI is thinking…"
    st.markdown(f"**{whose_turn}**")

    # ── AI move (runs automatically when it's the AI's turn) ─────────────────
    if board.turn != human_color:
        with st.spinner("AI thinking…"):
            move = ai.get_move(board)
            san  = board.san(move)
            board.push(move)
            ai.note_move_played(move)
            st.session_state.last_info = ai.last_info
            mn = board.fullmove_number if board.turn == chess.WHITE else board.fullmove_number
            side = "Black" if human_color == chess.WHITE else "White"
            st.session_state.move_log.append((mn, f"AI ({side})", san))
        st.rerun()

    # ── Human move input ──────────────────────────────────────────────────────
    else:
        with st.form("move_form", clear_on_submit=True):
            user_in = st.text_input("Your move (e.g. e4, Nf3, O-O, e2e4):",
                                    placeholder="Type move here…")
            submitted = st.form_submit_button("Make Move ▶")

        if submitted and user_in.strip():
            raw = user_in.strip()
            move = None
            # Try SAN first, then UCI
            try:
                move = board.parse_san(raw)
            except ValueError:
                try:
                    candidate = chess.Move.from_uci(raw)
                    move = candidate if candidate in board.legal_moves else None
                except ValueError:
                    pass

            if move is None:
                st.session_state.error_msg = f"❌ '{raw}' is not a legal move. Try again."
            else:
                mn   = board.fullmove_number
                side = "White" if human_color == chess.WHITE else "Black"
                san  = board.san(move)
                board.push(move)
                ai.note_move_played(move)
                st.session_state.move_log.append((mn, f"You ({side})", san))
                st.session_state.error_msg = ""
            st.rerun()

        if st.session_state.error_msg:
            st.error(st.session_state.error_msg)

# ── Move history ──────────────────────────────────────────────────────────────
if st.session_state.move_log:
    st.markdown("### Move History")
    lines = []
    for mn, side, san in st.session_state.move_log:
        lines.append(f"{mn}. {side}: {san}")
    st.markdown(
        '<div class="move-list">' + "<br>".join(lines) + "</div>",
        unsafe_allow_html=True
    )
