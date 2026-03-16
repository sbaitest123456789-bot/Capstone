from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import os
import json
from dotenv import load_dotenv
from functools import lru_cache
import traceback

# --- LangChain関連のインポート ---
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.globals import set_llm_cache
from langchain_core.caches import InMemoryCache

# Presidio（ローカルでのPIIマスキング）
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

load_dotenv()

app = FastAPI(
    title="IT Incident Knowledge Base API",
    description="過去のインシデントを検索する高度なAIアシスタント",
    version="2.0.0" 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- データベースとAIの初期化 ---
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings,
    collection_name="incidents"
)

db_data = vectorstore.get()
docs_for_bm25 = []
if db_data and 'documents' in db_data:
    for i in range(len(db_data['documents'])):
        docs_for_bm25.append(
            Document(page_content=db_data['documents'][i], metadata=db_data['metadatas'][i])
        )
bm25_retriever = BM25Retriever.from_documents(docs_for_bm25) if docs_for_bm25 else None

set_llm_cache(InMemoryCache())

# より安定して指定フォーマットを出力する gpt-4o-mini
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# --- Presidio NLPエンジンの初期化 ---
configuration = {
    "nlp_engine_name": "spacy",
    "models": [
        {"lang_code": "ja", "model_name": "ja_core_news_sm"},
        {"lang_code": "en", "model_name": "en_core_web_sm"}
    ]
}
provider = NlpEngineProvider(nlp_configuration=configuration)
nlp_engine = provider.create_engine()
analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["ja", "en"])

# IPアドレスとメールアドレスの強力なカスタムルール
custom_ip_pattern = Pattern(name="custom_ip", regex=r"(?<!\d)(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?!\d)", score=0.9)
analyzer.registry.add_recognizer(PatternRecognizer(supported_entity="IP_ADDRESS", patterns=[custom_ip_pattern], supported_language="ja"))
analyzer.registry.add_recognizer(PatternRecognizer(supported_entity="IP_ADDRESS", patterns=[custom_ip_pattern], supported_language="en"))

