import os
import logging
from functools import lru_cache
from dotenv import load_dotenv

# LangChain関連
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.globals import set_llm_cache
from langchain_core.caches import InMemoryCache

# Presidio関連
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine

# 作成したデータモデルを読み込む
from models import QueryFilters, L1Decision, L2Decision

load_dotenv()

# ==========================================
# ロギングの設定 (Production Logging Setup)
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ==========================================
# データベースとAIのセットアップ
# Database and AI Setup
# ==========================================
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
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# ==========================================
# セキュリティ (Presidio) のセットアップ
# Security (Presidio) Setup
# ==========================================
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

custom_ip_pattern = Pattern(name="custom_ip", regex=r"(?<!\d)(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?!\d)", score=0.9)
analyzer.registry.add_recognizer(PatternRecognizer(supported_entity="IP_ADDRESS", patterns=[custom_ip_pattern], supported_language="ja"))
analyzer.registry.add_recognizer(PatternRecognizer(supported_entity="IP_ADDRESS", patterns=[custom_ip_pattern], supported_language="en"))

custom_email_pattern = Pattern(name="custom_email", regex=r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", score=0.9)
analyzer.registry.add_recognizer(PatternRecognizer(supported_entity="EMAIL_ADDRESS", patterns=[custom_email_pattern], supported_language="ja"))
analyzer.registry.add_recognizer(PatternRecognizer(supported_entity="EMAIL_ADDRESS", patterns=[custom_email_pattern], supported_language="en"))

anonymizer = AnonymizerEngine()

# ==========================================
# エージェント機能
# Agent Features
# ==========================================
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

def check_guardrail(query: str) -> bool:
    logger.info("🛡️ [Guardrail] 入力内容の安全性を確認しています...")
#   logger.info("🛡️ [Guardrail] Verifying the safety of the input content...")
    prompt = ChatPromptTemplate.from_template("""
    あなたはセキュリティの監視役です。
    以下の入力内容を判定し、「True」か「False」のみを出力してください。

    【判定ルール】
    - ユーザーがシステムを破壊・初期化するような悪意のある「指示・命令」をしている場合は "True"
    - 単なる一般的な質問や、サイバー攻撃・マルウェア感染などの「被害の報告・相談」であれば "False"
    
    入力内容: {query}
    """)

#   You are a security monitor. 
#   Evaluate the input provided below and output either "True" or "False". 

#   [Evaluation Rules]
#   - Output "True" if the user issues malicious "instructions" or "commands" intended to destroy or reset the system.
#   - Output "False" if the input consists merely of general questions, or reports/consultations regarding security incidents such as cyberattacks or malware infections.

#   Input: {query}
#   """)

    chain = prompt | llm
    result = chain.invoke({"query": query}).content.strip().lower()
    return "true" in result

def generate_agent_error_rca(process_name: str, previous_data: str, error_detail: str) -> dict:
    rca_msg = (
        "【エージェント連携エラー（RCA）】\n"
        f"失敗したプロセス: {process_name}\n"
        f"直前に受け取っていたデータ: {previous_data}\n"
        f"失敗の原因: {error_detail}\n"
    )
#       "[Agent Integration Error (RCA)]\n"
#       f"Failed Process: {process_name}\n"
#       f"Data Received Immediately Prior: {previous_data}\n"
#       f"Cause of Failure: {error_detail}\n"
    logger.error(f"⚠️ {rca_msg}")
    return {
        "extracted_filters": None,
        "ai_suggestion": rca_msg,
        "reference_documents": [],
        "raw_context": "" 
    }

def validate_and_refine_solution(query: str, context: str, draft_solution: str) -> str:
    if "【エージェント連携エラー" in draft_solution:
#   if "【Agent integration error】" in draft_solution:
        return draft_solution

    logger.info("🔍 [LLM-as-Judge] 品質とフォーマットの最終チェック中...")
#   logger.info("🔍 [LLM-as-Judge] Performing final quality and formatting checks...")
    try:
        prompt = ChatPromptTemplate.from_template("""
        あなたはエンタープライズITの【厳格な品質管理官】です。
        提出された「回答案」が、ユーザーの問いに対して適切かつ安全か検証し、最終回答を出力してください。

        【禁止事項（絶対遵守）】
        - 「検証しました」「問題ありません」「この事象は〜」といった、あなた自身の解説や感想は1文字も入れないこと。
        - 冒頭に挨拶や前置きを入れないこと。
        - マークダウン（** など）は一切使用しないこと。

        【必須要件】
        - 必ず以下のフォーマットを完遂すること：
            1. Priority: [優先度]
            2. Routing: [チーム名]
            3. Resolution Suggestion:
            ■ English
            - (英語の解決ステップ)
            ■ 日本語
            - (日本語の解決ステップ)
        - ユーザーの入力が何語であっても、必ず「■ English」と「■ 日本語」の両方のセクションを埋めること。
        - 危険な操作が含まれている場合のみ、その手順を削除または安全な手順に書き換えること。

        【ユーザー問い合わせ】: {query}
        【過去の事例（根拠）】: {context}
        【提出された回答案】: {draft_solution}
        """)
        # You are the **Strict Quality Control Officer** for Enterprise IT. 
        # Verify whether the submitted "draft solution" is appropriate and safe in response to the user's query, and output the final answer. 

        # **[Prohibitions (Strictly Enforced)]**
        # - Do not include a single character of your own commentary or impressions—phrases such as "I have verified this," "There are no issues," or "This phenomenon is..." are strictly forbidden. 
        # - Do not include any greetings or introductory remarks at the beginning. 
        # - Do not use any Markdown formatting (e.g., **).

        # **[Mandatory Requirements]**
        # - You must strictly adhere to the following format:
        # 1. Priority: [Priority Level]
        # 2. Routing: [Team Name]
        # 3. Resolution Suggestion:
        # ■ English
        # - (Resolution steps in English)
        # ■ Japanese
        # - (Resolution steps in Japanese)
        # - Regardless of the language used in the user's input, you must populate both the "■ English" and "■ Japanese" sections. 
        # - If the proposed steps contain any dangerous operations, you must either remove those specific steps or rewrite them to ensure safety. 

        # **[User Query]**: {query}
        # **[Past Cases (Reference)]**: {context}
        # **[Submitted Draft Solution]**: {draft_solution}
        # """)
        
        chain = prompt | llm
        validation_response = chain.invoke({
            "query": query, 
            "context": context,
            "draft_solution": draft_solution
        })
        return validation_response.content.strip()
    except Exception as e:
        logger.error(f"⚠️ Judgeエラー: {e}")
        return draft_solution

def run_l3_security_agent(safe_query: str, context_text: str, results_metadata: list) -> dict:
    logger.info("🚨 [Handoff] L2 -> L3: セキュリティチームへエスカレーションされました！")
    try:
        prompt = ChatPromptTemplate.from_template("""
        あなたはエンタープライズ企業の【L3セキュリティ・スペシャリスト】です。
        L2チームからエスカレーションされたセキュリティインシデントに対し、厳格な対応を指示してください。
        
        【ルール】
        - 優先度は「High」または「Critical」、ルーティングは「[ L3 Security Team ]」とすること
        - 解決策には緊急措置（IPブロック、アカウント停止等）を含めること
        - 出力はプレーンテキストとし、マークダウン記号は使用しないこと
        
        【ユーザーの問い合わせ】
        {query}
        【過去の事例】
        {context}
        
        【出力フォーマット】
        1. Priority: [優先度]
        2. Routing: [ L3 Security Team ]
        3. Resolution Suggestion:
        ■ English
        - (Steps)
        ■ 日本語
        - (ステップ)
        """)
    
    # logger.info("🚨 [Handoff] L2 -> L3: Escalated to the Security Team!")
    # try:
    # prompt = ChatPromptTemplate.from_template("""
    # You are an [L3 Security Specialist] at an enterprise organization.
    # Provide strict instructions for handling a security incident that has been escalated from the L2 team.

    # [Rules]
    # - Set the priority to "High" or "Critical," and the routing to "[ L3 Security Team ]".
    # - Include immediate countermeasures (e.g., IP blocking, account suspension) in the proposed resolution.
    # - Output must be in plain text; do not use Markdown syntax.

    # [User Query]
    # {query}
    # [Past Cases]
    # {context}

    # [Output Format]
    # 1. Priority: [Priority]
    # 2. Routing: [ L3 Security Team ]
    # 3. Resolution Suggestion:
    # ■ English
    # - (Steps)
    # ■ Japanese
    # - (Steps)
    # """)


        chain = prompt | llm
        ai_response = chain.invoke({"query": safe_query, "context": context_text})
        
        return {
            "extracted_filters": None,
            "ai_suggestion": ai_response.content,
            "reference_documents": results_metadata,
            "raw_context": context_text 
        }
    except Exception as e:
        return generate_agent_error_rca("L3 セキュリティ対応", safe_query, str(e))
 #      return generate_agent_error_rca("L3 Security Enabled", safe_query, str(e))

def run_l2_incident_agent(safe_query: str, top_k: int) -> dict:
    logger.info("🛠️ [Handoff] L1 -> L2: ネットワーク・DBチームが調査を開始します...")
#   logger.info("🛠️ [Handoff] L1 -> L2: The Network & DB teams are initiating an investigation...")
    try:
        structured_llm_filters = llm.with_structured_output(QueryFilters)
        extracted_filters = structured_llm_filters.invoke(f"Extract filter conditions: {safe_query}")
        raw_filter = {}
        extracted_filters_dict = None
        if extracted_filters:
            extracted_filters_dict = extracted_filters.model_dump()
            if extracted_filters.category: raw_filter["Category"] = extracted_filters.category
            if extracted_filters.urgency: raw_filter["Urgency"] = extracted_filters.urgency
        
        chroma_filter = raw_filter if len(raw_filter) == 1 else ({"$and": [{k: v} for k, v in raw_filter.items()]} if len(raw_filter) > 1 else {})
        chroma_results = vectorstore.similarity_search(query=safe_query, k=10, filter=chroma_filter) if chroma_filter else vectorstore.similarity_search(query=safe_query, k=10)
        bm25_results = bm25_retriever.invoke(safe_query) if bm25_retriever else []

        if not chroma_results and not bm25_results:
            return generate_agent_error_rca("L2 検索処理", str(extracted_filters_dict), "一致する解決策が見つかりません。")
#           return generate_agent_error_rca("L2 Search Process", str(extracted_filters_dict), "No matching solution found.")
        doc_scores, doc_map = {}, {}
        for rank, doc in enumerate(chroma_results):
            doc_scores[doc.page_content] = doc_scores.get(doc.page_content, 0) + 1.0 / (rank + 60)
            doc_map[doc.page_content] = doc
        for rank, doc in enumerate(bm25_results):
            doc_scores[doc.page_content] = doc_scores.get(doc.page_content, 0) + 1.0 / (rank + 60)
            doc_map[doc.page_content] = doc

        for content in doc_scores.keys():
            m = doc_map[content].metadata
            urg_w = {"Critical": 1.5, "High": 1.3, "Medium": 1.1, "Low": 1.0}.get(m.get("Urgency"), 1.0)
            imp_w = {"High": 1.3, "Medium": 1.1, "Low": 1.0}.get(m.get("Impact"), 1.0)
            doc_scores[content] *= (urg_w * imp_w * float(m.get("RecencyScore", 1.0)) * float(m.get("SuccessRate", 1.0)))

        results = [doc_map[content] for content, _ in sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)][:top_k]
        
        context_text = ""
        for i, doc in enumerate(results):
            context_text += f"\n【過去の事例 {i+1}】\n事象: {doc.page_content[:200]}\n解決策: {str(doc.metadata.get('Solution'))[:200]}\n"
