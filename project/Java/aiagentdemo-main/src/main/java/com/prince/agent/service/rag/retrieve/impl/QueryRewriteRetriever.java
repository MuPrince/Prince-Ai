package com.prince.agent.service.rag.retrieve.impl;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.prince.agent.service.rag.Document;
import com.prince.agent.service.rag.VectorStore;
import com.prince.agent.service.rag.retrieve.Retriever;
import org.springframework.ai.chat.client.ChatClient;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 问题改写召回器
 * 让 ChatClient 将问题改写为多种表达，分别做向量召回，扩大语义覆盖面
 */
public class QueryRewriteRetriever implements Retriever {

    /** 每路召回的候选数量 */
    private static final int PER_ROUTE_CANDIDATE_COUNT = 10;

    /** 问题改写的数量 */
    private static final int QUERY_REWRITE_COUNT = 3;

    private final VectorStore vectorStore;
    private final ChatClient chatClient;

    public QueryRewriteRetriever(VectorStore vectorStore, ChatClient chatClient) {
        this.vectorStore = vectorStore;
        this.chatClient = chatClient;
    }

    @Override
    public List<Document> retrieve(String query, int topK) {
        return rewriteAndRecall(query);
    }

    /**
     * 问题改写召回
     * 让 GLM-5 将原始问题改写为 QUERY_REWRITE_COUNT 种不同表达，
     * 对每种改写分别做向量召回，合并所有结果
     */
    private List<Document> rewriteAndRecall(String originalQuery) {
        List<String> rewrittenQueries = rewriteQuery(originalQuery);
        System.out.println("  改写后的问题：");
        for (int i = 0; i < rewrittenQueries.size(); i++) {
            System.out.println("    [" + (i + 1) + "] " + rewrittenQueries.get(i));
        }

        // 用唯一键去重，保留首次出现的文档
        Map<String, Document> uniqueDocuments = new LinkedHashMap<>();
        for (String rewrittenQuery : rewrittenQueries) {
            List<Document> results = vectorStore.similaritySearch(rewrittenQuery, PER_ROUTE_CANDIDATE_COUNT);
            for (Document document : results) {
                String uniqueKey = buildUniqueKey(document);
                uniqueDocuments.putIfAbsent(uniqueKey, document);
            }
        }

        return new ArrayList<>(uniqueDocuments.values());
    }

    /**
     * 调用 ChatClient 将用户问题改写为多种不同表达
     *
     * @param originalQuery 原始用户问题
     * @return 改写后的问题列表（不含原始问题）
     */
    private List<String> rewriteQuery(String originalQuery) {
        String prompt = "你是一个专业的信息检索助手。请将以下用户问题改写为 " + QUERY_REWRITE_COUNT + " 种不同的表达方式，"
                + "以便从不同角度检索相关文档。\n\n"
                + "改写要求：\n"
                + "1. 每种改写应使用不同的词汇和句式，但保持原始问题的核心意图\n"
                + "2. 可以尝试：同义词替换、问题角度转换、关键词提取、扩展相关概念等方式\n"
                + "3. 每种改写应简洁明确，适合作为检索查询\n\n"
                + "输出格式要求：\n"
                + "只输出一个 JSON 数组，数组中每个元素是一个改写后的问题字符串。\n"
                + "不要输出任何解释、说明或 markdown 代码块标记，只输出纯 JSON 数组。\n\n"
                + "示例输出格式：\n"
                + "[\"改写问题1\", \"改写问题2\", \"改写问题3\"]\n\n"
                + "原始问题：" + originalQuery;

        String rawOutput = chatClient.prompt().user(prompt).call().content();
        return parseRewrittenQueries(rawOutput);
    }

    /**
     * 解析模型返回的改写问题 JSON 数组
     * 解析失败时返回空列表（兜底策略，不影响其他两路召回）
     */
    private List<String> parseRewrittenQueries(String rawOutput) {
        String jsonContent = extractJsonArray(rawOutput);
        try {
            JSONArray jsonArray = JSON.parseArray(jsonContent);
            List<String> queries = new ArrayList<>();
            for (int i = 0; i < jsonArray.size(); i++) {
                String rewrittenQuery = jsonArray.getString(i);
                if (rewrittenQuery != null && !rewrittenQuery.isBlank()) {
                    queries.add(rewrittenQuery.trim());
                }
            }
            return queries;
        } catch (Exception parseException) {
            System.err.println("警告：问题改写结果解析失败，跳过改写召回。原始输出: "
                    + rawOutput.substring(0, Math.min(200, rawOutput.length())));
            return new ArrayList<>();
        }
    }

    /**
     * 构造文档的唯一键，用于去重
     */
    private String buildUniqueKey(Document document) {
        return document.getSource() + "::" + document.getChunkIndex();
    }

    /**
     * 从模型输出中提取 JSON 数组字符串
     */
    private String extractJsonArray(String rawOutput) {
        String trimmed = rawOutput.trim();
        int startIndex = trimmed.indexOf('[');
        int endIndex = trimmed.lastIndexOf(']');
        if (startIndex != -1 && endIndex != -1 && endIndex > startIndex) {
            return trimmed.substring(startIndex, endIndex + 1);
        }
        return trimmed;
    }

    @Override
    public String name() {
        return "问题改写召回";
    }
}
