import os
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "knowledge_base")

_collection = None


def get_milvus_connection():
    try:
        connections.connect(host=MILVUS_HOST, port=MILVUS_PORT)
        return True
    except Exception as e:
        print(f"连接 Milvus 失败: {e}")
        return False


def close_milvus_connection():
    try:
        connections.disconnect("default")
    except Exception:
        pass


def create_collection():
    if not get_milvus_connection():
        return None

    try:
        if utility.has_collection(MILVUS_COLLECTION_NAME, using="default"):
            return Collection(MILVUS_COLLECTION_NAME)

        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="chunk_index", dtype=DataType.INT64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1536)
        ]

        schema = CollectionSchema(fields=fields, description="知识库向量数据库")
        collection = Collection(name=MILVUS_COLLECTION_NAME, schema=schema)

        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="embedding", index_params=index_params)

        return collection

    except Exception as e:
        print(f"创建 Collection 失败: {e}")
        return None


def get_collection():
    global _collection

    if _collection is not None:
        return _collection

    if not get_milvus_connection():
        return None

    try:
        if utility.has_collection(MILVUS_COLLECTION_NAME, using="default"):
            _collection = Collection(MILVUS_COLLECTION_NAME)
            _collection.load()
            return _collection
        else:
            return create_collection()
    except Exception as e:
        print(f"获取 Collection 失败: {e}")
        return None


def insert_chunks(file_name: str, chunks: list, embeddings: list):
    collection = get_collection()
    if collection is None:
        return False

    try:
        data = [
            [chunk for chunk in chunks],
            [file_name] * len(chunks),
            list(range(len(chunks))),
            [emb.tolist() if hasattr(emb, 'tolist') else list(emb) for emb in embeddings]
        ]

        result = collection.insert(data)
        collection.flush()
        return True

    except Exception as e:
        print(f"插入数据失败: {e}")
        return False


def search_vectors(query_embedding: list, top_k: int = 5):
    collection = get_collection()
    if collection is None:
        return []

    try:
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["chunk_text", "file_name", "chunk_index"]
        )

        search_results = []
        for hits in results:
            for hit in hits:
                search_results.append({
                    "chunk_text": hit.entity.get("chunk_text"),
                    "file_name": hit.entity.get("file_name"),
                    "chunk_index": hit.entity.get("chunk_index"),
                    "distance": hit.distance
                })

        return search_results

    except Exception as e:
        print(f"搜索失败: {e}")
        return []
