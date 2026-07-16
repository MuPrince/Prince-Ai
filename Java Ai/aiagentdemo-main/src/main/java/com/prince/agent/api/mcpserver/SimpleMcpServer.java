package com.prince.agent.api.mcpserver;

import com.prince.agent.service.rag.RagService;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Component;

/**
 * MCP Server 工具：知识库查询
 * <p>
 * 对外提供知识库检索能力的 MCP 服务。
 * MCP 客户端通过 tools/call 调用此工具，传入结构化参数进行知识库检索。
 */
@Component
public class SimpleMcpServer {

    private final RagService ragService;

    public SimpleMcpServer(RagService ragService) {
        this.ragService = ragService;
    }

    @Tool(name = "knowledge_query", description = "查询内部知识库，根据关键词和分类检索相关技术文档内容")
    public String knowledgeQuery(
            @ToolParam(description = "检索关键词，如：HashMap、Spring Boot 自动配置、线程池") String keyword,
            @ToolParam(description = "知识分类，可选值：java_basic（Java基础）、jvm（JVM）、concurrent（并发）、spring（Spring框架）、design_pattern（设计模式）、all（全部），默认 all") String category,
            @ToolParam(description = "返回的最大结果条数，默认 3") int maxResults
    ) {
        if (keyword == null || keyword.isBlank()) {
            return "错误：检索关键词不能为空";
        }

        if (!ragService.isKnowledgeLoaded()) {
            return "错误：知识库尚未加载";
        }

        // 格式化查询：将结构化参数组装为检索语句
        String formattedQuery = buildFormattedQuery(keyword, category);

        String result = ragService.query(formattedQuery);

        if (result == null || result.isBlank()) {
            return "未找到与关键词 \"" + keyword + "\" 相关的知识库内容";
        }

        return result;
    }

    private String buildFormattedQuery(String keyword, String category) {
        String categoryLabel = switch (category != null ? category.toLowerCase() : "all") {
            case "java_basic" -> "Java 基础";
            case "jvm" -> "JVM 虚拟机";
            case "concurrent" -> "多线程与并发";
            case "spring" -> "Spring 框架";
            case "design_pattern" -> "设计模式";
            default -> "";
        };

        if (categoryLabel.isEmpty()) {
            return keyword;
        }

        return categoryLabel + " " + keyword;
    }
}
