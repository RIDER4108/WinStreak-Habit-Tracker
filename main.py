import sqlite3
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any

# Initialize the server
app = FastAPI(title="WinStreak API", version="1.0")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the data structure
class SyncPayload(BaseModel):
    username: str
    habits: List[Dict[str, Any]]
    meta: Dict[str, Any]

# --- DATABASE SETUP ---
def init_db():
    # Connects to (or creates) a file named winstreak.db in your folder
    conn = sqlite3.connect("winstreak.db")
    cursor = conn.cursor()
    # Create a table for users if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            username TEXT PRIMARY KEY,
            habits TEXT,
            meta TEXT
        )
    """)
    conn.commit()
    conn.close()

# Run the database setup as soon as the file runs
init_db()

@app.get("/")
def health_check():
    return {"status": "WinStreak Server is online! 🚀"}

@app.post("/api/sync")
def sync_data(payload: SyncPayload):
    # Connect to the DB
    conn = sqlite3.connect("winstreak.db")
    cursor = conn.cursor()
    
    # Save the data (INSERT if new user, UPDATE if existing user)
    cursor.execute("""
        INSERT INTO user_data (username, habits, meta)
        VALUES (?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            habits=excluded.habits,
            meta=excluded.meta
    """, (payload.username, json.dumps(payload.habits), json.dumps(payload.meta)))
    
    conn.commit()
    conn.close()
    
    print(f"✅ SYNCHRONIZED: Successfully saved data for '{payload.username}' to database.")
    
    return {"message": f"Data saved securely for {payload.username}!", "status": "success"}