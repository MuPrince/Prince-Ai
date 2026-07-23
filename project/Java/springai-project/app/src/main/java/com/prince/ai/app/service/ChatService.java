package com.prince.ai.app.service;

import com.prince.ai.app.entity.dto.ChatRequest;
import org.springframework.http.codec.ServerSentEvent;
import reactor.core.publisher.Flux;

/**
 *
 * Description : 聊天业务 <br\>
 *
 * @author Mu.Prince <br\>
 * @since 2026/7/20 14:00
 */
public interface ChatService {
    /**
     * Description :  聊天
     * @param input 用户输入
     * @return reactor.core.publisher.Mono<java.lang.String>
     * @since 2026/7/20 14:03
     * @author Prince
     */
    Flux<ServerSentEvent<String>> chat(String input, String sessionId);
}
