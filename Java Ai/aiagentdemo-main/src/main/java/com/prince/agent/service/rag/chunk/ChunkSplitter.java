package com.prince.agent.service.rag.chunk;

import com.prince.agent.service.rag.Document;
import java.util.List;

/**
 * 文档分块策略接口
 * 不同的分块策略实现此接口，由 RagService 统一调用
 */
public interface ChunkSplitter {
    /**
     * 将文本分块
     * @param text 原始文档文本
     * @param source 文档来源标识（如文件名）
     * @return 分块后的文档列表
     */
    List<Document> split(String text, String source);

    /** 分块策略名称，用于日志输出 */
    String name();
}
