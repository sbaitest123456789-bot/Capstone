# ベースイメージ
FROM python:3.10-slim

# 作業ディレクトリの設定
WORKDIR /app

# 必要なパッケージをインストールするためのシステム要件を追加
# (RustとC++コンパイラをインストールし、後で削除してイメージを軽量に保ちます)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && export PATH="$HOME/.cargo/bin:$PATH" \
    && pip install --upgrade pip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Rustのパスを通す
ENV PATH="/root/.cargo/bin:${PATH}"

# 要件ファイルのコピー
COPY requirements.txt .

# 依存関係のインストール
RUN pip install --no-cache-dir -r requirements.txt

# spaCyのモデルをダウンロード
RUN python -m spacy download ja_core_news_sm
RUN python -m spacy download en_core_web_sm

# ソースコードのコピー
COPY . .

# アプリケーションの実行
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]