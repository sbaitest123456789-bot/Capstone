from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import search, feedback

# ==========================================
# サーバーの初期化
# Server Initialization
# ==========================================
app = FastAPI(
    title="IT Incident Knowledge Base API",
    description="過去のインシデントを検索する高度なAIアシスタント",
#   description="An advanced AI assistant for searching past incidents"
    version="2.0.0" 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 別フォルダ(routers)のAPI受付口を登録する
# Register the API endpoints located in a separate folder (routers).
# ==========================================
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])

# ==========================================
# ルートのヘルスチェック
# Root Health Check
# ==========================================
@app.get("/")
def read_root():
    return {"message": "Incident Assistant API is running!"}