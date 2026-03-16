# AI-Powered Incident Knowledge Base Assistant

## Overview
ITサポートチームのトリアージ業務とナレッジ検索を自動化する、AI駆動型のインシデント解決アシスタントです。
ユーザーから自然言語で入力されたトラブル事象に対し、過去のインシデントデータから最適な解決策を検索し、優先度の判定と適切な担当チームへのルーティングを自律的に行います。

## Key Features (Basic Requirements Completed)
- **Hybrid Search (Semantic + Keyword)**
  - ChromaDB (ベクトル検索) による文脈理解と、BM25 (キーワード完全一致) を組み合わせた RRF (Reciprocal Rank Fusion) アルゴリズムを実装。エラーコードや特定サーバー名の検索精度を極限まで高めています。
- **Autonomous Triage Agent**
  - プロンプト内でSOP（標準作業手順）を厳格に定義したLLMエージェントが、過去の事例と現在の事象を比較推論し、優先度 (High/Medium/Low) と対応チームを自動決定します。
- **Data Privacy Guardrails**
  - LLMのFew-shotプロンプティングを活用し、検索実行前にユーザー入力からPII（氏名、IPアドレス、メールアドレス等）を高精度に検出・マスキングします。
- **Modern Microservices Architecture**
  - Next.js (Frontend) と FastAPI (Backend) を完全に分離し、Dockerコンテナとして統合したスケーラブルな設計です。

## Tech Stack
- Frontend: Next.js, React, Tailwind CSS
- Backend: FastAPI, Python
- AI / LLM: OpenAI (gpt-3.5-turbo, text-embedding-3-small), LangChain
- Vector Database: ChromaDB
- Keyword Search: rank_bm25
- Infrastructure: Docker, Docker Compose

## Project Setup (How to run)

### Prerequisites
- Docker および Docker Compose がインストールされていること
- OpenAI API Key が取得済みであること

### Installation Steps

1. プロジェクトのルートディレクトリに .env ファイルを作成し、以下の内容を記述します。
OPENAI_API_KEY=your_openai_api_key_here

2. Dockerコンテナをビルドして起動します。
docker compose up --build

3. 起動完了後、ブラウザで以下のURLにアクセスします。
- Frontend UI: http://localhost:3000
- Backend API Docs (Swagger): http://localhost:8000/docs

## Sample Usage

本システムの実力を最大限に確認できるテストクエリです。ブラウザのUIから以下の文章を入力し、「Generate Solution」をクリックしてください。

**Test Query:**
> 田中さんのPCから、MediaServer05のCPU使用率が異常に高くなっています。INC-5005の事例と同じでしょうか？

**Expected System Behavior:**
1. Guardrail: 「田中さん」が [MASKED_NAME] に自動変換され、PIIが保護されます。
2. Hybrid Search: MediaServer05 と INC-5005 (BM25によるキーワード一致) ＋ CPU使用率が高い (ChromaDBによる意味検索) により、ピンポイントで該当事例を抽出します。
3. Triage & Routing: 過去の対応履歴と運用ルールに基づき、AIが「優先度: Medium または High」「アサイン先: L2DB・ストレージチーム」などを自動判定し、最適な解決ステップ（パラメータの最適化と再起動など）を提示します。

## Future Work (Advanced Concepts)
- Rerank by incident recency and resolution success rate
- Custom metrics (Resolution time prediction)
- LLM-as-judge for troubleshooting step validation