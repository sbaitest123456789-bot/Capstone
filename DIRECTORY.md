# Project Directory Structure

## English Version
```text
INCIDENT-ASSISTANT/
├── .env                        # API keys and LangSmith environment variables
├── .gitignore                  # Git ignore rules
├── Dockerfile                  # Backend Docker configuration
├── README.md                   # Project documentation (Japanese)
├── README_en.md                # Project documentation (English)
├── DIRECTORY.md                # This file (Project structure guide)
├── agents.py                   # Core AI logic (PII masking, Guardrails, Multi-tier agents)
├── docker-compose.yml          # Container orchestration (Frontend & Backend)
├── evaluate_solution.py        # DeepEval automated quality metrics
├── ingest.py                   # Data ingestion script to ChromaDB
├── main.py                     # FastAPI entry point (App setup & Router inclusion)
├── models.py                   # Pydantic data models for request/response
├── requirements.txt            # Python dependencies
├── test_main.py                # Automated API validation (pytest)
│
├── routers/                    # API Route Handlers
│   ├── __init__.py             # Package initializer
│   ├── feedback.py             # Endpoint for user feedback (👍/👎)
│   └── search.py               # Endpoint for incident search & resolution
│
├── chroma_db/                  # Vector Database storage (ChromaDB)
│   ├── (collection_data)       # Indexed vector data
│   └── chroma.sqlite3          # Metadata storage
│
├── data/                       # Raw dataset for RAG
│   └── incident_response_data.xlsx
│
├── frontend/                   # Next.js Application
│   ├── app/
│   │   ├── globals.css         # Global styling
│   │   ├── layout.tsx          # App layout template
│   │   └── page.tsx            # Main UI for Incident Intelligence Base
│   ├── Dockerfile              # Frontend Docker configuration
│   └── (others)                # Node.js configuration files
│
└── feedback_log.csv            # Stored user feedback data (Generated at runtime)
```

---

## 日本語版 (Japanese Version)
```text
INCIDENT-ASSISTANT/
├── .env                        # APIキーおよびLangSmith環境変数
├── .gitignore                  # Git管理除外ルール
├── Dockerfile                  # バックエンドDocker設定ファイル
├── README.md                   # プロジェクト説明ドキュメント (日本語)
├── README_en.md                # プロジェクト説明ドキュメント (英語)
├── DIRECTORY.md                # 本ファイル (ディレクトリ構成ガイド)
├── agents.py                   # AIコアロジック (PII匿名化、ガードレール、マルチエージェント)
├── docker-compose.yml          # コンテナ一括管理設定 (Frontend & Backend)
├── evaluate_solution.py        # DeepEvalによる回答品質の自動評価スクリプト
├── ingest.py                   # 初期データをChromaDBへ取り込むスクリプト
├── main.py                     # FastAPIエントリーポイント (ルーターの統合と起動)
├── models.py                   # Pydanticデータモデル (リクエスト/レスポンスの定義)
├── requirements.txt            # Python依存ライブラリ一覧
├── test_main.py                # pytestによるAPI動作の自動検証スクリプト
│
├── routers/                    # APIエンドポイント定義
│   ├── __init__.py             # パッケージ初期化ファイル
│   ├── feedback.py             # ユーザー評価 (👍/👎) 受付用エンドポイント
│   └── search.py               # インシデント検索・解決策生成用エンドポイント
│
├── chroma_db/                  # ベクトルデータベース保存先
│   ├── (collection_data)       # インデックス化されたベクトルデータ
│   └── chroma.sqlite3          # メタデータ管理用DB
│
├── data/                       # RAG用原材料データ
│   └── incident_response_data.xlsx
│
├── frontend/                   # Next.js アプリケーション (フロントエンド)
│   ├── app/
│   │   ├── globals.css         # 全体スタイル定義
│   │   ├── layout.tsx          # 共通レイアウトテンプレート
│   │   └── page.tsx            # メインUI画面 (Incident Intelligence Base)
│   ├── Dockerfile              # フロントエンドDocker設定ファイル
│   └── (others)                # Node.js設定ファイル群
│
└── feedback_log.csv            # 蓄積されたユーザーフィードバックデータ (実行時に生成)
```