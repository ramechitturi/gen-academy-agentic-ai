import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()

from graph import app


async def run(ticker: str):
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
    result = await app.ainvoke(initial_state)

    print(f"\n--- {ticker} ---")
    print("Price data:", result["price_data"])
    print("\nSummary:", result["summary"])
    print("\nRetrieved policy docs:", [d["source"] for d in result["retrieved_docs"]])
    print("Compliance notes:", result["compliance_notes"])
    print("\nDecision:", result["decision"], "-", result["reason"])
    print("Status:", result["status"])


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    asyncio.run(run(ticker))
