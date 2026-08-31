"""
FastAPI backend for stock analysis with human approval workflow.
Wraps the LangGraph agent and stores decisions in SQLite.
"""

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph import app as graph_app

# Database setup
DB_PATH = Path(__file__).parent / "decisions.db"

def init_db():
    """Create database table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            price REAL,
            profile TEXT,
            news TEXT,
            analyst_summary TEXT,
            compliance_notes TEXT,
            retrieved_docs TEXT,
            llm_decision TEXT,
            user_decision TEXT,
            reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# API models
class AnalysisRequest(BaseModel):
    ticker: str

class AnalysisResponse(BaseModel):
    analysis_id: int
    ticker: str
    price: Optional[float]
    analyst_summary: str
    compliance_notes: str
    llm_decision: str
    reason: str
    retrieved_docs: list

class DecisionRequest(BaseModel):
    analysis_id: int
    user_decision: str  # "approve" or "reject"

class DecisionResponse(BaseModel):
    analysis_id: int
    user_decision: str
    timestamp: str

class DecisionHistory(BaseModel):
    id: int
    ticker: str
    analyst_summary: str
    llm_decision: str
    user_decision: str
    created_at: str

# FastAPI app
app = FastAPI(
    title="Stock Analysis API",
    description="Multi-agent stock analysis with human approval workflow"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_stock(request: AnalysisRequest):
    """
    Run the stock analysis graph for a given ticker.
    Stores intermediate results and returns analysis ID for later approval.
    """
    ticker = request.ticker.upper()

    try:
        # Initialize state and run the graph
        initial_state = {
            "ticker": ticker,
            "price_data": {},
            "profile": {},
            "news": [],
            "summary": "",
            "compliance_notes": "",
            "retrieved_docs": [],
            "decision": "",
            "reason": "",
            "status": "",
        }

        result = await graph_app.ainvoke(initial_state)

        # Extract price from price_data
        price = None
        if isinstance(result["price_data"], dict) and "price" in result["price_data"]:
            price = result["price_data"]["price"]
        elif isinstance(result["price_data"], list) and len(result["price_data"]) > 0:
            # Handle MCP wrapper format
            import json
            try:
                price_data = json.loads(result["price_data"][0]["text"])
                price = price_data.get("price")
            except:
                pass

        # Store analysis in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        import json
        cursor.execute("""
            INSERT INTO decisions (
                ticker, price, profile, news, analyst_summary,
                compliance_notes, retrieved_docs, llm_decision, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ticker,
            price,
            json.dumps(result["profile"]),
            json.dumps(result["news"]),
            result["summary"],
            result["compliance_notes"],
            json.dumps([d if isinstance(d, dict) else json.loads(d) if isinstance(d, str) else str(d)
                       for d in result["retrieved_docs"]]),
            result["decision"],
            result["reason"]
        ))
        conn.commit()
        analysis_id = cursor.lastrowid
        conn.close()

        return AnalysisResponse(
            analysis_id=analysis_id,
            ticker=ticker,
            price=price,
            analyst_summary=result["summary"],
            compliance_notes=result["compliance_notes"],
            llm_decision=result["decision"],
            reason=result["reason"],
            retrieved_docs=result["retrieved_docs"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/decision", response_model=DecisionResponse)
async def submit_decision(request: DecisionRequest):
    """
    Record the human's approval/rejection decision for an analysis.
    """
    if request.user_decision not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Decision must be 'approve' or 'reject'")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE decisions
            SET user_decision = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (request.user_decision, request.analysis_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Analysis not found")

        conn.commit()

        cursor.execute("SELECT updated_at FROM decisions WHERE id = ?", (request.analysis_id,))
        timestamp = cursor.fetchone()[0]
        conn.close()

        return DecisionResponse(
            analysis_id=request.analysis_id,
            user_decision=request.user_decision,
            timestamp=timestamp
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decision submission failed: {str(e)}")

@app.get("/api/decisions", response_model=list[DecisionHistory])
async def get_decisions():
    """
    Retrieve all past analysis decisions.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, ticker, analyst_summary, llm_decision, user_decision, created_at
            FROM decisions
            ORDER BY created_at DESC
            LIMIT 50
        """)

        rows = cursor.fetchall()
        conn.close()

        return [
            DecisionHistory(
                id=row[0],
                ticker=row[1],
                analyst_summary=row[2],
                llm_decision=row[3],
                user_decision=row[4] or "pending",
                created_at=row[5]
            )
            for row in rows
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

@app.get("/api/analysis/{analysis_id}")
async def get_analysis(analysis_id: int):
    """
    Retrieve a specific analysis by ID.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                ticker, price, analyst_summary, compliance_notes,
                retrieved_docs, llm_decision, user_decision, reason, created_at
            FROM decisions WHERE id = ?
        """, (analysis_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Analysis not found")

        import json
        return {
            "analysis_id": analysis_id,
            "ticker": row[0],
            "price": row[1],
            "analyst_summary": row[2],
            "compliance_notes": row[3],
            "retrieved_docs": json.loads(row[4]) if row[4] else [],
            "llm_decision": row[5],
            "user_decision": row[6] or "pending",
            "reason": row[7],
            "created_at": row[8]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
