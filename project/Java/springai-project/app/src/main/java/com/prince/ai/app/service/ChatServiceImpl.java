package com.prince.ai.app.service;

import com.alibaba.cloud.ai.dashscope.chat.DashScopeChatOptions;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;

/**
 *
 * Description : 聊天业务实现 <br\>
 *
 * @author Mu.Prince <br\>
 * @since 2026/7/20 14:00
 */
@Service
public class ChatServiceImpl implements ChatService {

    private final ChatClient chatClient;

    public ChatServiceImpl(ChatClient.Builder chatClientBuilder) {
        this.chatClient = chatClientBuilder
                .defaultSystem("你是一个友善的智能客服")
                .defaultOptions(DashScopeChatOptions.builder()
                        .topP(0.7)
                        .build())
                .build();
    }

    @Override
    public Flux<ServerSentEvent<String>> chat(String input, String sessionId) {
        return chatClient.prompt().user(input).stream().content()
                .map(reply -> ServerSentEvent.<String>builder(reply).build());

//        return Flux.empty();
//        Flux<ChatResponse> stream = dashScopeChatModel.stream(new Prompt(new UserMessage(input)));
//        System.out.println(stream);
//        return stream.map(response -> ServerSentEvent.<String>builder().data(response.getResult().getOutput().getText()).build());
    }

}
