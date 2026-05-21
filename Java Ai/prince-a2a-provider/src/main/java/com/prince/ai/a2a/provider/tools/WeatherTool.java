package com.prince.ai.a2a.provider.tools;

import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
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

    @Tool(name = "temperature", description = "获取指定城市的温度")
    public String getTemperature(@ToolParam String city) {
        return city;
    }
}
