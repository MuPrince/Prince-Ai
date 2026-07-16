package com.prince.agent.service.rag.retrieve.impl;

import com.prince.agent.service.rag.Document;
import com.prince.agent.service.rag.VectorStore;
import com.prince.agent.service.rag.retrieve.Retriever;

import java.util.List;

/**
 * 向量语义召回器
 * 基于 EmbeddingModel 余弦相似度，捕获语义层面的相关性
 */
public class SemanticRetriever implements Retriever {

    private final VectorStore vectorStore;

    public SemanticRetriever(VectorStore vectorStore) {
        this.vectorStore = vectorStore;
    }

    @Override
    public List<Document> retrieve(String query, int topK) {
        return vectorStore.similaritySearch(query, topK);
    }

    @Override
    public String name() {
        return "向量语义召回";
    }
}
