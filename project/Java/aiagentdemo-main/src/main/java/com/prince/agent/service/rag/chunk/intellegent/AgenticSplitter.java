package com.prince.agent.service.rag.chunk.intellegent;

import com.prince.agent.service.rag.Document;
import com.prince.agent.service.rag.chunk.ChunkSplitter;
import org.springframework.ai.chat.client.ChatClient;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * 智能体分块器（Agentic Chunking）
 * <p>
 * 让 LLM 作为智能体逐段阅读文档，判断每段内容应该归入当前块还是开始新块。
 * 这是最接近人类分块方式的策略——跨段落的同一主题内容会被合并到一起，
 * 不同主题之间自然分离。
 *
 * <p>算法流程：
 * <ol>
 *   <li>按句子将文本切分为句子列表</li>
 *   <li>初始化第一个块，包含第一个句子</li>
 *   <li>对后续每个句子，让 LLM 判断它与当前块的主题是否一致：
 *     <ul>
 *       <li>一致 → 合并到当前块</li>
 *       <li>不一致 → 保存当前块，开始新块</li>
 *     </ul>
 *   </li>
 *   <li>如果合并后的块超过 maxChunkSize，按句子边界拆分</li>
 * </ol>
 *
 * <p>为减少 LLM 调用次数，采用批量判断策略：每次将多个待判断句子一起发给 LLM，
 * 让 LLM 返回第一个主题不一致的句子编号。
 */
public class AgenticSplitter implements ChunkSplitter {

    /** 句末标点正则 */
    private static final Pattern SENTENCE_END_PATTERN =
            Pattern.compile("(?<=[。！？!?.])");

    /** 每批发送给 LLM 判断的句子数量 */
    private static final int BATCH_SIZE = 5;

    private final ChatClient chatClient;

    /** 单个块的最大字符数 */
    private final int maxChunkSize;

    /**
     * @param chatClient   ChatClient，用于调用 LLM 判断主题一致性
     * @param maxChunkSize 单个块的最大字符数
     */
    public AgenticSplitter(ChatClient chatClient, int maxChunkSize) {
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

        // 1. 按句子切分
        List<String> sentences = splitIntoSentences(text.trim());
        if (sentences.size() <= 1) {
            return List.of(new Document(text.trim(), source, 0));
        }

        System.out.println("  Agentic 分块：共 " + sentences.size() + " 个句子待处理");

        // 2. 让 LLM 逐批判断主题一致性，构建语义分组
        List<List<String>> semanticGroups = buildSemanticGroups(sentences);
        System.out.println("  Agentic 分块：识别出 " + semanticGroups.size() + " 个主题段");

        // 3. 将每组合并为文档块，超长的再拆分
        return buildDocuments(semanticGroups, source);
    }

    /**
     * 按句末标点切分文本为句子列表
     */
    private List<String> splitIntoSentences(String text) {
        String[] rawSentences = SENTENCE_END_PATTERN.split(text);
        List<String> sentences = new ArrayList<>();
        for (String sentence : rawSentences) {
            String trimmed = sentence.trim();
            if (!trimmed.isEmpty()) {
                sentences.add(trimmed);
            }
        }
        return sentences;
    }

    /**
     * 逐批让 LLM 判断句子与当前块的主题一致性，构建语义分组
     */
    private List<List<String>> buildSemanticGroups(List<String> sentences) {
        List<List<String>> groups = new ArrayList<>();
        List<String> currentGroup = new ArrayList<>();
        currentGroup.add(sentences.get(0));

        int index = 1;
        while (index < sentences.size()) {
            // 取一批待判断的句子
            int batchEnd = Math.min(index + BATCH_SIZE, sentences.size());
            List<String> batchSentences = sentences.subList(index, batchEnd);

            // 获取当前块的摘要（取最后几句作为上下文）
            String currentContext = buildCurrentContext(currentGroup);

            // 让 LLM 判断这批句子中第一个主题不一致的位置
            int breakPosition = findBreakPosition(currentContext, batchSentences);

            if (breakPosition == -1) {
                // 整批都与当前主题一致，全部合并
                currentGroup.addAll(batchSentences);
                index = batchEnd;
            } else {
                // 将断裂点之前的句子合并到当前组
                for (int i = 0; i < breakPosition; i++) {
                    currentGroup.add(batchSentences.get(i));
                }
                // 保存当前组，从断裂点开始新组
                groups.add(currentGroup);
                currentGroup = new ArrayList<>();
                currentGroup.add(batchSentences.get(breakPosition));
                index += breakPosition + 1;
            }
        }

        if (!currentGroup.isEmpty()) {
            groups.add(currentGroup);
        }

        return groups;
    }

