package com.prince.ai.mcp.server.conf;

import com.prince.ai.mcp.server.tools.WeatherTool;
import org.springframework.ai.tool.ToolCallbackProvider;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 *
 * Description : 工具类注册 <br\>
 * 把工具类写入MCP工具清单
 *
 * @author Mu.Prince <br\>
 * @since 2026/5/14 21:11
 */
//@Configuration
public class ToolsRegister {

    @Bean
    public ToolCallbackProvider getToolCallbackProvider(WeatherTool weatherTool) {
        return MethodToolCallbackProvider.builder().toolObjects(
                weatherTool
        ).build();
    }
}