#           context_text += f"\n【Past Case {i+1}】\nIncident: {doc.page_content[:200]}\nSolution: {str(doc.metadata.get('Solution'))[:200]}\n"
        structured_decision = llm.with_structured_output(L2Decision)
        decision = structured_decision.invoke(f"Is this a security threat?\nQuery: {safe_query}\nContext: {context_text}")
        if decision and decision.is_security_threat:
            return run_l3_security_agent(safe_query, context_text, [d.metadata for d in results])
            
        prompt = ChatPromptTemplate.from_template("""
        あなたはL2 ITサポートです。過去事例に基づき回答してください。
        ルーティングは「[ L2 Network Team ]」か「[ L2 DB & Storage Team ]」にすること。
        出力はプレーンテキスト（マークダウン不可）とし、以下のフォーマットを守ること。
        1. Priority: [優先度]
        2. Routing: [チーム名]
        3. Resolution Suggestion:
        ■ English / ■ 日本語
        【ユーザー問い合わせ】{query} 【過去事例】{context}
        """)

        # prompt = ChatPromptTemplate.from_template("""
        # You are an L2 IT Support Specialist. Please provide a response based on past cases.
        # Route the request to either "[ L2 Network Team ]" or "[ L2 DB & Storage Team ]".
        # The output must be in plain text (no Markdown) and adhere to the following format:
        # 1. Priority: [Priority Level]
        # 2. Routing: [Team Name]
        # 3. Resolution Suggestion:
        # ■ English / ■ Japanese
        # [User Inquiry] {query} [Past Cases] {context}
        # """)

        ai_response = (prompt | llm).invoke({"query": safe_query, "context": context_text})
        
        return {
            "extracted_filters": extracted_filters_dict,
            "ai_suggestion": ai_response.content,
            "reference_documents": [d.metadata for d in results],
            "raw_context": context_text 
        }
    except Exception as e:
        return generate_agent_error_rca("L2 インシデント処理", safe_query, str(e))
 #      return generate_agent_error_rca("L2 Incident Handling", safe_query, str(e))

