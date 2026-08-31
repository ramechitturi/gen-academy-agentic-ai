# Stock Analysis Chatbot UI

A web-based interface for the multi-agent stock analysis system with human approval workflow.

## Features

- **Live Stock Analysis**: Enter a ticker symbol to fetch price, profile, and news
- **AI-Powered Insights**: LLM summarizes the data and recommends approve/review
- **Policy Compliance Checking**: RAG retrieves relevant compliance policies and checks violations
- **Human Approval**: Two buttons to approve or reject the LLM's recommendation
- **Decision History**: View all past analyses and decisions
- **SQLite Database**: Stores all analyses and decisions for audit trail

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Backend Server

In one terminal, run the FastAPI backend:

```bash
python3 backend.py
```

The API will be available at `http://localhost:8000`.

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

### 3. Open the Frontend

In your browser, open:

```
file:///Users/ramechitturi/coding-projects/learning/mcp-agent-project/index.html
```

Or run a simple HTTP server from the project directory:

```bash
python3 -m http.server 8080
```

Then open `http://localhost:8080/index.html`

## Usage

### Basic Workflow

1. **Enter a ticker**: Type a stock symbol (e.g., `AAPL`, `MSFT`, `TSLA`)
2. **Click Analyze**: The system will:
   - Fetch real stock price from yfinance
   - Get company profile and news (Alpha Vantage or mock)
   - Run the analyst agent (LLM summary)
   - Run compliance agent (RAG retrieval + policy check)
   - Run decision agent (approve vs. review recommendation)
3. **Review the Analysis**:
   - Price and analyst summary
   - Retrieved compliance policies
   - LLM's recommendation (Approve or Review)
4. **Make a Decision**:
   - Click **Approve** to accept the LLM's recommendation
   - Click **Reject** if you disagree with the LLM
5. **Check History**: Click any item in the right sidebar to reload a past analysis

### Demo Mode

Try the ticker **`BADNEWS`** to trigger the negative sentiment compliance check:

- The news will show bearish headlines
- Compliance will flag it for human review
- The LLM will recommend "review" instead of "approve"

## API Endpoints

### `/api/analyze` (POST)

Run a stock analysis for a given ticker.

**Request:**
```json
{
  "ticker": "AAPL"
}
```

**Response:**
```json
{
  "analysis_id": 1,
  "ticker": "AAPL",
  "price": 319.70,
  "analyst_summary": "...",
  "compliance_notes": "...",
  "llm_decision": "approve",
  "reason": "...",
  "retrieved_docs": [...]
}
```

### `/api/decision` (POST)

Record a human's approval/rejection decision.

**Request:**
```json
{
  "analysis_id": 1,
  "user_decision": "approve"
}
```

**Response:**
```json
{
  "analysis_id": 1,
  "user_decision": "approve",
  "timestamp": "2026-08-30T12:34:56"
}
```

### `/api/decisions` (GET)

List all past analyses and decisions (most recent first, max 50).

**Response:**
```json
[
  {
    "id": 1,
    "ticker": "AAPL",
    "analyst_summary": "...",
    "llm_decision": "approve",
    "user_decision": "approve",
    "created_at": "2026-08-30T12:34:56"
  }
]
```

### `/api/analysis/{id}` (GET)

Get full details of a specific analysis by ID.

## Database

Analysis data is stored in `decisions.db` (SQLite). Schema:

```sql
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    ticker TEXT,
    price REAL,
    profile TEXT,
    news TEXT,
    analyst_summary TEXT,
    compliance_notes TEXT,
    retrieved_docs TEXT,
    llm_decision TEXT,
    user_decision TEXT,
    reason TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

To inspect the database:

```bash
sqlite3 decisions.db
sqlite> SELECT ticker, user_decision, created_at FROM decisions ORDER BY created_at DESC;
```

## Troubleshooting

### CORS Error in Browser

If you see a CORS error when the frontend tries to call the backend, make sure:
1. Backend is running on `http://localhost:8000`
2. Frontend is opened via `file://` or `http://localhost:8080` (not a different port)

The backend has CORS enabled for all origins by default. If needed, edit `backend.py` line ~35 to restrict origins.

### Connection Refused

If you see "connection refused", make sure the backend is running:

```bash
python3 backend.py
```

### No Stock Data (Mock Data)

If you see "mock" in the profile/news, it means:
- **yfinance**: Works fine (always free)
- **Alpha Vantage**: API key not set. Add `ALPHA_VANTAGE_API_KEY` to `.env` to use real data, or just use mock for demo

## Extending the Chatbot

### Add More Agent Nodes

Edit `graph.py` to add new nodes (e.g., a risk assessment node). They automatically flow through the backend.

### Customize UI

Edit `index.html` CSS and JavaScript to change colors, layout, or add new features like:
- Email notifications on important decisions
- Export to CSV
- Webhooks to trading systems

### Add Authentication

Wrap the backend endpoints with Flask-Login or similar to track which user approved each decision.

### Connect to Database UI

Use a tool like `adminer` or `datagrip` to browse `decisions.db` in real-time as analyses come in.

## Notes

- The backend runs the full LangGraph (7 nodes) for each analysis, so it can take 10-30 seconds depending on LLM latency
- Analyses are stored as JSON in SQLite for easy export/auditing
- The UI is a single HTML file with embedded CSS/JS, so it runs in any browser without build steps
