from fastapi import APIRouter, HTTPException
import csv
import os
import logging
from datetime import datetime
from models import FeedbackQuery

# ==========================================
# ロギングの設定 (Production Logging Setup)
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

router = APIRouter()
FEEDBACK_FILE = "feedback_log.csv"

@router.post("/feedback")
async def save_feedback(feedback: FeedbackQuery):
    logger.info(f"📝 [Feedback] 受信: {'👍 Helpful' if feedback.is_helpful else '👎 Not Helpful'}")
    # logger.info(f"📝 [Feedback] Received: {'👍 Helpful' if feedback.is_helpful else '👎 Not Helpful'}")

    file_exists = os.path.isfile(FEEDBACK_FILE)
    try:
        with open(FEEDBACK_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Query", "Category", "Helpful", "AI_Suggestion"])
            
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                feedback.query,
                feedback.category,
                feedback.is_helpful,
                feedback.ai_suggestion.replace('\n', ' ') 
            ])
        return {"status": "success", "message": "Feedback saved!"}
    except Exception as e:
        logger.error(f"❌ フィードバック保存エラー: {e}")
        # logger.error(f"❌ Feedback save error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save feedback")