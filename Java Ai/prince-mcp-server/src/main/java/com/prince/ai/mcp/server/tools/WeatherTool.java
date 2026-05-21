package com.prince.ai.mcp.server.tools;

import io.modelcontextprotocol.server.McpSyncServerExchange;
import io.modelcontextprotocol.spec.McpSchema;
import org.springaicommunity.mcp.annotation.McpProgressToken;
import org.springaicommunity.mcp.annotation.McpTool;
import org.springaicommunity.mcp.annotation.McpToolParam;
import org.springframework.stereotype.Component;

/**
 *
 * Description : 天气工具类 <br\>
 *
 * @author Mu.Prince <br\>
 * @since 2026/5/14 21:00
 */
@Component
public class WeatherTool {

    @McpTool(name = "temperature", description = "获取指定城市的温度")
    public String getTemperature(@McpToolParam String city, @McpProgressToken String token, McpSyncServerExchange exchange) {

        // 处理进度
        if (token != null) {
            exchange.progressNotification(
                    new McpSchema.ProgressNotification(
                            token, 0.5, 1.0, "正在查询"
                    )
            );
            exchange.progressNotification(
                    new McpSchema.ProgressNotification(
                            token, 0.9, 1.0, "准备返回数据"
                    )
            );
        }
        return city;
    }

    @McpTool(name = "ultraviolet", description = "获取指定城市的紫外线光照")
    public String getUltraviolet(@McpToolParam String ultraviolet, @McpProgressToken String token, McpSyncServerExchange exchange) {

        return ultraviolet;
    }
}
