package com.prince.agent.service.skill;

import org.springframework.core.io.Resource;
import org.springframework.core.io.support.PathMatchingResourcePatternResolver;
import org.springframework.stereotype.Component;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * 技能管理器
 * <p>
 * 扫描 classpath:skill/*.md 文件，自动解析并转换为 ToolCallback。
 * <p>
 * 每个 .md 文件支持两种格式：
 * <p>
 * 简单格式（向后兼容，自动生成单个 input 参数）：
 * <pre>
 * ---
 * name: skill_name
 * description: 技能描述
 * ---
 *
 * Prompt 模板内容，使用 {{input}} 作为用户输入占位符
 * </pre>
 * <p>
 * 多参数格式（支持自定义参数列表）：
 * <pre>
 * ---
 * name: skill_name
 * description: 技能描述
 * parameters:
 *   - name: code
 *     description: 需要审查的代码
 *     required: true
 *   - name: language
 *     description: 编程语言
 *     required: false
 *     default: auto
 * ---
 *
 * Prompt 模板内容，使用 {{code}}、{{language}} 等占位符
 * </pre>
 */
@Component
public class SkillManager {

    private final List<SkillDefinition> skillDefinitions = new ArrayList<>();

    public SkillManager() {
        loadSkills();
    }

    /**
     * 扫描 classpath:skill/ 目录下所有 .md 文件，加载并转换为 ToolCallback 列表
     */
    public void loadSkills() {
        try {
            PathMatchingResourcePatternResolver resolver = new PathMatchingResourcePatternResolver();
            Resource[] resources = resolver.getResources("classpath:skill/*.md");

            for (Resource resource : resources) {
                SkillDefinition definition = parseSkillFile(resource);
                if (definition != null) {
                    skillDefinitions.add(definition);
                    System.out.println("[Skill] 已加载技能: " + definition.name()
                            + "（参数: " + definition.parameters().stream()
                            .map(SkillParameter::name).toList() + "）");
                }
            }
            System.out.println("[Skill] 共加载 " + skillDefinitions.size() + " 个技能");
        } catch (IOException exception) {
            System.err.println("[Skill] 技能加载失败: " + exception.getMessage());
        }
    }

    public List<SkillDefinition> getSkillDefinitions() {
        return skillDefinitions;
    }

    private SkillDefinition parseSkillFile(Resource resource) throws IOException {
        String content = readResource(resource);

        if (!content.startsWith("---")) {
            System.err.println("[Skill] 文件格式错误（缺少 front matter）: " + resource.getFilename());
            return null;
        }

        int endIndex = content.indexOf("---", 3);
        if (endIndex < 0) {
            System.err.println("[Skill] 文件格式错误（front matter 未闭合）: " + resource.getFilename());
            return null;
        }

        String frontMatter = content.substring(3, endIndex).trim();
        String promptTemplate = content.substring(endIndex + 3).trim();

        String name = null;
        String description = null;
        List<SkillParameter> parameters = new ArrayList<>();

        String[] lines = frontMatter.split("\n");
        for (int i = 0; i < lines.length; i++) {
            String line = lines[i].trim();
            if (line.startsWith("name:")) {
                name = line.substring("name:".length()).trim();
            } else if (line.startsWith("description:") && !isInsideParameterBlock(lines, i)) {
                description = line.substring("description:".length()).trim();
            } else if (line.equals("parameters:")) {
                i = parseParameters(lines, i + 1, parameters);
            }
        }

        if (name == null || description == null || promptTemplate.isEmpty()) {
            System.err.println("[Skill] 文件缺少必要字段（name/description/prompt）: " + resource.getFilename());
            return null;
        }

        // 向后兼容：未定义 parameters 时，通过检测模板中是否包含 {{input}} 占位符来判断
        // - 模板包含 {{input}} → 旧格式简单 Skill，自动生成单个 input 参数
        // - 模板不包含 {{input}} 且无 parameters 定义 → 零参数 Skill，无需声明 parameters
        if (parameters.isEmpty() && promptTemplate.contains("{{input}}")) {
            parameters.add(new SkillParameter("input", "需要处理的文本内容", true, null));
        }

        return new SkillDefinition(name, description, promptTemplate, parameters);
    }

    /**
     * 判断当前行的 description 是否属于 parameter 块内部（缩进判断）
     */
    private boolean isInsideParameterBlock(String[] lines, int currentIndex) {
        if (currentIndex == 0) {
            return false;
        }
        String rawLine = lines[currentIndex];
        return rawLine.startsWith("    ") || rawLine.startsWith("\t");
    }

    /**
     * 解析 parameters 块，支持 YAML 列表格式
     *
     * @return 解析结束后的行索引
     */
    private int parseParameters(String[] lines, int startIndex, List<SkillParameter> parameters) {
        String paramName = null;
        String paramDescription = null;
        boolean paramRequired = true;
        String paramDefault = null;

        int i = startIndex;
        for (; i < lines.length; i++) {
            String line = lines[i];
            String trimmed = line.trim();

            // 遇到非缩进行，说明 parameters 块结束
            if (!line.startsWith("  ") && !line.startsWith("\t") && !trimmed.isEmpty()) {
                i--; // 回退一行，让外层循环重新处理
                break;
            }

            if (trimmed.startsWith("- name:")) {
                // 遇到新参数定义前，先保存上一个参数
                if (paramName != null) {
                    parameters.add(new SkillParameter(paramName, paramDescription, paramRequired, paramDefault));
                }
                paramName = trimmed.substring("- name:".length()).trim();
                paramDescription = null;
                paramRequired = true;
                paramDefault = null;
            } else if (trimmed.startsWith("description:")) {
                paramDescription = trimmed.substring("description:".length()).trim();
            } else if (trimmed.startsWith("required:")) {
                paramRequired = Boolean.parseBoolean(trimmed.substring("required:".length()).trim());
            } else if (trimmed.startsWith("default:")) {
                paramDefault = trimmed.substring("default:".length()).trim();
            }
        }

        // 保存最后一个参数
        if (paramName != null) {
            parameters.add(new SkillParameter(paramName, paramDescription, paramRequired, paramDefault));
        }

        return i;
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

    /**
     * 技能参数定义
     *
     * @param name         参数名称，对应 Prompt 模板中的 {{name}} 占位符
     * @param description  参数描述，用于 LLM 理解参数含义
     * @param required     是否必填
     * @param defaultValue 默认值，当参数未传入时使用
     */
    public record SkillParameter(String name, String description, boolean required, String defaultValue) {}

    /**
     * 技能定义
     *
     * @param name           技能名称
     * @param description    技能描述
     * @param promptTemplate Prompt 模板
     * @param parameters     参数列表
     */
    public record SkillDefinition(String name, String description, String promptTemplate,
                                  List<SkillParameter> parameters) {}
}
