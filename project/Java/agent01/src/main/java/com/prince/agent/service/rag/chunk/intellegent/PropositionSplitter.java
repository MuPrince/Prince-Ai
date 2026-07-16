package com.prince.agent.service.rag.chunk.intellegent;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.prince.agent.service.rag.Document;
import com.prince.agent.service.rag.chunk.ChunkSplitter;
import org.springframework.ai.chat.client.ChatClient;

import java.util.ArrayList;
import java.util.List;

/**
 * 命题分块器（Propositional Chunking）
 * <p>
 * 让 LLM 将文档拆解为独立的命题（Proposition），每个命题是一个自包含的、
 * 可独立理解的事实陈述。相比传统分块，命题分块的检索精度更高，
 * 因为每个块都是一个完整的知识单元。
 *
 * <p>算法流程：
 * <ol>
 *   <li>按段落（双换行）将文本粗切为段落列表</li>
 *   <li>对每个段落调用 LLM，提取其中包含的独立命题</li>
 *   <li>将相邻命题合并到不超过 maxChunkSize 的块中</li>
 * </ol>
 *
 * <p>示例：
 * <pre>
 * 原文："张三是阿里巴巴的工程师，2020年入职，负责搜索推荐系统。"
 * 命题：
 *   - "张三是一名工程师"
 *   - "张三在阿里巴巴工作"
 *   - "张三于2020年入职"
 *   - "张三负责搜索推荐系统"
 * </pre>
 */
public class PropositionSplitter implements ChunkSplitter {

    /** 每次发送给 LLM 的最大段落字符数，防止超出上下文窗口 */
    private static final int MAX_PARAGRAPH_SIZE = 2000;

    private final ChatClient chatClient;

    /** 合并命题后单个块的最大字符数 */
    private final int maxChunkSize;

    /**
     * @param chatClient   ChatClient，用于调用 LLM 提取命题
     * @param maxChunkSize 合并命题后单个块的最大字符数
     */
    public PropositionSplitter(ChatClient chatClient, int maxChunkSize) {
        if (maxChunkSize <= 0) {
            throw new IllegalArgumentException("maxChunkSize 必须大于 0");
        }
        this.chatClient = chatClient;
        this.maxChunkSize = maxChunkSize;
    }

    @Override
    public List<Document> split(String text, String source) {
        if (text == null || text.isBlank()) {
            return new ArrayList<>();
        }

        // 1. 按段落粗切
        List<String> paragraphs = splitIntoParagraphs(text.trim());
        System.out.println("  命题分块：共 " + paragraphs.size() + " 个段落待处理");

        // 2. 对每个段落提取命题
        List<String> allPropositions = new ArrayList<>();
        for (int i = 0; i < paragraphs.size(); i++) {
            String paragraph = paragraphs.get(i);
            List<String> propositions = extractPropositions(paragraph);
            System.out.println("    段落 " + (i + 1) + ": 提取 " + propositions.size() + " 个命题");
            allPropositions.addAll(propositions);
        }

        if (allPropositions.isEmpty()) {
            return List.of(new Document(text.trim(), source, 0));
        }

        // 3. 将命题合并为不超过 maxChunkSize 的块
        return mergePropositions(allPropositions, source);
    }

    /**
     * 按段落（双换行）切分文本
     */
    private List<String> splitIntoParagraphs(String text) {
        List<String> paragraphs = new ArrayList<>();
        for (String segment : text.split("\n\n+")) {
            String trimmed = segment.trim();
            if (!trimmed.isEmpty()) {
                // 超长段落按 MAX_PARAGRAPH_SIZE 再切分，避免超出 LLM 上下文
                if (trimmed.length() > MAX_PARAGRAPH_SIZE) {
                    int start = 0;
                    while (start < trimmed.length()) {
                        int end = Math.min(start + MAX_PARAGRAPH_SIZE, trimmed.length());
                        paragraphs.add(trimmed.substring(start, end));
                        start = end;
                    }
                } else {
                    paragraphs.add(trimmed);
                }
            }
        }
        return paragraphs;
    }

    /**
     * 调用 LLM 从段落中提取独立命题
     * 解析失败时返回原始段落作为兜底
     */
    private List<String> extractPropositions(String paragraph) {
        String prompt = "你是一个专业的知识提取助手。请将以下文本拆解为独立的命题（Proposition）。\n\n"
                + "要求：\n"
                + "1. 每个命题必须是一个完整的、自包含的事实陈述\n"
                + "2. 每个命题应该可以脱离上下文独立理解\n"
                + "3. 将代词替换为具体的实体名称（如\"他\"替换为具体人名）\n"
                + "4. 保留关键的时间、地点、数量等信息\n"
                + "5. 不要遗漏原文中的任何重要信息\n\n"
                + "输出格式：只输出一个 JSON 字符串数组，不要输出任何解释或 markdown 标记。\n"
                + "示例输出：[\"命题1\", \"命题2\", \"命题3\"]\n\n"
                + "原文：\n" + paragraph;

        try {
            String rawOutput = chatClient.prompt().user(prompt).call().content();
            return parseJsonArray(rawOutput, paragraph);
        } catch (Exception exception) {
            System.err.println("警告：命题提取失败，使用原始段落作为兜底: " + exception.getMessage());
            return List.of(paragraph);
        }
    }

    /**
     * 解析 LLM 返回的 JSON 数组
     * 解析失败时返回原始段落作为兜底
     */
    private List<String> parseJsonArray(String rawOutput, String fallbackText) {
        String jsonContent = extractJsonArrayString(rawOutput);
        try {
            JSONArray jsonArray = JSON.parseArray(jsonContent);
            List<String> propositions = new ArrayList<>();
            for (int i = 0; i < jsonArray.size(); i++) {
                String proposition = jsonArray.getString(i);
                if (proposition != null && !proposition.isBlank()) {
                    propositions.add(proposition.trim());
                }
            }
            return propositions.isEmpty() ? List.of(fallbackText) : propositions;
        } catch (Exception parseException) {
            System.err.println("警告：命题 JSON 解析失败，使用原始段落。输出: "
                    + rawOutput.substring(0, Math.min(200, rawOutput.length())));
            return List.of(fallbackText);
        }
    }

    /**
     * 将命题列表合并为不超过 maxChunkSize 的文档块
     */
    private List<Document> mergePropositions(List<String> propositions, String source) {
        List<Document> documents = new ArrayList<>();
        StringBuilder currentChunk = new StringBuilder();
        int chunkIndex = 0;

        for (String proposition : propositions) {
            if (!currentChunk.isEmpty()
                    && currentChunk.length() + proposition.length() + 1 > maxChunkSize) {
                documents.add(new Document(currentChunk.toString().trim(), source, chunkIndex++));
                currentChunk = new StringBuilder();
            }
            if (!currentChunk.isEmpty()) {
                currentChunk.append("\n");
            }
            currentChunk.append(proposition);
        }

        if (!currentChunk.isEmpty()) {
            documents.add(new Document(currentChunk.toString().trim(), source, chunkIndex));
        }

        return documents;
    }

    /**
     * 从模型输出中提取 JSON 数组字符串
     */
    private String extractJsonArrayString(String rawOutput) {
        String trimmed = rawOutput.trim();
        int startIndex = trimmed.indexOf('[');
        int endIndex = trimmed.lastIndexOf(']');
        if (startIndex != -1 && endIndex != -1 && endIndex > startIndex) {
            return trimmed.substring(startIndex, endIndex + 1);
        }
        return trimmed;
    }

    @Override
    public String name() {
        return "命题分块";
    }
}
