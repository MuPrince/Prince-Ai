package com.prince.agent.service.command;

import org.springframework.core.io.Resource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 命令管理器
 * <p>
 * 扫描 classpath:command/*.md 文件，加载为用户可直接调用的快捷命令。
 * Command 与 Skill 的区别：Command 不是工具（不注册为 ToolCallback），
 * 而是用户通过 /命令名 直接调用的 Prompt 模板。
 * <p>
 * .md 文件格式：纯 Prompt 模板，文件名即命令名，使用 {{input}} 作为用户输入占位符。
 */
@Component
public class CommandManager {

    private final List<CommandDefinition> commandDefinitions = new ArrayList<>();

    public CommandManager() {
        loadCommands();
    }

    private void loadCommands() {
        try {
            PathMatchingResourcePatternResolver resolver = new PathMatchingResourcePatternResolver();
            Resource[] resources = resolver.getResources("classpath:command/*.md");

            for (Resource resource : resources) {
                String fileName = resource.getFilename();
                if (fileName == null || !fileName.endsWith(".md")) {
                    continue;
                }

                String name = fileName.substring(0, fileName.length() - 3);
                String promptTemplate = readResource(resource).trim();

                if (!promptTemplate.isEmpty()) {
                    commandDefinitions.add(new CommandDefinition(name, promptTemplate));
                    System.out.println("[Command] 已加载命令: /" + name);
                }
            }
            System.out.println("[Command] 共加载 " + commandDefinitions.size() + " 个命令");
        } catch (IOException exception) {
            System.err.println("[Command] 命令加载失败: " + exception.getMessage());
        }
    }

    /**
     * 获取所有已加载的命令定义
     */
    public List<CommandDefinition> getCommandDefinitions() {
        return Collections.unmodifiableList(commandDefinitions);
    }

    /**
     * 根据命令名查找命令定义
     */
    public CommandDefinition findByName(String name) {
        return commandDefinitions.stream()
                .filter(cmd -> cmd.name().equals(name))
                .findFirst()
                .orElse(null);
    }

    /**
     * 将命令模板中的 {{input}} 替换为用户输入，生成最终 Prompt
     */
    public String buildPrompt(CommandDefinition command, String input) {
        return command.promptTemplate().replace("{{input}}", input);
    }

    private String readResource(Resource resource) throws IOException {
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8))) {
            StringBuilder builder = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) {
                builder.append(line).append("\n");
            }
            return builder.toString();
        }
    }

    public record CommandDefinition(String name, String promptTemplate) {
    }
}