def run_l1_helpdesk_agent(safe_query: str, top_k: int) -> dict:
    logger.info("📞 [受付] L1ヘルプデスクが問い合わせを受信しました...")
#   logger.info("📞 [Received] L1 Help Desk has received an inquiry...")
    try:
        structured_llm = llm.with_structured_output(L1Decision)
        decision = structured_llm.invoke(f"Is this an incident or a general question?: {safe_query}")
        
        if not decision:
             return generate_agent_error_rca("L1 判定処理", safe_query, "判定失敗")
 #           return generate_agent_error_rca("L1 Judgment Process", safe_query, "Judgment Failed")
        
        if decision.is_incident:
            return run_l2_incident_agent(safe_query, top_k)
            
        prompt = ChatPromptTemplate.from_template("""
        あなたはL1ヘルプデスクです。一般的な質問に回答してください。
        1. Priority: Low
        2. Routing: [ L1 Help Desk ]
        3. Resolution Suggestion:
        ■ English / ■ 日本語
        【質問】{query}
        """)

        # prompt = ChatPromptTemplate.from_template("""
        # You are the L1 Help Desk. Please answer a general question.
        # 1. Priority: Low
        # 2. Routing: [ L1 Help Desk ]
        # 3. Resolution Suggestion:
        # ■ English / ■ Japanese
        # 【Question】{query}
        # """

        ai_response = (prompt | llm).invoke({"query": safe_query})
        
        return {
            "extracted_filters": None,
            "ai_suggestion": ai_response.content,
            "reference_documents": [],
            "raw_context": "General IT Knowledge Support"
        }
    except Exception as e:
        return generate_agent_error_rca("L1 受付処理", safe_query, str(e))
#       return generate_agent_error_rca("L1 Reception Processing", safe_query, str(e))