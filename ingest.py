import pandas as pd
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
import os
import shutil
from dotenv import load_dotenv

load_dotenv()

# 新しいCSVファイルの読み込み
# Loading a New CSV File
file_path = 'data/incident_response_dataset_with_urgency_impact - Incident Data.csv'
df = pd.read_csv(file_path)

documents = []
metadatas = []

for index, row in df.iterrows():
    # 1. ベクトル化するテキスト（メタデータ以外のすべての要素を結合）
    # 1. Text to be vectorized (combining all elements excluding metadata)
    text = (
        f"Media Asset: {row['Media Asset']}\n"
        f"Ticket ID: {row['Ticket ID']}\n"
        f"Incident ID: {row['Incident ID']}\n"
        f"Incident Details: {row['Incident Details']}\n"
        f"Description: {row['Description']}\n"
        f"Solution: {row['Solution']}"
    )
    documents.append(text)
    
    # 2. メタデータ（フィルター・リランキング用）
    # ※検索結果のUI表示ですぐに使えるよう、Solutionもメタデータとして持たせておきます
    # 2. Metadata (for Filtering and Re-ranking)
    # * We also include the 'Solution' as metadata so that it can be used immediately for displaying search results in the UI.
    metadatas.append({
        "Category": str(row["Category"]),
        "Urgency": str(row["Urgency"]),
        "Impact": str(row["Impact"]),
        "Solution": str(row["Solution"])
    })

# 既存の古いデータベース（フォルダ）がある場合は削除してクリーンな状態にする
# If an existing legacy database (folder) is present, delete it to ensure a clean state.
db_dir = "./chroma_db"
if os.path.exists(db_dir):
    shutil.rmtree(db_dir)
    print(f"古い {db_dir} を削除しました。")
#   print(f"Deleted old {db_dir}.")

# ChromaDBの初期化と保存
# Initializing and Saving ChromaDB
print("新しいデータをベクトル化して保存しています...")
# print("Vectorizing and saving new data...")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vectorstore = Chroma.from_texts(
    texts=documents,
    metadatas=metadatas,
    embedding=embeddings,
    persist_directory=db_dir,
    collection_name="incidents"
)

print(f"完了！合計 {len(documents)} 件のインシデントデータをChromaDBに保存しました。")
# print(f"Complete! A total of {len(documents)} incident records have been saved to ChromaDB.")