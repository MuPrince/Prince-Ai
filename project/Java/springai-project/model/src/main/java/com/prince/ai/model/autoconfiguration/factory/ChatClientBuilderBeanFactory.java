package com.prince.ai.model.autoconfiguration.factory;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.beans.factory.NoSuchBeanDefinitionException;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

import java.util.List;

/**
 *
 * Description : ChatClient.Builder Bean工厂，用于注入时自动选择注入的Bean实例 <br\>
 *
 * @author Mu·Prince
 * @since 2026/3/16 14:45
 */
@Configuration
public class ChatClientBuilderBeanFactory {


    @Bean
    @Primary
    @ConditionalOnBean(ChatClient.Builder.class)
    ChatClient.Builder chatClientBuilderFactory(List<ChatClient.Builder> builders) {
        return builders.get(0);
    }
}
