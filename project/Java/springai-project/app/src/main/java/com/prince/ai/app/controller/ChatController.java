package com.prince.ai.app.controller;

import com.prince.ai.app.entity.dto.ChatRequest;
import com.prince.ai.app.service.ChatService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

/**
 *
 * Description : 聊天接口 <br\>
 *
 * @author Mu.Prince <br\>
 * @since 2026/7/20 13:38
 */
@RestController
@RequestMapping("api/chat")
@RequiredArgsConstructor
public class ChatController {

    private final ChatService chatService;

    @PostMapping("stream")
    public Flux<ServerSentEvent<String>> chat(@RequestBody ChatRequest input) {

        if (input.getMessage() == null || input.getMessage().isBlank()) {
            return Flux.just(ServerSentEvent.<String>builder().data("[ERROR] 消息不能为空").build());
        }
        String sessionId = resolveSessionId(input.getSessionId());

        System.out.println(input.getMessage());

        return chatService.chat(input.getMessage(), sessionId);
    }

    /**
     * 解析 sessionId，未传时生成默认值
     */
    private String resolveSessionId(String sessionId) {
        return (sessionId != null && !sessionId.isBlank()) ? sessionId : "default";
    }
}