    /**
     * 构建当前块的上下文摘要（取最后 3 句，避免上下文过长）
     */
    private String buildCurrentContext(List<String> currentGroup) {
        int contextSize = Math.min(3, currentGroup.size());
        List<String> contextSentences = currentGroup.subList(
                currentGroup.size() - contextSize, currentGroup.size());
        return String.join("\n", contextSentences);
    }

    /**
     * 调用 LLM 判断一批句子中第一个与当前主题不一致的位置
     *
     * @param currentContext 当前块的上下文（最后几句）
     * @param batchSentences 待判断的句子列表
     * @return 第一个主题不一致的句子在 batchSentences 中的索引，全部一致返回 -1
     */
    private int findBreakPosition(String currentContext, List<String> batchSentences) {
        StringBuilder sentenceList = new StringBuilder();
        for (int i = 0; i < batchSentences.size(); i++) {
            sentenceList.append(i + 1).append(". ").append(batchSentences.get(i)).append("\n");
        }

        String prompt = "你是一个文档分析助手。请判断以下待分析句子中，哪个句子开始讨论了一个与当前段落不同的新主题。\n\n"
                + "当前段落的最后几句：\n"
                + currentContext + "\n\n"
                + "待分析的句子：\n"
                + sentenceList + "\n"
                + "规则：\n"
                + "1. 如果所有句子都与当前段落讨论同一主题，请回复数字 0\n"
                + "2. 如果某个句子开始讨论新主题，请回复该句子的编号（1-" + batchSentences.size() + "）\n"
                + "3. 只回复一个数字，不要输出任何解释\n\n"
                + "回复：";

        try {
            String rawOutput = chatClient.prompt().user(prompt).call().content();
            int position = parseBreakPosition(rawOutput.trim());
            if (position >= 1 && position <= batchSentences.size()) {
                return position - 1; // 转为 0-based 索引
            }
            return -1; // 0 或无效值表示全部一致
        } catch (Exception exception) {
            System.err.println("警告：Agentic 主题判断失败，默认合并: " + exception.getMessage());
            return -1;
        }
    }

    /**
     * 解析 LLM 返回的断裂位置数字
     */
    private int parseBreakPosition(String rawOutput) {
        // 提取第一个数字
        StringBuilder numberBuilder = new StringBuilder();
        for (char ch : rawOutput.toCharArray()) {
            if (Character.isDigit(ch)) {
                numberBuilder.append(ch);
            } else if (!numberBuilder.isEmpty()) {
                break;
            }
        }
        if (numberBuilder.isEmpty()) {
            return 0;
        }
        try {
            return Integer.parseInt(numberBuilder.toString());
        } catch (NumberFormatException exception) {
            return 0;
        }
    }

    /**
     * 将语义分组转换为 Document 列表
     * 超长的组按句子边界再拆分
     */
    private List<Document> buildDocuments(List<List<String>> semanticGroups, String source) {
        List<Document> documents = new ArrayList<>();
        int chunkIndex = 0;

        for (List<String> group : semanticGroups) {
            String mergedContent = String.join("\n", group);

            if (mergedContent.length() <= maxChunkSize) {
                documents.add(new Document(mergedContent, source, chunkIndex++));
            } else {
                // 超长组按句子边界再拆分
                List<Document> subChunks = splitOversizedGroup(group, source, chunkIndex);
                documents.addAll(subChunks);
                chunkIndex += subChunks.size();
            }
        }

        return documents;
    }

    /**
     * 将超长的语义组按句子边界拆分为多个不超过 maxChunkSize 的块
     */
    private List<Document> splitOversizedGroup(List<String> sentences, String source, int startIndex) {
        List<Document> documents = new ArrayList<>();
        StringBuilder currentChunk = new StringBuilder();
        int chunkIndex = startIndex;

        for (String sentence : sentences) {
            if (!currentChunk.isEmpty()
                    && currentChunk.length() + sentence.length() + 1 > maxChunkSize) {
                documents.add(new Document(currentChunk.toString().trim(), source, chunkIndex++));
                currentChunk = new StringBuilder();
            }
            if (!currentChunk.isEmpty()) {
                currentChunk.append("\n");
            }
            currentChunk.append(sentence);
        }

        if (!currentChunk.isEmpty()) {
            documents.add(new Document(currentChunk.toString().trim(), source, chunkIndex));
        }

        return documents;
    }

    @Override
    public String name() {
        return "Agentic 分块";
    }
}
