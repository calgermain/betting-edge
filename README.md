# Edge Terminal — Sports Betting Research Prototype

A self-contained frontend prototype based on the supplied Sports Betting Research & Parlay Analysis specification.

## Run
Open `index.html` directly in a browser, or serve the folder with any static web server.

For GitHub Pages:
1. Create a GitHub repository.
2. Upload `index.html`.
3. Enable GitHub Pages from the repository's Pages settings.
4. The interface is static and needs no backend for the mock-data prototype.

## Architecture
The prototype keeps the major layers conceptually separate:
- UI / dashboard
- Betting calculations
- Probability calculations
- Correlation/parlay construction
- Research/data layer (currently mock data)
- Sportsbook selection (currently mock data)

## Next API integration
Replace the `baseBets` mock dataset and market-overview fields with a backend/data service. The browser UI should call a normalized internal API rather than calling individual sportsbook APIs directly.

Recommended production architecture:
Browser UI -> application API -> normalized odds/injury/weather/news adapters -> model/calculation services.

Do not put sportsbook API secrets in client-side JavaScript.
