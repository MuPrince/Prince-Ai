package com.prince.agent.service.rag.retrieve.impl;

import com.prince.agent.service.rag.Document;
import com.prince.agent.service.rag.VectorStore;
import com.prince.agent.service.rag.retrieve.Retriever;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;

/**
 * BM25 关键词召回器
 * 基于 BM25 算法的关键词匹配，捕获精确关键词匹配
 */
public class Bm25Retriever implements Retriever {

    private final VectorStore vectorStore;

    public Bm25Retriever(VectorStore vectorStore) {
        this.vectorStore = vectorStore;
    }

    @Override
    public List<Document> retrieve(String query, int topK) {
        List<Document> documents = vectorStore.getDocuments();
        if (documents.isEmpty()) {
            return new ArrayList<>();
        }

        // BM25 超参数：k1 控制词频饱和度，b 控制文档长度归一化程度
        final double k1 = 1.5;
        final double b = 0.75;

        // 对查询分词（按非中文字符和空格切分，保留中文字符）
        List<String> queryTerms = tokenize(query);
        if (queryTerms.isEmpty()) {
            return new ArrayList<>();
        }

        int totalDocumentCount = documents.size();

        // 计算所有文档的平均长度（以词数衡量）
        double averageDocumentLength = documents.stream()
                .mapToInt(doc -> tokenize(doc.getContent()).size())
                .average()
                .orElse(1.0);

        // 预计算每个词在多少篇文档中出现（用于 IDF 计算）
        Map<String, Integer> termDocumentFrequency = new HashMap<>();
        for (Document document : documents) {
            List<String> docTerms = tokenize(document.getContent());
            // 每篇文档中每个词只计一次
            for (String term : new HashSet<>(docTerms)) {
                termDocumentFrequency.merge(term, 1, Integer::sum);
            }
        }

        // 对每篇文档计算 BM25 分数
        List<ScoredDocument> scoredDocuments = new ArrayList<>();
        for (Document document : documents) {
            List<String> docTerms = tokenize(document.getContent());
            int documentLength = docTerms.size();

            // 统计文档中每个词的出现次数
            Map<String, Long> termFrequencyInDoc = new HashMap<>();
            for (String term : docTerms) {
                termFrequencyInDoc.merge(term, 1L, Long::sum);
            }

            double bm25Score = 0.0;
            for (String queryTerm : queryTerms) {
                long termFrequency = termFrequencyInDoc.getOrDefault(queryTerm, 0L);
                if (termFrequency == 0) {
                    continue;
                }

                int documentFrequency = termDocumentFrequency.getOrDefault(queryTerm, 0);
                // IDF：逆文档频率，词越稀有分数越高
                double idf = Math.log((totalDocumentCount - documentFrequency + 0.5)
                        / (documentFrequency + 0.5) + 1.0);
                // TF 归一化：考虑词频饱和度和文档长度
                double normalizedTf = (termFrequency * (k1 + 1))
                        / (termFrequency + k1 * (1 - b + b * documentLength / averageDocumentLength));

                bm25Score += idf * normalizedTf;
            }

            if (bm25Score > 0) {
                scoredDocuments.add(new ScoredDocument(document, bm25Score));
            }
        }

        return scoredDocuments.stream()
                .sorted(Comparator.comparingDouble(ScoredDocument::score).reversed())
                .limit(topK)
                .map(ScoredDocument::document)
                .toList();
    }

    /**
     * 对文本进行简单分词：按空白字符切分英文，逐字符切分中文
     * 过滤掉长度为 1 的单字符英文词和标点符号
     */
    private List<String> tokenize(String text) {
        List<String> terms = new ArrayList<>();
        // 先按空白和标点切分
        String[] rawTokens = text.toLowerCase().split("[\\s\\p{Punct}]+");
        for (String token : rawTokens) {
            if (token.isEmpty()) {
                continue;
            }
            // 判断是否包含中文字符
            boolean containsChinese = token.chars().anyMatch(ch -> Character.UnicodeScript.of(ch) == Character.UnicodeScript.HAN);
            if (containsChinese) {
                // 中文逐字切分
                for (char ch : token.toCharArray()) {
                    String charStr = String.valueOf(ch);
                    if (!charStr.isBlank()) {
                        terms.add(charStr);
                    }
                }
            } else {
                // 英文过滤掉单字符（通常是无意义的字母）
                if (token.length() > 1) {
                    terms.add(token);
                }
            }
        }
        return terms;
    }

    @Override
    public String name() {
        return "BM25 关键词召回";
    }

    /** 带相似度分数的文档 */
    private record ScoredDocument(Document document, double score) {}
}
