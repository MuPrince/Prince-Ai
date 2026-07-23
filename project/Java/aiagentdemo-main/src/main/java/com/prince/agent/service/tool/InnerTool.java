package com.prince.agent.service.tool;

import org.springframework.ai.tool.ToolCallback;

import java.util.List;

/**
 * 内置工具接口
 * <p>
 * 所有内置工具（简单工具、Skill、RAG、MCP 等）都应实现此接口。
 * 初始化成功后返回一组 ToolCallback，由 AgentBeanConfig 统一收集并注册到 Agent。
 */
public interface InnerTool {

    /**
     * 加载并返回该工具提供的所有 ToolCallback
     * <p>
     * 简单工具通常返回单元素列表，Skill/MCP 等可返回多个。
     */
    List<ToolCallback> loadToolCallbacks();
}
