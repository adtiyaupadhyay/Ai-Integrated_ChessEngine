"""
play.py
========
Minimal command-line demo: play a game against the ChessAI engine.

Usage:
    python play.py                  # you play White, AI plays Black
    python play.py --black          # you play Black, AI plays White
    python play.py --depth 5 --time 8
"""
import argparse
import chess

from chess_ai.engine import ChessAI



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--black", action="store_true", help="play as Black (AI plays White)")
    parser.add_argument("--depth", type=int, default=4, help="base search depth (default 4)")
    parser.add_argument("--time", type=float, default=5.0, help="seconds the AI may think per move")
    args = parser.parse_args()

    human_color = chess.BLACK if args.black else chess.WHITE
    ai_color = not human_color

    board = chess.Board()
    ai = ChessAI(color=ai_color, max_depth=args.depth, time_limit=args.time)

    print(board)
    print()

    while not board.is_game_over():
        if board.turn == human_color:
            move = None
            while move is None:
                user_in = input("Your move (SAN or UCI, e.g. e4 / e2e4): ").strip()
                try:
                    move = board.parse_san(user_in)
                except ValueError:
                    try:
                        candidate = chess.Move.from_uci(user_in)
                        move = candidate if candidate in board.legal_moves else None
                        if move is None:
                            print("Illegal move, try again.")
                    except ValueError:
                        print("Could not parse that move, try again.")
            board.push(move)
            ai.note_move_played(move)
        else:
            print("AI is thinking...")
            move = ai.get_move(board)
            san = board.san(move)
            board.push(move)
            ai.note_move_played(move)
            info = ai.last_info
            print(f"AI plays: {san}  ({move.uci()})")
            print(f"  source={info.get('source')} phase={info.get('phase')} "
                  f"posture={info.get('posture')} score_cp={info.get('score_cp')} "
                  f"depth={info.get('depth_reached')} nodes={info.get('nodes')}")
            if info.get("opening"):
                print(f"  opening: {info['opening'][1]} ({info['opening'][0]})")
            if info.get("plan_title"):
                print(f"  plan: {info['plan_title']} -- {info['plan_description']}")
            if info.get("endgame_principles"):
                print(f"  endgame ideas: {', '.join(info['endgame_principles'])}")

        print()
        print(board)
        print()

    print("Game over:", board.result())
    ai.close()


if __name__ == "__main__":
    main()
