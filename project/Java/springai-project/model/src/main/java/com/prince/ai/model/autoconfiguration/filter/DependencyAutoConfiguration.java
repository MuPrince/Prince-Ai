package com.prince.ai.model.autoconfiguration.filter;

import org.springframework.boot.autoconfigure.AutoConfigurationImportFilter;
import org.springframework.boot.autoconfigure.AutoConfigurationMetadata;

/**
 *
 * Description : 自动装配类管理自动装配配置类 <br\>
 *
 * @author Mu.Prince <br\>
 * @since 2026/7/23 06:37
 */
public class DependencyAutoConfiguration implements AutoConfigurationImportFilter {

    @Override
    public boolean[] match(String[] autoConfigurationClasses, AutoConfigurationMetadata autoConfigurationMetadata) {
        boolean[] matches = new boolean[autoConfigurationClasses.length];
        for (int i = 0; i < autoConfigurationClasses.length; i++) {
            if (autoConfigurationClasses[i] != null && autoConfigurationClasses[i].startsWith("com.alibaba.cloud.ai.autoconfigure.dashscope.")) {
                System.out.println("排除自动装配类：" + autoConfigurationClasses[i]);
                matches[i] = false;
            } else if (autoConfigurationClasses[i] != null && autoConfigurationClasses[i].startsWith("org.springframework.ai.model.deepseek.autoconfigure.DeepSeekChatAutoConfiguration")) {
                System.out.println("排除自动装配类：" + autoConfigurationClasses[i]);
                matches[i] = false;
            } else if (autoConfigurationClasses[i] != null && autoConfigurationClasses[i].startsWith("org.springframework.ai.model.openai.autoconfigure.")) {
                System.out.println("排除自动装配类：" + autoConfigurationClasses[i]);
                matches[i] = false;
            } else {
                matches[i] = true;
            }
        }
        return matches;
    }
}
