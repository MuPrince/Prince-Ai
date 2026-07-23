package com.prince.ai.model.autoconfiguration.openai;

import io.micrometer.observation.ObservationRegistry;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.observation.AdvisorObservationConvention;
import org.springframework.ai.chat.client.observation.ChatClientObservationConvention;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.model.chat.client.autoconfigure.ChatClientBuilderConfigurer;
import org.springframework.ai.model.chat.client.autoconfigure.ChatClientBuilderProperties;
import org.springframework.ai.openai.OpenAiChatModel;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.core.annotation.Order;

/**
 *
 * Description : Dashscope的ChatClient自动装配类 <br\>
 *
 * @author Mu·Prince
 * @since 2026/3/16 13:12
 */
@AutoConfiguration(
        afterName = "org.springframework.boot.actuate.autoconfigure.observation.ObservationAutoConfiguration")
@ConditionalOnClass(ChatClient.class)
@EnableConfigurationProperties(ChatClientBuilderProperties.class)
@ConditionalOnProperty(prefix = ChatClientBuilderProperties.CONFIG_PREFIX, name = "enabled", havingValue = "true",
        matchIfMissing = true)
public class OpenAiChatClientAutoConfiguration {

    @Bean
    @Order(2)
    @ConditionalOnBean(OpenAiChatModel.class)
    ChatClient.Builder openAiChatClientBuilder(ChatClientBuilderConfigurer chatClientBuilderConfigurer, @Qualifier("openAiChatModel") ChatModel chatModel,
                                         ObjectProvider<ObservationRegistry> observationRegistry,
                                         ObjectProvider<ChatClientObservationConvention> chatClientObservationConvention,
                                         ObjectProvider<AdvisorObservationConvention> advisorObservationConvention) {
        ChatClient.Builder builder = ChatClient.builder(chatModel,
                observationRegistry.getIfUnique(() -> ObservationRegistry.NOOP),
                chatClientObservationConvention.getIfUnique(() -> null),
                advisorObservationConvention.getIfUnique(() -> null));
        return chatClientBuilderConfigurer.configure(builder);
    }
}
