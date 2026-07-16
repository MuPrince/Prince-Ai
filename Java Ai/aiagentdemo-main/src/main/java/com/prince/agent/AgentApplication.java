package com.prince.agent;

import com.prince.agent.api.controller.ChatController;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

/**
 * AI Agent 应用入口
 * <p>
 * 串联所有模块：RAG（知识库检索）、Function Calling（工具调用）、Skill（技能）、MCP（远程工具协议）。
 * <p>
 * 启动后提供：
 * <ul>
 *   <li>HTTP API：POST /api/chat（对话）、POST /api/chat/clear（清空历史）、POST /api/chat/switch-model（切换模型）</li>
 *   <li>MCP Server（SSE 端点，通过 Spring AI 自动配置）</li>
 * </ul>
 *
 * @see ChatController HTTP 接口
 */
@SpringBootApplication
public class AgentApplication {

    @Bean(name = "chatClient")
    public ChatClient chatClient(ChatClient.Builder chatClientBuilder) {
        return chatClientBuilder.build();

    }

    public static void main(String[] args) {
        SpringApplication.run(AgentApplication.class, args);
    }
}
