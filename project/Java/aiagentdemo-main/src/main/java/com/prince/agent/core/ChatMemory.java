package com.prince.agent.core;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.MessageType;
import org.springframework.ai.chat.messages.SystemMessage;
import org.springframework.ai.chat.messages.UserMessage;
import org.springframework.ai.chat.prompt.Prompt;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 对话记忆管理器
 * <p>
 * 维护对话历史，支持滑动窗口裁剪和摘要压缩，防止上下文超出模型限制。
 * system 消息始终保留在最前面，不受窗口裁剪影响。
 * <p>
 * 由于大模型回复通常较长，为节省上下文空间，仅保留最近 N 条 Assistant 回复，
 * 更早的 Assistant 消息会被裁剪掉。
 * <p>
 * 当历史消息数超过阈值时，自动将较早的消息通过 LLM 总结为摘要，
 * 注入到 system prompt 中，在不丢失历史信息的前提下减少 token 占用。
 */
public class ChatMemory {

    /** 主 Agent 默认最大历史轮数 */
    private static final int MAIN_AGENT_MAX_ROUNDS = 20;
    /** 主 Agent 默认最多保留的 Assistant 回复条数 */
    private static final int MAIN_AGENT_MAX_ASSISTANT = 3;
    /** SubAgent 默认最大历史轮数 */
    private static final int SUB_AGENT_MAX_ROUNDS = 10;
    /** SubAgent 默认最多保留的 Assistant 回复条数 */
    private static final int SUB_AGENT_MAX_ASSISTANT = 3;

    /** 触发摘要压缩的消息数阈值（超过此值时压缩较早的消息） */
    private static final int COMPRESS_THRESHOLD_MESSAGES = 15;
    /** 压缩后保留的最近消息条数 */
    private static final int PRESERVE_RECENT_MESSAGES = 5;

    private final int maxRounds;
    /** 最多保留的 Assistant 回复条数（大模型回复通常较长，需要限制数量） */
    private final int maxAssistantMessages;
    /** 用于摘要压缩的 ChatClient（可为 null，为 null 时不启用摘要压缩） */
    private final ChatClient chatClient;
    private SystemMessage systemMessage;
    private final List<Message> history = new ArrayList<>();
    /** 历史对话摘要（由内部 SummaryCompressor 生成） */
    private String summaryText;

    private ChatMemory(int maxRounds, int maxAssistantMessages, ChatClient chatClient) {
        this.maxRounds = maxRounds;
        this.maxAssistantMessages = maxAssistantMessages;
        this.chatClient = chatClient;
    }

    /**
     * 为主 Agent 创建对话记忆（历史 20 轮，Assistant 回复最多保留 3 条，启用摘要压缩）
     */
    public static ChatMemory forMainAgent(ChatClient chatClient) {
        return new ChatMemory(MAIN_AGENT_MAX_ROUNDS, MAIN_AGENT_MAX_ASSISTANT, chatClient);
    }

    /**
     * 为 SubAgent 创建对话记忆（历史 10 轮，Assistant 回复最多保留 3 条，不启用摘要压缩）
     */
    public static ChatMemory forSubAgent() {
        return new ChatMemory(SUB_AGENT_MAX_ROUNDS, SUB_AGENT_MAX_ASSISTANT, null);
    }

    public void setSystemPrompt(String systemPrompt) {
        this.systemMessage = new SystemMessage(systemPrompt);
    }

    public void addMessage(Message message) {
        history.add(message);
        trimHistory();
    }

    public void addMessages(List<Message> messages) {
        history.addAll(messages);
        trimHistory();
    }

    /**
     * 获取用于构建 Prompt 的消息列表
     * <p>
     * 在返回消息之前，会自动判断是否需要摘要压缩。
     * 如果历史消息数超过阈值且 chatClient 可用，将自动压缩较早的消息为摘要。
     */
    public List<Message> getMessages() {
        // 在构建消息列表之前，自动尝试摘要压缩
        compressIfNeeded();

        List<Message> messages = new ArrayList<>();

        // 将原始 system prompt 与摘要合并为一条 SystemMessage
        if (systemMessage != null || (summaryText != null && !summaryText.isBlank())) {
            String systemContent = systemMessage != null ? systemMessage.getText() : "";
            if (summaryText != null && !summaryText.isBlank()) {
                systemContent += "\n\n【以下是之前对话的摘要，请参考】\n" + summaryText;
            }
            messages.add(new SystemMessage(systemContent));
        }

        // 统计 history 中 Assistant 消息的总数
        long assistantCount = history.stream()
                .filter(msg -> msg.getMessageType() == MessageType.ASSISTANT)
                .count();

        // 需要跳过的 Assistant 消息数量（只保留最近 maxAssistantMessages 条）
        long skipCount = Math.max(0, assistantCount - maxAssistantMessages);
        long skipped = 0;

        for (Message msg : history) {
            if (msg.getMessageType() == MessageType.ASSISTANT && skipped < skipCount) {
                skipped++;
                continue;
            }
            messages.add(msg);
        }

        return Collections.unmodifiableList(messages);
    }

