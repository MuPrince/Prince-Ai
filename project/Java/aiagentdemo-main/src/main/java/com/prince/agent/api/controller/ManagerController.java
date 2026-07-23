package com.prince.agent.api.controller;

import com.prince.agent.core.AgentCore;
import com.prince.agent.core.ModelConfig;
import com.prince.agent.api.controller.dto.ChatResponse;
import com.prince.agent.api.controller.dto.McpConnectRequest;
import com.prince.agent.api.controller.dto.SwitchModelRequest;
import com.prince.agent.service.extrenal.McpClient;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 配置管理接口
 * <p>
 * 统一管理 Agent 的配置操作：清空记忆、切换模型、MCP 服务增删查。
 */
@RestController
@RequestMapping(value = "/api/manage", produces = MediaType.APPLICATION_JSON_VALUE)
public class ManagerController {

    private final AgentCore agentCore;
    private final McpClient mcpClient;

    public ManagerController(AgentCore agentCore, McpClient mcpClient) {
        this.agentCore = agentCore;
        this.mcpClient = mcpClient;
    }

    // ========== 对话管理 ==========

    /**
     * 清空指定会话的对话历史
     */
    @PostMapping("/clear-memory")
    public ChatResponse clearMemory(@RequestBody(required = false) Map<String, String> request) {
        String sessionId = "default";
        if (request != null && request.get("sessionId") != null && !request.get("sessionId").isBlank()) {
            sessionId = request.get("sessionId");
        }
        agentCore.clearMemory(sessionId);
        return ChatResponse.ok("对话历史已清空");
    }

    /**
     * 运行时切换模型
     */
    @PostMapping("/switch-model")
    public ChatResponse switchModel(@RequestBody SwitchModelRequest request) {
        if (request.getBaseUrl() == null || request.getApiKey() == null || request.getChatModel() == null) {
            return ChatResponse.fail("baseUrl、apiKey、chatModel 不能为空");
        }

        try {
            ModelConfig modelConfig = new ModelConfig(
                    request.getBaseUrl(),
                    request.getApiKey(),
                    request.getChatModel(),
                    request.getEmbeddingModel(),
                    request.getCompletionsPath(),
                    request.getEmbeddingsPath()
            );
            agentCore.switchModel(modelConfig);
            return ChatResponse.ok("已切换到: " + modelConfig);
        } catch (Exception exception) {
            return ChatResponse.fail("切换失败: " + exception.getMessage());
        }
    }

    // ========== 模型参数管理 ==========

    /**
     * 获取当前模型推理参数
     */
    @GetMapping("/model-params")
    public Map<String, Object> getModelParams() {
        return Map.of(
                "temperature", agentCore.getTemperature(),
                "maxTokens", agentCore.getMaxTokens(),
                "topP", agentCore.getTopP()
        );
    }

    /**
     * 调整模型推理参数
     * <p>
     * 支持的参数：temperature（0.0~2.0）、maxTokens（正整数）、topP（0.0~1.0）
     */
    @PostMapping("/model-params")
    public ChatResponse updateModelParams(@RequestBody Map<String, Object> request) {
        try {
            Double temperature = request.containsKey("temperature")
                    ? ((Number) request.get("temperature")).doubleValue() : null;
            Integer maxTokens = request.containsKey("maxTokens")
                    ? ((Number) request.get("maxTokens")).intValue() : null;
            Double topP = request.containsKey("topP")
                    ? ((Number) request.get("topP")).doubleValue() : null;

            agentCore.setModelParams(temperature, maxTokens, topP);

            return ChatResponse.ok("模型参数已更新: temperature=" + agentCore.getTemperature()
                    + ", maxTokens=" + agentCore.getMaxTokens()
                    + ", topP=" + agentCore.getTopP());
        } catch (Exception exception) {
            return ChatResponse.fail("参数更新失败: " + exception.getMessage());
        }
    }

    // ========== MCP 服务管理 ==========

    /**
     * 连接 MCP 服务
     */
    @PostMapping("/mcp/connect")
    public ChatResponse connectMcp(@RequestBody McpConnectRequest request) {
        if (request.getUrl() == null || request.getUrl().isBlank()) {
            return ChatResponse.fail("MCP 服务 URL 不能为空");
        }

        try {
            ToolCallback[] mcpCallbacks = mcpClient.connect(request.getUrl());
            agentCore.registerToolCallbacks(mcpCallbacks);
            return ChatResponse.ok("已连接: " + request.getUrl());
        } catch (Exception exception) {
            return ChatResponse.fail("连接失败: " + exception.getMessage());
        }
    }

    /**
     * 断开 MCP 服务
     */
    @PostMapping("/mcp/disconnect")
    public ChatResponse disconnectMcp(@RequestBody McpConnectRequest request) {
        if (request.getUrl() == null || request.getUrl().isBlank()) {
            return ChatResponse.fail("MCP 服务 URL 不能为空");
        }

        try {
            List<ToolCallback> removedCallbacks = mcpClient.disconnect(request.getUrl());
            agentCore.removeToolCallbacks(removedCallbacks);
            return ChatResponse.ok("已断开: " + request.getUrl());
        } catch (Exception exception) {
            return ChatResponse.fail("断开失败: " + exception.getMessage());
        }
    }

    /**
     * 获取所有 MCP 服务列表
     */
    @GetMapping("/mcp/list")
    public List<McpClient.McpServerInfo> listMcpServers() {
        mcpClient.getToolCallbacks();
        return mcpClient.getAllServers();
    }
}
