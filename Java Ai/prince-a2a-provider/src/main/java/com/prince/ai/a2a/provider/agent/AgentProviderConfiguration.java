package com.prince.ai.a2a.provider.agent;

import com.alibaba.cloud.ai.graph.agent.ReactAgent;
import com.prince.ai.a2a.provider.tools.WeatherTool;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.tool.function.FunctionToolCallback;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 *
 * Description :  <br\>
 *
 * @author Mu.Prince <br\>
 * @since 2026/5/14 23:07
 */
@Configuration
public class AgentProviderConfiguration {

//    @Value("${spring.ai.dashscope.api-key}")
//    public String key;

//    @Bean
//    public ChatModel chatModel() {
//        // 初始化 ChatModel
//        DashScopeApi dashScopeApi = DashScopeApi.builder()
//                .apiKey(key)
//                .build();
//
//        return DashScopeChatModel.builder()
//                .dashScopeApi(dashScopeApi)
//                .build();
//    }

    @Bean
    public ReactAgent agentProvider(WeatherTool weatherTool, ChatModel chatModel) {
        FunctionToolCallback<String, String> toolCallback = FunctionToolCallback.builder("get_weather", weatherTool::getTemperature)
                .description("获取指定城市的天气信息")
                .inputType(String.class)
                .build();
        return ReactAgent.builder()
                .name("AgentProvider")
                .model(chatModel)
                .tools(toolCallback)
                .build();
    }
}
