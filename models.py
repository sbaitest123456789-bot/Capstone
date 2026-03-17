from pydantic import BaseModel, Field
from typing import Optional

class SearchQuery(BaseModel):
    query_text: str = Field(..., max_length=500)
    top_k: int = 3

class FeedbackQuery(BaseModel):
    query: str
    ai_suggestion: str
    is_helpful: bool  # True = 👍, False = 👎
    category: Optional[str] = None

class QueryFilters(BaseModel):
    category: Optional[str] = Field(description="Category (e.g., Database, Network, Storage, Application, Security, Hardware)", default=None)
    urgency: Optional[str] = Field(description="Urgency (e.g., Critical, High, Medium, Low)", default=None)

class L1Decision(BaseModel):
    is_incident: bool = Field(description="システムが動かない、アクセスできない等のインシデントであればTrue、パスワード変更等の一般的な質問であればFalse")
#   is_incident: bool = Field(description="True if the issue is an incident (e.g., the system is down or inaccessible); False if it is a general inquiry (e.g., a password change request).")
class L2Decision(BaseModel):
    is_security_threat: bool = Field(description="不正アクセス、攻撃の検知、マルウェアなどセキュリティに関する重大な脅威であればTrue、通常のインシデントであればFalse")
#   is_security_threat: bool = Field(description="True if the incident constitutes a major security threat—such as unauthorized access, detection of an attack, or malware—and False if it is a standard incident.")