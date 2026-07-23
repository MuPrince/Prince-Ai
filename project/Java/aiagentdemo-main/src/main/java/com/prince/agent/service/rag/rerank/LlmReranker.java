package com.prince.agent.service.rag.rerank;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.prince.agent.service.rag.Document;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

/**
 * 基于专用 Rerank 模型的文档重排器
 * <p>
 * 调用智谱 Rerank API（/rerank 端点），使用专门的重排模型计算候选文档与查询的相关性分数，
 * 按分数降序重排，取前 topK 个最相关的文档块。
 * <p>
 * 相比使用通用 LLM 打分，专用 Rerank 模型速度更快、成本更低、排序质量更高。
 */
public class LlmReranker {

    /** HTTP 请求超时时间 */
    private static final Duration REQUEST_TIMEOUT = Duration.ofSeconds(30);

    private final String rerankUrl;
    private final String rerankModel;
    private final String apiKey;
    private final HttpClient httpClient;

    /**
     * @param baseUrl    API 基础 URL（如 https://open.bigmodel.cn/api/paas/v4）
     * @param apiKey     API 密钥
     * @param rerankPath Rerank API 路径后缀（如 /rerank）
     * @param rerankModel Rerank 模型名称（如 rerank）
     */
    public LlmReranker(String baseUrl, String apiKey, String rerankPath, String rerankModel) {
        this.rerankUrl = baseUrl + rerankPath;
        this.rerankModel = rerankModel;
        this.apiKey = apiKey;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(REQUEST_TIMEOUT)
                .build();
    }

    /**
     * 对候选文档块进行重排，返回最相关的 topK 个文档
     *
     * @param query      用户查询问题
     * @param candidates 多路召回的候选文档块列表
     * @param topK       重排后保留的文档数量
     * @return 按相关性降序排列的 topK 个文档
     */
    public List<Document> rerank(String query, List<Document> candidates, int topK) {
        if (candidates.isEmpty()) {
            return new ArrayList<>();
        }

        try {
            return callRerankApi(query, candidates, topK);
        } catch (Exception exception) {
            System.err.println("警告：Rerank API 调用失败，使用原始召回顺序: " + exception.getMessage());
            return candidates.stream().limit(topK).toList();
        }
    }

    /**
     * 调用智谱 Rerank API
     * <p>
     * 请求格式：
     * <pre>
     * {
     *   "model": "rerank",
     *   "query": "用户问题",
     *   "top_n": 3,
     *   "documents": ["文档1内容", "文档2内容", ...]
     * }
     * </pre>
     * <p>
     * 响应格式：
     * <pre>
     * {
     *   "results": [
     *     {"index": 1, "relevance_score": 0.998},
     *     {"index": 0, "relevance_score": 0.512}
     *   ]
     * }
     * </pre>
     */
    private List<Document> callRerankApi(String query, List<Document> candidates, int topK)
            throws Exception {

        // 构建请求体
        JSONObject requestBody = new JSONObject();
        requestBody.put("model", rerankModel);
        requestBody.put("query", truncateText(query, 4096));
        requestBody.put("top_n", topK);

        JSONArray documentsArray = new JSONArray();
        for (Document candidate : candidates) {
            documentsArray.add(truncateText(candidate.getContent(), 4096));
        }
        requestBody.put("documents", documentsArray);

        // 发送 HTTP 请求
        HttpRequest httpRequest = HttpRequest.newBuilder()
                .uri(URI.create(rerankUrl))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + apiKey)
                .timeout(REQUEST_TIMEOUT)
                .POST(HttpRequest.BodyPublishers.ofString(requestBody.toJSONString()))
                .build();

        System.out.println("  调用 Rerank API: " + rerankUrl);
        HttpResponse<String> httpResponse = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());

        if (httpResponse.statusCode() != 200) {
            throw new RuntimeException("Rerank API 返回异常状态码: " + httpResponse.statusCode()
                    + ", 响应: " + httpResponse.body().substring(0, Math.min(200, httpResponse.body().length())));
        }

        return parseRerankResponse(httpResponse.body(), candidates, topK);
    }

    /**
     * 解析 Rerank API 响应，按 relevance_score 降序取 topK 个文档
     */
    private List<Document> parseRerankResponse(String responseBody, List<Document> candidates, int topK) {
        JSONObject responseJson = JSON.parseObject(responseBody);
        JSONArray results = responseJson.getJSONArray("results");

        if (results == null || results.isEmpty()) {
            System.err.println("警告：Rerank API 返回空结果，使用原始召回顺序");
            return candidates.stream().limit(topK).toList();
        }

        List<ScoredDocument> scoredDocuments = new ArrayList<>();
        for (int i = 0; i < results.size(); i++) {
            JSONObject result = results.getJSONObject(i);
            int documentIndex = result.getIntValue("index");
            double relevanceScore = result.getDoubleValue("relevance_score");

            if (documentIndex >= 0 && documentIndex < candidates.size()) {
                scoredDocuments.add(new ScoredDocument(candidates.get(documentIndex), relevanceScore));
                System.out.println("    文档 " + documentIndex + " 相关性: "
                        + String.format("%.4f", relevanceScore));
            }
        }

        return scoredDocuments.stream()
                .sorted(Comparator.comparingDouble(ScoredDocument::score).reversed())
                .limit(topK)
                .map(ScoredDocument::document)
                .toList();
    }

    /**
     * 截断文本到指定最大长度（Rerank API 限制 query 和 document 最大 4096 字符）
     */
    private String truncateText(String text, int maxLength) {
        if (text.length() <= maxLength) {
            return text;
        }
        return text.substring(0, maxLength);
    }

    /** 带相关性分数的文档 */
    private record ScoredDocument(Document document, double score) {}
}
