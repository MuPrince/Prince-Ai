package com.prince.agent.service.rag;

import org.springframework.ai.embedding.EmbeddingModel;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.Collections;
import java.util.List;

/**
 * 内存向量存储，使用 Spring AI EmbeddingModel 生成向量，通过余弦相似度检索最相关的文档
 */
public class VectorStore {

    private final EmbeddingModel embeddingModel;

    /** 存储所有文档及其对应的向量 */
    private final List<DocumentWithVector> documentVectors = new ArrayList<>();

    /** 存储所有文档（供 BM25 等外部召回器使用） */
    private final List<Document> documents = new ArrayList<>();

    public VectorStore(EmbeddingModel embeddingModel) {
        this.embeddingModel = embeddingModel;
    }

    /**
     * 将文档列表向量化并存入内存
     *
     * @param newDocuments 待存储的文档列表
     */
    public void addDocuments(List<Document> newDocuments) {
        System.out.println("正在向量化 " + newDocuments.size() + " 个文档块...");
        for (Document document : newDocuments) {
            double[] vector = embed(document.getContent());
            documentVectors.add(new DocumentWithVector(document, vector));
            this.documents.add(document);
            System.out.println("  已处理: [" + document.getSource() + "] chunk-" + document.getChunkIndex());
        }
        System.out.println("向量化完成，共存储 " + documentVectors.size() + " 个文档块。\n");
    }

    /**
     * 获取所有已存储的文档（不可变视图）
     *
     * @return 文档列表的不可变视图
     */
    public List<Document> getDocuments() {
        return Collections.unmodifiableList(documents);
    }

    /**
     * 检索与查询最相关的 topK 个文档
     *
     * @param query 用户查询文本
     * @param topK  返回的最大文档数量
     * @return 按相似度降序排列的文档列表
     */
    public List<Document> similaritySearch(String query, int topK) {
        double[] queryVector = embed(query);

        return documentVectors.stream()
                .map(docVec -> new ScoredDocument(docVec.document, cosineSimilarity(queryVector, docVec.vector)))
                .sorted(Comparator.comparingDouble(ScoredDocument::score).reversed())
                .limit(topK)
                .map(ScoredDocument::document)
                .toList();
    }

    /**
     * 调用 Spring AI EmbeddingModel 将文本转换为向量
     */
    private double[] embed(String text) {
        float[] floatEmbedding = embeddingModel.embed(text);
        double[] embedding = new double[floatEmbedding.length];
        for (int i = 0; i < floatEmbedding.length; i++) {
            embedding[i] = floatEmbedding[i];
        }
        return embedding;
    }

    /**
     * 计算两个向量的余弦相似度
     */
    private double cosineSimilarity(double[] vectorA, double[] vectorB) {
        double dotProduct = 0.0;
        double normA = 0.0;
        double normB = 0.0;

        for (int i = 0; i < vectorA.length; i++) {
            dotProduct += vectorA[i] * vectorB[i];
            normA += vectorA[i] * vectorA[i];
            normB += vectorB[i] * vectorB[i];
        }

        double denominator = Math.sqrt(normA) * Math.sqrt(normB);
        if (denominator == 0) {
            return 0.0;
        }
        return dotProduct / denominator;
    }

    /** 文档与向量的组合 */
    private record DocumentWithVector(Document document, double[] vector) {}

    /** 带相似度分数的文档 */
    private record ScoredDocument(Document document, double score) {}
}
