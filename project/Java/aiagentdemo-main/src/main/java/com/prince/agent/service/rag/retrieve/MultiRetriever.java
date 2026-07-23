package com.prince.agent.service.rag.retrieve;

import com.prince.agent.service.rag.Document;

import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 多路召回融合器
 * <p>
 * 接收多个 Recaller 实现，对每个 Recaller 的召回结果使用
 * RRF（Reciprocal Rank Fusion）算法进行融合排序，
 * 去重后返回综合排名最高的候选文档块。
 *
 * <p>RRF 融合公式：score(d) = Σ 1 / (k + rank_i(d))，其中 k=60 为平滑常数
 */
public class MultiRetriever implements Retriever {

    /** RRF 平滑常数，防止排名靠前的文档分数过于悬殊 */
    private static final int RRF_K = 60;

    /** 每路召回的候选数量 */
    private static final int PER_ROUTE_CANDIDATE_COUNT = 10;

    private final List<Retriever> retrievers;

    public MultiRetriever(List<Retriever> retrievers) {
        this.retrievers = retrievers;
    }

    /**
     * 执行多路召回，返回 RRF 融合后的候选文档列表
     *
     * @param query 用户查询问题
     * @param topK  最终返回的候选文档数量
     * @return 经 RRF 融合排序后的候选文档列表
     */
    public List<Document> retrieve(String query, int topK) {
        Map<String, Double> rrfScores = new HashMap<>();
        Map<String, Document> keyToDocument = new LinkedHashMap<>();

        for (Retriever retriever : retrievers) {
            System.out.println("\n--- " + retriever.name() + " ---");
            List<Document> results = retriever.retrieve(query, PER_ROUTE_CANDIDATE_COUNT);
            System.out.println("  召回 " + results.size() + " 个候选");
            accumulateRrfScores(results, rrfScores, keyToDocument);
        }

        List<Document> mergedResults = rrfScores.entrySet().stream()
                .sorted(Map.Entry.<String, Double>comparingByValue().reversed())
                .limit(topK)
                .map(entry -> keyToDocument.get(entry.getKey()))
                .toList();

        System.out.println("\n  多路召回融合后共 " + mergedResults.size() + " 个候选（去重后）");
        return mergedResults;
    }

    @Override
    public String name() {
        return "多路召回";
    }

    /**
     * 将一路召回结果的 RRF 分数累加到总分数表中
     * 排名从 1 开始，第 rank 名的贡献分数为 1 / (RRF_K + rank)
     */
    private void accumulateRrfScores(
            List<Document> rankedDocuments,
            Map<String, Double> rrfScores,
            Map<String, Document> keyToDocument) {

        for (int rank = 0; rank < rankedDocuments.size(); rank++) {
            Document document = rankedDocuments.get(rank);
            String uniqueKey = document.getSource() + "::" + document.getChunkIndex();
            double rrfContribution = 1.0 / (RRF_K + rank + 1);
            rrfScores.merge(uniqueKey, rrfContribution, Double::sum);
            keyToDocument.putIfAbsent(uniqueKey, document);
        }
    }
}
