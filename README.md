# Conversational Fairness Intelligence Engine

Complete full-stack prototype with:

- FastAPI backend for dataset parsing, bias analysis, simulation, and strategy ranking
- React + Tailwind + Framer Motion conversational UI
- Logistic Regression model pipeline with feature importance explainability

## Folder Structure

```text
backend/
  requirements.txt
  app/
    main.py
    routes/
      upload.py
      analyze.py
      simulate.py
      strategy.py
    core/
      model.py
      bias.py
      simulation.py
      explain.py
      strategy.py
      state.py
    utils/
      parser.py
      preprocess.py
frontend/
  package.json
  index.html
  vite.config.js
  postcss.config.js
  tailwind.config.js
  src/
    main.jsx
    App.jsx
    api.js
    index.css
    components/
      MessageBubble.jsx
      TypingDots.jsx
      StrategyCard.jsx
```

## Backend Setup (FastAPI)

1. Create virtual environment (optional):
   - `python -m venv .venv`
   - `.\.venv\Scripts\activate` (PowerShell)
2. Install dependencies:
   - `python -m pip install -r backend/requirements.txt`
3. Run API server:
   - `uvicorn app.main:app --reload --port 8000`
   - Run this command inside `backend/`

Health check:
- `http://localhost:8000/health`

## Frontend Setup (React + Tailwind)

1. Install dependencies:
   - `cd frontend`
   - `npm install`
2. Start dev server:
   - `npm run dev`
3. Open:
   - `http://localhost:5173`

## Workflow

1. Upload CSV
2. System detects target column (last column), features, and candidate sensitive attributes
3. Model trains and computes:
   - Selection rates by sensitive group
   - Disparate Impact (DI)
4. Counterfactual simulation flips the sensitive attribute and checks prediction changes
5. Strategy engine generates and ranks:
   - Remove Sensitive Feature
   - Reweight Samples
   - Resample Dataset
6. User selects strategy and retrains model
7. Final explanation is returned:
   - What bias existed
   - Why it happened
   - What changed
   - Final improvement

## Notes

- Current session state is in-memory (`app/core/state.py`) for a single-user local prototype.
- SHAP is kept modular as optional extension point (`shap.enabled = false` response).
