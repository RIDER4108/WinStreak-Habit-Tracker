from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
import sqlite3
import json

# ==========================================
# 1. APP SETUP & CORS
# ==========================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. SECURITY ENGINE (BCRYPT)
# ==========================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# ==========================================
# 3. DATABASE SETUP (SQLITE)
# ==========================================
def init_db():
    conn = sqlite3.connect("winstreak.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            habits_data TEXT,
            meta_data TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 4. DATA MODELS
# ==========================================
class UserAuth(BaseModel):
    username: str
    password: str

class SyncPayload(BaseModel):
    username: str
    habits: list
    meta: dict

class ChangePasswordReq(BaseModel):
    username: str
    current_password: str
    new_password: str

# ==========================================
# 5. API ENDPOINTS
# ==========================================

@app.post("/api/signup")
async def signup(user: UserAuth):
    conn = sqlite3.connect("winstreak.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists. Try logging in.")
        
    hashed_pw = get_password_hash(user.password)
    cursor.execute("INSERT INTO users (username, password, habits_data, meta_data) VALUES (?, ?, ?, ?)", 
                   (user.username, hashed_pw, "[]", "{}"))
    conn.commit()
    conn.close()
    
    return {"message": "Account created successfully"}

@app.post("/api/login")
async def login(user: UserAuth):
    conn = sqlite3.connect("winstreak.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT password FROM users WHERE username = ?", (user.username,))
    row = cursor.fetchone()
    conn.close()
    
    if not row or not verify_password(user.password, row[0]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    return {"message": "Login successful"}

@app.post("/api/sync")
async def sync_data(payload: SyncPayload):
    conn = sqlite3.connect("winstreak.db")
    cursor = conn.cursor()
    
    habits_json = json.dumps(payload.habits)
    meta_json = json.dumps(payload.meta)
    
    cursor.execute("""
        UPDATE users 
        SET habits_data = ?, meta_data = ? 
        WHERE username = ?
    """, (habits_json, meta_json, payload.username))
    
    conn.commit()
    conn.close()
    
    return {"message": "Data synced successfully"}

@app.post("/api/change-password")
async def change_password(data: ChangePasswordReq):
    conn = sqlite3.connect("winstreak.db")
    cursor = conn.cursor()
    
    # 1. Verify they know their current password before changing it
    cursor.execute("SELECT password FROM users WHERE username = ?", (data.username,))
    row = cursor.fetchone()
    
    if not row or not verify_password(data.current_password, row[0]):
        conn.close()
        raise HTTPException(status_code=401, detail="Incorrect current password.")
        
    # 2. Hash the new password and update the database
    hashed_new_pw = get_password_hash(data.new_password)
    cursor.execute("UPDATE users SET password = ? WHERE username = ?", (hashed_new_pw, data.username))
    conn.commit()
    conn.close()
    
    return {"message": "Password updated successfully"}

@app.post("/api/delete-account")
async def delete_account(user: UserAuth):
    conn = sqlite3.connect("winstreak.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT password FROM users WHERE username = ?", (user.username,))
    row = cursor.fetchone()
    
    if not row or not verify_password(user.password, row[0]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid password. Cannot delete account.")
        
    cursor.execute("DELETE FROM users WHERE username = ?", (user.username,))
    conn.commit()
    conn.close()
    
    return {"message": "Account permanently deleted"}