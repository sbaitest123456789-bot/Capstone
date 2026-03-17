# Architecture Decision Records (ADRs)

This document outlines the key architectural decisions, technology choices, and trade-offs made during the development of the Incident Intelligence Base.

## English Version

### 1. Separation of Concerns: Microservices Architecture
* **Context:** The system needs to be maintainable, scalable, and easy to upgrade in an enterprise environment.
* **Decision:** We decoupled the system into a Frontend (Next.js/React) and a Backend API (FastAPI/Python), containerized via Docker.
* **Pros:** * Independent scaling of UI and AI processing layers.
  * The Vector DB (ChromaDB) or LLM provider can be easily swapped without rewriting the frontend.
* **Trade-offs:** Slightly higher deployment complexity (requires Docker Compose) compared to a monolithic application (e.g., Streamlit).

### 2. Retrieval Strategy: Hybrid Search (Vector + Keyword)
* **Context:** IT support queries contain both semantic descriptions (e.g., "server is running slow") and exact strings (e.g., "INC-5005", "Error 0x80070057"). Pure vector search struggles with exact keyword matches.
* **Decision:** Implemented a Hybrid Search engine combining **ChromaDB** (Dense Vector Search) and **BM25** (Sparse Keyword Search), fused using the **Reciprocal Rank Fusion (RRF)** algorithm.
* **Pros:** Maximizes retrieval accuracy by capturing both contextual meaning and exact system identifiers.
* **Trade-offs:** Higher memory usage and slightly increased latency due to running two search indices simultaneously.

### 3. Data Privacy: Deterministic PII Masking
* **Context:** Sending enterprise incident data containing Personally Identifiable Information (PII) to external LLM APIs poses a severe security risk.
* **Decision:** Integrated **Microsoft Presidio** (with local spaCy NLP models) to sanitize inputs *before* they leave the backend environment.
* **Pros:** * Zero risk of data leakage to external providers.
  * Faster and more deterministic than relying on an LLM-based masking prompt.
* **Trade-offs:** The backend Docker image size is larger due to the inclusion of local NLP models (en_core_web_sm, ja_core_news_sm).

### 4. Processing Flow: Multi-Tier Agent System
* **Context:** Routing every user query to a complex, heavy reasoning agent is costly and introduces unnecessary latency for simple questions.
* **Decision:** Designed a Multi-Tier Agent routing system (L1 Triage → L2 Incident → L3 Security).
* **Pros:** * **Cost & Performance Optimization:** General IT questions are resolved quickly at L1 without triggering the RAG pipeline.
  * **Security:** High-risk queries are isolated and handled strictly by the L3 Security Agent.
* **Trade-offs:** Increased orchestration complexity within the `agents.py` logic.

### 5. Quality Assurance: LLM-as-a-Judge
* **Context:** We need to ensure that the AI always responds in a specific bilingual format (Priority, Routing, Steps) and does not output dangerous instructions.
* **Decision:** Implemented a final QA Agent (LLM-as-a-Judge) that inspects the draft solution before returning it to the user.
* **Pros:** Guarantees strict adherence to Standard Operating Procedures (SOPs) and effectively blocks hallucinatory or hazardous commands.
* **Trade-offs:** Adds an additional LLM API call, increasing total latency by ~1 second per request. We accepted this trade-off prioritizing accuracy and safety over pure speed.

---

## 日本語版 (Japanese Version)

### 1. 関心の分離：マイクロサービス・アーキテクチャ
* **背景:** エンタープライズ環境において、保守性・拡張性が高く、将来のアップグレードが容易なシステムが求められる。
* **決定:** フロントエンド（Next.js）とバックエンドAPI（FastAPI）を完全に分離し、Dockerでコンテナ化するマイクロサービス構成を採用した。
* **メリット:** * UI層とAI処理層を独立してスケールさせることが可能。
  * 将来、ベクトルDB（ChromaDB）やLLMプロバイダを変更する際も、フロントエンドを改修する必要がない（疎結合）。
* **トレードオフ:** Streamlitなどのモノリス（単一）アプリと比較すると、Docker Composeを必要とするためデプロイの複雑さがわずかに増す。

### 2. 検索戦略：ハイブリッド検索（ベクトル＋キーワード）
* **背景:** ITサポートの問い合わせには、「サーバーが重い」などの意味的な表現と、「INC-5005」「Error 0x80070057」のような完全一致が求められる文字列が混在する。純粋なベクトル検索は後者が苦手である。
* **決定:** **ChromaDB**（ベクトル検索）と **BM25**（キーワード検索）を組み合わせ、**RRF (Reciprocal Rank Fusion)** アルゴリズムで結果を統合するハイブリッド検索を実装した。
* **メリット:** 文脈の理解と、システム固有のIDの完全一致の両方を捕捉でき、検索精度が最大化される。
* **トレードオフ:** 2つの検索インデックスを同時に稼働させるため、メモリ使用量と計算コスト（レイテンシ）がわずかに増加する。

### 3. データプライバシー：決定論的PIIマスキング
* **背景:** 個人情報（PII）を含むインシデントデータを、そのまま外部のLLM APIに送信することは重大なセキュリティリスクとなる。
* **決定:** **Microsoft Presidio**（ローカルのspaCy NLPモデル）を統合し、データがバックエンド環境を出る「前」にマスキング処理を行うアーキテクチャとした。
* **メリット:** * 外部プロバイダへのデータ漏洩リスクがゼロになる。
  * プロンプトでLLMにマスキングを指示するよりも、高速かつ確実（決定論的）に処理できる。
* **トレードオフ:** ローカルNLPモデルを組み込むため、バックエンドのDockerイメージサイズが大きくなる。

### 4. 処理フロー：マルチ・ティアー（多層）エージェントシステム
* **背景:** すべてのユーザーからの質問を、複雑で重い推論エージェントに処理させることは、コストの無駄でありレイテンシの悪化を招く。
* **決定:** L1（トリアージ）、L2（インシデント対応）、L3（セキュリティ）の役割を持たせた多層エージェントルーティングシステムを設計した。
* **メリット:** * **コストと速度の最適化:** 一般的な質問はL1で即座に回答し、不要なRAG検索（APIコール）を節約できる。
  * **安全性:** 高リスクなセキュリティの脅威はL3エージェントに隔離して厳格に対処できる。
* **トレードオフ:** `agents.py` 内の連携ロジックとオーケストレーションが複雑になる。

### 5. 品質保証：LLM-as-a-Judge（AIによる検閲）
* **背景:** AIの回答が、常に指定されたバイリンガルフォーマット（優先度、担当チーム、解決ステップ）を遵守し、危険な操作手順を出力しないことを保証する必要がある。
* **決定:** ユーザーに回答を返す直前に、最終検閲を行うQAエージェント（LLM-as-a-Judge）を配置した。
* **メリット:** 標準作業手順（SOP）の厳格な遵守を保証し、ハルシネーションや有害なコマンドの出力を強力にブロックできる。
* **トレードオフ:** LLMのAPIコールが1回追加されるため、1リクエストあたりのレイテンシが約1秒増加する。しかし、本システムでは「純粋な速度」よりも「エンタープライズ品質の安全性と正確性」を優先し、このトレードオフを受け入れた。