package com.prince.agent.service.rag.retrieve;

import com.prince.agent.service.rag.Document;
import java.util.List;

/**
 * 召回器接口
 * 每种召回策略实现此接口，由 MultiRecaller 统一编排和 RRF 融合
 */
public interface Retriever {
    /**
     * 执行召回
     * @param query 用户查询
     * @param topK 返回的最大文档数
     * @return 按相关性降序排列的文档列表
     */
    List<Document> retrieve(String query, int topK);

    /** 召回器名称，用于日志输出 */
    String name();
}
