# ♟️ Chess AI — Web UI

A chess engine with an opening book, middlegame plans, and endgame principles,
wrapped in a Streamlit web UI. Play it locally or deploy to Render for free.

---

## Project layout

```
chess_project/
├── app.py                  ← the web UI (run this)
├── requirements.txt
├── render.yaml             ← Render deployment config
├── Procfile                ← start command for Render
├── .gitignore
├── README.md
└── chess_ai/
    ├── __init__.py
    ├── db_setup.py         ← builds the 3 SQLite databases
    ├── opening_book.py
    ├── middlegame_plans.py
    ├── endgame_principles.py
    ├── evaluation.py
    ├── search.py
    ├── engine.py
    └── data/               ← auto-created SQLite .db files live here
```

---

## Run locally (step by step)

**Step 1 — make sure Python 3.9+ is installed**
```bash
python --version
```
If not installed, download from https://python.org

**Step 2 — install dependencies**
```bash
pip install -r requirements.txt
```

**Step 3 — launch the app**
```bash
streamlit run app.py
```

Your browser will open automatically at `http://localhost:8501`.
The databases are built automatically on first launch — no extra step needed.

---

## Deploy to Render (free tier)

**Step 1 — push your code to GitHub**

1. Create a new repo on https://github.com (click "New repository")
2. In your project folder, run:
```bash
git init
git add .
git commit -m "Initial chess AI commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

**Step 2 — create a Render web service**

1. Go to https://render.com and sign up (free)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account and select your repo
4. Render will auto-detect `render.yaml` — just click **"Create Web Service"**
5. Wait 2–3 minutes for the build to finish

Your app will be live at `https://chess-ai.onrender.com` (or similar URL).

> **Note:** On Render's free tier the app "sleeps" after 15 minutes of
> inactivity. The first visit after sleep takes ~30 seconds to wake up.
> This is normal and free — upgrade to a paid plan to keep it always-on.

---

## How to play

- **Choose a side** in the left sidebar (White or Black)
- **Adjust AI strength** with the depth and time sliders
- **Type your move** in the text box below the board
  - Standard notation: `e4`, `Nf3`, `O-O` (castling), `exd5`
  - Or UCI notation: `e2e4`, `g1f3`, `e1g1`
- The AI moves automatically after you

---

## What the AI does

1. **Opening phase** — plays book moves from its opening database (15 named lines)
2. **Middlegame** — runs alpha-beta search with evaluation weights biased toward
   the strategic plan matching your opening (e.g. kingside attack for King's Indian)
3. **Endgame** — adjusts weights for endgame technique (king activity, passed pawns, etc.)
4. **Posture** — switches between ⚔ Attack, 🛡 Defense, ⚖ Balanced based on how
   much it's winning or losing