    /**
     * 自动判断并执行摘要压缩
     * <p>
     * 当历史消息数超过阈值时，将较早的消息通过 LLM 总结为摘要，
     * 然后从 history 中移除已压缩的消息，仅保留最近的若干条。
     */
    private void compressIfNeeded() {
        if (chatClient == null || history.size() <= COMPRESS_THRESHOLD_MESSAGES) {
            return;
        }

        // 计算需要压缩的消息范围：保留最近 PRESERVE_RECENT_MESSAGES 条，其余压缩
        int compressEndIndex = history.size() - PRESERVE_RECENT_MESSAGES;

        // 确保不会在 TOOL 消息的前面截断（TOOL 消息必须紧跟在对应的 ASSISTANT 消息后面）
        while (compressEndIndex < history.size()
                && history.get(compressEndIndex).getMessageType() == MessageType.TOOL) {
            compressEndIndex--;
        }

        if (compressEndIndex <= 0) {
            return;
        }

        List<Message> messagesToCompress = new ArrayList<>(history.subList(0, compressEndIndex));

        // 调用内部压缩器生成摘要
        String newSummary = SummaryCompressor.compress(chatClient, messagesToCompress, summaryText);
        if (newSummary != null && !newSummary.isBlank()) {
            this.summaryText = newSummary;
            history.subList(0, compressEndIndex).clear();
            System.out.println("[ChatMemory] 摘要压缩完成，压缩了 " + messagesToCompress.size()
                    + " 条消息，剩余 " + history.size() + " 条");
        }
    }

    public void clear() {
        history.clear();
        summaryText = null;
    }

    private void trimHistory() {
        int maxMessages = maxRounds * 4;
        if (history.size() <= maxMessages) {
            return;
        }

        int removeCount = history.size() - maxMessages;
        int actualRemoveCount = 0;
        for (int i = 0; i < removeCount && i < history.size(); i++) {
            MessageType nextType = (i + 1 < history.size()) ? history.get(i + 1).getMessageType() : null;
            if (MessageType.TOOL == nextType) {
                continue;
            }
            actualRemoveCount = i + 1;
        }

        if (actualRemoveCount > 0) {
            history.subList(0, actualRemoveCount).clear();
        }
    }

    /**
     * 对话摘要压缩器（内部类）
     * <p>
     * 将一段历史对话消息通过 LLM 总结为简洁的摘要文本，
     * 用于在不完全丢失历史信息的前提下大幅减少上下文 token 占用。
     */
    private static class SummaryCompressor {

        private static final String SUMMARIZE_PROMPT =
                "请将以下对话历史总结为一段简洁的摘要。\n"
                        + "要求：\n"
                        + "1. 保留关键信息：用户的核心需求、重要决策、已完成的操作、关键结论\n"
                        + "2. 去除冗余：省略寒暄、重复内容、中间推理过程\n"
                        + "3. 使用第三人称描述，如\"用户询问了...\"、\"助手完成了...\"\n"
                        + "4. 摘要长度控制在 300 字以内\n"
                        + "5. 如果存在之前的摘要，请将其与新的对话内容合并总结\n\n";

        /**
         * 将消息列表压缩为摘要文本
         *
         * @param chatClient         用于调用 LLM 的 ChatClient
         * @param messagesToCompress 需要压缩的消息列表
         * @param existingSummary    已有的摘要（可为 null，首次压缩时无历史摘要）
         * @return 压缩后的摘要文本
         */
        static String compress(ChatClient chatClient, List<Message> messagesToCompress, String existingSummary) {
            if (messagesToCompress == null || messagesToCompress.isEmpty()) {
                return existingSummary;
            }

            StringBuilder conversationText = new StringBuilder();

            if (existingSummary != null && !existingSummary.isBlank()) {
                conversationText.append("【之前的对话摘要】\n").append(existingSummary).append("\n\n");
            }

            conversationText.append("【需要总结的新对话】\n");
            for (Message message : messagesToCompress) {
                String role = formatRole(message.getMessageType());
                String content = message.getText();
                if (content != null && !content.isBlank()) {
                    conversationText.append(role).append(": ").append(content).append("\n");
                }
            }

            List<Message> promptMessages = new ArrayList<>();
            promptMessages.add(new SystemMessage(SUMMARIZE_PROMPT));
            promptMessages.add(new UserMessage(conversationText.toString()));

            try {
                String summary = chatClient.prompt(new Prompt(promptMessages))
                        .call()
                        .content();
                return (summary != null && !summary.isBlank()) ? summary : existingSummary;
            } catch (Exception exception) {
                System.err.println("[SummaryCompressor] 摘要压缩失败: " + exception.getMessage());
                return existingSummary;
            }
        }

        private static String formatRole(MessageType messageType) {
            return switch (messageType) {
                case USER -> "用户";
                case ASSISTANT -> "助手";
                case SYSTEM -> "系统";
                case TOOL -> "工具";
            };
        }
    }
}
