package com.prince.agent.config;

import com.prince.agent.service.tool.WeatherService;
import org.springframework.ai.tool.ToolCallbackProvider;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 *
 * Description : MCP-nacos配置 <br\>
 *
 * @author Mu.Prince <br\>
 * @since 2026/7/5 21:38
 */
//@Configuration
public class ToolCallbackConfiguration {

    @Bean
    public ToolCallbackProvider weatherTools(WeatherService weatherService) {
        return MethodToolCallbackProvider.builder().toolObjects(weatherService).build();
    }
}
