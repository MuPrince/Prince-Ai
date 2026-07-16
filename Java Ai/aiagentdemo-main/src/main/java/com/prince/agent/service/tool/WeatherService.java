package com.prince.agent.service.tool;

import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Service;

/**
 *
 * Description : 天气查询 <br\>
 *
 * @author Mu.Prince <br\>
 * @since 2026/7/5 21:41
 */
@Service
public class WeatherService {

    @Tool(description = "Get weather information by city name")
    public String getWeather(@ToolParam(description = "City name") String cityName) {
        return "Sunny in " + cityName;
    }
}
