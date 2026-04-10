#!/usr/bin/env python3
"""查询 ChromaDB 存储的记忆数据，用于 PPT 截图展示（直接读取本地文件）"""

import chromadb

# 直接读取用户数据库文件
db_path = "/Users/xuzi/Downloads/AI_Dialogue/Server/data/users/811f3290-bab6-4b9b-8fa7-91ad91868c0d/chroma_db"
client = chromadb.PersistentClient(path=db_path)

print("=" * 60)
print("ChromaDB 数据查询结果")
print("=" * 60)

# 列出所有 collections
collections = client.list_collections()
print(f"\n共 {len(collections)} 个 Collection：\n")
for col in collections:
    print(f"  · {col.name}")

print()

# 逐个查看每个 collection 的数据
for col in collections:
    print("-" * 60)
    print(f"Collection: {col.name}")
    print("-" * 60)
    data = col.get(limit=3)
    if not data['documents']:
        print("  (暂无数据)")
    else:
        for i, (doc_text, uid) in enumerate(zip(data['documents'], data['ids'])):
            meta = data.get('metadatas', [{}] * len(data['documents']))[i]
            print(f"\n  [{i+1}] ID: {uid[:50]}...")
            print(f"      内容: {doc_text[:120]}{'...' if len(doc_text) > 120 else ''}")
            if meta:
                tags = meta.get('tags', '')
                if tags:
                    print(f"      标签: {tags}")
    print()

print("=" * 60)
