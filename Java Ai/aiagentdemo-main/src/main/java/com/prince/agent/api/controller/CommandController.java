package com.prince.agent.api.controller;

import com.prince.agent.service.command.CommandManager;
import com.prince.agent.service.command.CommandManager.CommandDefinition;
import com.prince.agent.core.AgentCore;
import com.prince.agent.api.controller.dto.ChatResponse;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;

import java.util.List;
import java.util.Map;

/**
 * Command 命令接口
 * <p>
 * 提供命令列表查询和命令执行能力。
 * 用户在前端输入 / 时可唤起命令列表，选择后执行对应 Prompt。
 */
@RestController
@RequestMapping("/api/command")
public class CommandController {

    private final CommandManager commandManager;
    private final AgentCore agentCore;

    public CommandController(CommandManager commandManager, AgentCore agentCore) {
        this.commandManager = commandManager;
        this.agentCore = agentCore;
    }

    /**
     * 获取所有可用命令列表
     */
    @GetMapping("/list")
    public List<String> listCommands() {
        return commandManager.getCommandDefinitions().stream()
                .map(CommandDefinition::name)
                .toList();
    }

    /**
     * 执行指定命令（非流式）
     */
    @PostMapping("/execute")
    public ChatResponse executeCommand(@RequestBody Map<String, String> request) {
        String name = request.get("name");
        String input = request.getOrDefault("input", "");
        String sessionId = resolveSessionId(request.get("sessionId"));

        if (name == null || name.isBlank()) {
            return ChatResponse.fail("命令名不能为空");
        }

        CommandDefinition command = commandManager.findByName(name);
        if (command == null) {
            return ChatResponse.fail("未找到命令: /" + name);
        }

        try {
            String prompt = commandManager.buildPrompt(command, input);
            String reply = agentCore.chat(sessionId, prompt);
            return ChatResponse.ok(reply);
        } catch (Exception exception) {
            return ChatResponse.fail("命令执行失败: " + exception.getMessage());
        }
    }

    /**
     * 执行指定命令（流式 SSE）
     */
    @PostMapping(value = "/execute/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> executeCommandStream(@RequestBody Map<String, String> request) {
        String name = request.get("name");
        String input = request.getOrDefault("input", "");
        String sessionId = resolveSessionId(request.get("sessionId"));

        if (name == null || name.isBlank()) {
            return Flux.just(ServerSentEvent.<String>builder().data("[ERROR] 命令名不能为空").build());
        }

        CommandDefinition command = commandManager.findByName(name);
        if (command == null) {
            return Flux.just(ServerSentEvent.<String>builder().data("[ERROR] 未找到命令: /" + name).build());
        }

        String prompt = commandManager.buildPrompt(command, input);
        return agentCore.chatStream(sessionId, prompt)
                .map(token -> ServerSentEvent.<String>builder()
                        .data(token.replace("\n", "\\n"))
                        .build());
    }

    private String resolveSessionId(String sessionId) {
        return (sessionId != null && !sessionId.isBlank()) ? sessionId : "default";
    }
}
