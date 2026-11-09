# Betting Edge — Edge Terminal

Sports betting research dashboard hosted as a static GitHub Pages frontend.

## Current architecture
- Frontend: `index.html` (HTML/CSS/vanilla JavaScript)
- Backend URL configured in frontend: `https://betting-edge-api.onrender.com`
- Frontend expects `/api/v1/events`, `/api/v1/odds`, `/api/v1/events/{id}/props`, and `/api/v1/research/game`.
- The backend source/deployment has **not** been verified in this repository.

## Run locally
Serve the repository folder with any static file server, or open `index.html` in a browser. API requests require the external backend to be running and configured for CORS.

## What works in the frontend
- Sport, date, event and sportsbook selection
- Standard odds and on-demand player-prop requests
- News/injury/weather research request and display
- Market-implied probabilities and illustrative parlay combinations
- Bankroll and risk allocation controls

## Important limitations
- No independent probability model, backtesting or calibrated edge estimate has been verified.
- The parlay builder multiplies individual sportsbook-implied probabilities as an **independence-only illustration**. It does not model correlation, remove vig, or fetch an actual same-game-parlay quote.
- Market availability and freshness depend on the external API.
- Risk preferences, betting style and free-text preferences are not yet connected to a recommendation engine.
- Research status indicates available evidence, **not** predictive confidence.
- The interface has not been validated end-to-end against the deployed backend in this change.

## Next development steps
1. Confirm where the Render backend source lives and validate API endpoints, CORS, errors and rate limits.
2. Add browser-based smoke tests for date selection, odds caching, risk allocation and empty/error states.
3. Add historical data ingestion, model evaluation and calibration for one sport (suggested: NFL).
4. Only display a betting edge after validating independent probabilities; obtain actual sportsbook quotes for parlays.

Keep API keys and other secrets on the backend, never in GitHub Pages JavaScript.
