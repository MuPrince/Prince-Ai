import os
import numpy as np
from typing import List
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings, HuggingFaceBgeEmbeddings

try:
    import dashscope
    from dashscope import TextEmbedding
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "dashscope")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "nomic-embed-text")

_bge_model = None


def get_embedding_dimension() -> int:
    model_type = EMBEDDING_MODEL.lower()
    if model_type in ["dashscope", "openai"]:
        return 1536
    elif model_type == "ollama":
        return 768
    elif model_type == "bge":
        return 1024
    else:
        return 1536


def compute_embedding(text: str) -> np.ndarray:
    try:
        if EMBEDDING_MODEL.lower() == "dashscope":
            return _compute_dashscope_embedding(text)
        elif EMBEDDING_MODEL.lower() == "openai":
            return _compute_openai_embedding(text)
        elif EMBEDDING_MODEL.lower() == "ollama":
            return _compute_ollama_embedding(text)
        elif EMBEDDING_MODEL.lower() == "bge":
            return _compute_bge_embedding(text)
        else:
            return _compute_dashscope_embedding(text)
    except Exception as e:
        print(f"计算单个文本嵌入失败: {e}")
        dimension = get_embedding_dimension()
        return np.zeros(dimension, dtype=np.float32)


def compute_embeddings(texts: List[str]) -> List[np.ndarray]:
    if not texts:
        return []

    try:
        if EMBEDDING_MODEL.lower() == "dashscope":
            return _compute_dashscope_embeddings(texts)
        elif EMBEDDING_MODEL.lower() == "openai":
            return _compute_openai_embeddings(texts)
        elif EMBEDDING_MODEL.lower() == "ollama":
            return _compute_ollama_embeddings(texts)
        elif EMBEDDING_MODEL.lower() == "bge":
            return _compute_bge_embeddings(texts)
        else:
            return _compute_dashscope_embeddings(texts)
    except Exception as e:
        print(f"批量计算文本嵌入失败: {e}")
        dimension = get_embedding_dimension()
        return [np.zeros(dimension, dtype=np.float32) for _ in texts]


def _compute_dashscope_embedding(text: str) -> np.ndarray:
    if not DASHSCOPE_AVAILABLE:
        raise ImportError("dashscope 未安装，请运行: pip install dashscope")

    if not DASHSCOPE_API_KEY:
        raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")

    dashscope.api_key = DASHSCOPE_API_KEY

    response = TextEmbedding.call(
        model=TextEmbedding.Models.text_embedding_v1,
        input=text
    )

    if response.status_code != 200:
        raise ValueError(f"DashScope API 调用失败: {response.message}")

    embedding = response.output['embeddings'][0]['embedding']
    return np.array(embedding, dtype=np.float32)


def _compute_dashscope_embeddings(texts: List[str]) -> List[np.ndarray]:
    if not DASHSCOPE_AVAILABLE:
        raise ImportError("dashscope 未安装，请运行: pip install dashscope")

    if not DASHSCOPE_API_KEY:
        raise ValueError("DASHSCOPE_API_KEY 环境变量未设置")

    dashscope.api_key = DASHSCOPE_API_KEY

    embeddings = []
    batch_size = 25

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        response = TextEmbedding.call(
            model=TextEmbedding.Models.text_embedding_v1,
            input=batch
        )

        if response.status_code != 200:
            raise ValueError(f"DashScope API 调用失败: {response.message}")

        for item in response.output['embeddings']:
            embedding = item['embedding']
            embeddings.append(np.array(embedding, dtype=np.float32))

    return embeddings


def _compute_openai_embedding(text: str) -> np.ndarray:
    model = OpenAIEmbeddings(
        api_key=OPENAI_API_KEY,
        model="text-embedding-ada-002"
    )
    embedding = model.embed_query(text)
    return np.array(embedding, dtype=np.float32)


def _compute_openai_embeddings(texts: List[str]) -> List[np.ndarray]:
    model = OpenAIEmbeddings(
        api_key=OPENAI_API_KEY,
        model="text-embedding-ada-002"
    )
    embeddings = model.embed_documents(texts)
    return [np.array(emb, dtype=np.float32) for emb in embeddings]


def _compute_ollama_embedding(text: str) -> np.ndarray:
    model = OllamaEmbeddings(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL
    )
    embedding = model.embed_query(text)
    return np.array(embedding, dtype=np.float32)


def _compute_ollama_embeddings(texts: List[str]) -> List[np.ndarray]:
    model = OllamaEmbeddings(
        base_url=OLLAMA_BASE_URL,
        model=OLLAMA_MODEL
    )
    embeddings = model.embed_documents(texts)
    return [np.array(emb, dtype=np.float32) for emb in embeddings]


def _compute_bge_embedding(text: str) -> np.ndarray:
    global _bge_model
    if _bge_model is None:
        _bge_model = HuggingFaceBgeEmbeddings(
            model_name="BAAI/bge-large-zh-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
    embedding = _bge_model.embed_query(text)
    return np.array(embedding, dtype=np.float32)


def _compute_bge_embeddings(texts: List[str]) -> List[np.ndarray]:
    global _bge_model
    if _bge_model is None:
        _bge_model = HuggingFaceBgeEmbeddings(
            model_name="BAAI/bge-large-zh-v1.5",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
    embeddings = _bge_model.embed_documents(texts)
    return [np.array(emb, dtype=np.float32) for emb in embeddings]