custom_email_pattern = Pattern(name="custom_email", regex=r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", score=0.9)
analyzer.registry.add_recognizer(PatternRecognizer(supported_entity="EMAIL_ADDRESS", patterns=[custom_email_pattern], supported_language="ja"))
analyzer.registry.add_recognizer(PatternRecognizer(supported_entity="EMAIL_ADDRESS", patterns=[custom_email_pattern], supported_language="en"))

anonymizer = AnonymizerEngine()

# --- データモデル ---
class SearchQuery(BaseModel):
    query_text: str
    top_k: int = 3

class QueryFilters(BaseModel):
    category: Optional[str] = Field(description="Category (e.g., Database, Network, Storage, Application, Security, Hardware)", default=None)
    urgency: Optional[str] = Field(description="Urgency (e.g., Critical, High, Medium, Low)", default=None)

class L1Decision(BaseModel):
    is_incident: bool = Field(description="システムが動かない、アクセスできない等のインシデントであればTrue、パスワード変更等の一般的な質問であればFalse")

class L2Decision(BaseModel):
    is_security_threat: bool = Field(description="不正アクセス、攻撃の検知、マルウェアなどセキュリティに関する重大な脅威であればTrue、通常のインシデントであればFalse")

# --- 関数群 ---
@lru_cache(maxsize=1024)
def mask_pii_with_presidio(text: str) -> str:
    is_japanese = any('\u3040' <= c <= '\u30ff' or '\u4e00' <= c <= '\u9faf' for c in text)
    if is_japanese:
        results_ja = analyzer.analyze(text=text, entities=["PERSON"], language='ja')
        results_en = analyzer.analyze(text=text, entities=["EMAIL_ADDRESS", "IP_ADDRESS", "PHONE_NUMBER"], language='en')
        results = results_ja + results_en
    else:
        results = analyzer.analyze(text=text, entities=["PERSON", "EMAIL_ADDRESS", "IP_ADDRESS", "PHONE_NUMBER"], language='en')
        
    return anonymizer.anonymize(text=text, analyzer_results=results).text

# ==========================================
# L3: セキュリティ専門エージェント
# ==========================================
def run_l3_security_agent(safe_query: str, context_text: str, results_metadata: list) -> dict:
    print("🚨 [Handoff] L2 -> L3: セキュリティチームへエスカレーションされました！")
    
    prompt = ChatPromptTemplate.from_template("""
    あなたはエンタープライズ企業の【L3セキュリティ・スペシャリスト】です。
    L2チームからエスカレーションされた以下の重大なセキュリティインシデントに対し、厳格な対応を指示してください。
    
    【ルール】
    - トリアージ優先度は必ず「High」または「Critical」にすること
    - ルーティング先は必ず「[ L3 Security Team ]」にすること
    - 解決策には、IPブロック、アカウント停止、ネットワーク遮断などの緊急措置を含めること
    - 出力はプレーンテキストとし、マークダウン記号（** など）は使用しないこと
    
    【ユーザーの問い合わせ】
    {query}

    【L2チームが検索した過去の事例】
    {context}
    
    【出力フォーマット】(※絶対にこの形式を守ること)
    1. Priority: [優先度]
    2. Routing: [ L3 Security Team ]
    3. Resolution Suggestion:
    ■ English
    - (Action step 1)
    - (Action step 2)
    ■ 日本語
    - (具体的な解決ステップ1)
    - (具体的な解決ステップ2)
    """)
    
    chain = prompt | llm
    ai_response = chain.invoke({"query": safe_query, "context": context_text})
    
    return {
        "extracted_filters": None,
        "ai_suggestion": ai_response.content,
        "reference_documents": results_metadata
    }

# ==========================================
# L2: インシデント対応エージェント
# ==========================================
def run_l2_incident_agent(safe_query: str, top_k: int) -> dict:
    print("🛠️ [Handoff] L1 -> L2: ネットワーク・DBチームが調査を開始します...")
    
    structured_llm_filters = llm.with_structured_output(QueryFilters)
    extracted_filters = structured_llm_filters.invoke(f"Extract filter conditions from this incident query if explicitly mentioned: {safe_query}")
    
    raw_filter = {}
    extracted_filters_dict = None
    
    if extracted_filters:
        if hasattr(extracted_filters, 'model_dump'):
            extracted_filters_dict = extracted_filters.model_dump()
            cat = getattr(extracted_filters, 'category', None)
            urg = getattr(extracted_filters, 'urgency', None)
            if cat: raw_filter["Category"] = cat
            if urg: raw_filter["Urgency"] = urg
        elif isinstance(extracted_filters, dict):
            extracted_filters_dict = extracted_filters
            if extracted_filters.get('category'): raw_filter["Category"] = extracted_filters.get('category')
            if extracted_filters.get('urgency'): raw_filter["Urgency"] = extracted_filters.get('urgency')
    
    chroma_filter = {}
    if len(raw_filter) == 1:
        chroma_filter = raw_filter
    elif len(raw_filter) > 1:
        and_conditions = [{k: v} for k, v in raw_filter.items()]
        chroma_filter = {"$and": and_conditions}
        
    fetch_k = 10
    if chroma_filter:
        chroma_results = vectorstore.similarity_search(query=safe_query, k=fetch_k, filter=chroma_filter)
    else:
        chroma_results = vectorstore.similarity_search(query=safe_query, k=fetch_k)
        
    bm25_results = bm25_retriever.invoke(safe_query) if bm25_retriever else []

    doc_scores, doc_map = {}, {}
    for rank, doc in enumerate(chroma_results):
        doc_scores[doc.page_content] = doc_scores.get(doc.page_content, 0) + 1.0 / (rank + 60)
        doc_map[doc.page_content] = doc
    for rank, doc in enumerate(bm25_results):
        doc_scores[doc.page_content] = doc_scores.get(doc.page_content, 0) + 1.0 / (rank + 60)
        doc_map[doc.page_content] = doc

    urgency_weight = {"Critical": 1.5, "High": 1.3, "Medium": 1.1, "Low": 1.0}
    impact_weight = {"High": 1.3, "Medium": 1.1, "Low": 1.0}
    
    for content in doc_scores.keys():
        metadata = doc_map[content].metadata or {} 
        doc_scores[content] *= urgency_weight.get(metadata.get("Urgency", "Low"), 1.0) * impact_weight.get(metadata.get("Impact", "Low"), 1.0)

    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    results = [doc_map[content] for content, score in sorted_docs][:top_k]
    
    context_text = ""
    for i, doc in enumerate(results):
        metadata = doc.metadata or {}
        context_text += f"\n【過去の事例 {i+1}】\n事象: {doc.page_content}\n解決策: {metadata.get('Solution', 'N/A')}\n"

    structured_llm_decision = llm.with_structured_output(L2Decision)
    decision = structured_llm_decision.invoke(f"以下の問い合わせと検索された事例から、これが不正アクセスなどのセキュリティの脅威か判断してください。\n問い合わせ: {safe_query}\n過去の事例: {context_text}")
    
    is_threat = False
    if decision:
        if hasattr(decision, 'is_security_threat'):
            is_threat = decision.is_security_threat
        elif isinstance(decision, dict):
            is_threat = decision.get('is_security_threat', False)
    
    if is_threat:
        return run_l3_security_agent(safe_query, context_text, [doc.metadata for doc in results])
        
    print("✅ [L2 完了] 通常のインシデントとしてL2チームが解決策を生成します")
    prompt = ChatPromptTemplate.from_template("""
    あなたはエンタープライズ企業の【L2 ITサポートディスパッチャー】です。
    ユーザーからの問い合わせ内容と、検索された過去の事例をもとに、出力してください。
    
    【ルール】
    - ルーティング先は「[ L2 Network Team ]」か「[ L2 DB & Storage Team ]」のいずれかにすること。
    - 出力はプレーンテキストとし、マークダウン記号（** など）は使用しないこと
    
    【ユーザーの問い合わせ】
    {query}

    【参考となる過去の事例】
    {context}
    
    【出力フォーマット】(※絶対にこの形式を守ること)
    1. Priority: [優先度]
    2. Routing: [チーム名]
    3. Resolution Suggestion:
    ■ English
    - (Action step 1)
    - (Action step 2)
    ■ 日本語
    - (具体的な解決ステップ1)
    - (具体的な解決ステップ2)
    """)
    chain = prompt | llm
    ai_response = chain.invoke({"query": safe_query, "context": context_text})
    
    return {
        "extracted_filters": extracted_filters_dict,
        "ai_suggestion": ai_response.content,
        "reference_documents": [doc.metadata for doc in results]
    }

# ==========================================
# L1: 一次受付エージェント
# ==========================================
def run_l1_helpdesk_agent(safe_query: str, top_k: int) -> dict:
    print("📞 [受付] L1ヘルプデスクが問い合わせを受信しました...")
    
    structured_llm = llm.with_structured_output(L1Decision)
    decision = structured_llm.invoke(f"以下の問い合わせは、システム障害などのインシデントですか？一般的な質問ですか？: {safe_query}")
    
    is_inc = False
    if decision:
        if hasattr(decision, 'is_incident'):
            is_inc = decision.is_incident
        elif isinstance(decision, dict):
            is_inc = decision.get('is_incident', False)
            
    if is_inc:
        return run_l2_incident_agent(safe_query, top_k)
        
    print("✅ [L1 完了] 一般的な質問としてL1チームが回答します")
    prompt = ChatPromptTemplate.from_template("""
    あなたはエンタープライズ企業の【L1 ヘルプデスク担当】です。
    ユーザーからの一般的なITに関する質問に対して、丁寧かつ簡潔に回答してください。
    
    【ルール】
    - 出力はプレーンテキストとし、マークダウン記号（** など）は使用しないこと
    
    【ユーザーの質問】
    {query}
    
    【出力フォーマット】(※絶対にこの形式を守ること)
    1. Priority: Low
    2. Routing: [ L1 Help Desk ]
    3. Resolution Suggestion:
    ■ English
    - (Action step 1)
    - (Action step 2)
    ■ 日本語
    - (具体的な回答ステップ1)
    - (具体的な回答ステップ2)
    """)
    chain = prompt | llm
    ai_response = chain.invoke({"query": safe_query})
    
    return {
        "extracted_filters": None,
        "ai_suggestion": ai_response.content,
        "reference_documents": []
    }

# ==========================================
# APIの受付口
# ==========================================
@app.post("/api/search")
async def search_incidents(request: SearchQuery):
    try:
        safe_query = mask_pii_with_presidio(request.query_text)
        agent_result = run_l1_helpdesk_agent(safe_query, request.top_k)
        
        return {
            "status": "success",
            "original_query": request.query_text,
            "masked_query": safe_query,
            "extracted_filters": agent_result.get("extracted_filters"),
            "ai_suggestion": agent_result["ai_suggestion"],
            "reference_documents": agent_result["reference_documents"]
        }
    
    except Exception as e:
        print("❌ エラーが発生しました！詳細:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Incident Assistant API is running!"}