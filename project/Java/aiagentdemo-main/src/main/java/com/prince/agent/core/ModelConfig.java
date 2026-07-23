package com.prince.agent.core;

/**
 * 模型配置，描述一个 AI 模型提供商的连接信息
 * <p>
 * 支持运行时动态切换模型，只需传入不同的 ModelConfig 即可。
 */
public class ModelConfig {

    private final String baseUrl;
    private final String apiKey;
    private final String chatModel;
    private final String embeddingModel;
    private final String completionsPath;
    private final String embeddingsPath;

    public ModelConfig(String baseUrl, String apiKey, String chatModel, String embeddingModel) {
        this(baseUrl, apiKey, chatModel, embeddingModel, null, null);
    }

    public ModelConfig(String baseUrl, String apiKey, String chatModel, String embeddingModel,
                       String completionsPath, String embeddingsPath) {
        this.baseUrl = baseUrl;
        this.apiKey = apiKey;
        this.chatModel = chatModel;
        this.embeddingModel = embeddingModel;
        this.completionsPath = completionsPath;
        this.embeddingsPath = embeddingsPath;
    }

    public String getBaseUrl() {
        return baseUrl;
    }

    public String getApiKey() {
        return apiKey;
    }

    public String getChatModel() {
        return chatModel;
    }

    public String getEmbeddingModel() {
        return embeddingModel;
    }

    public String getCompletionsPath() {
        return completionsPath;
    }

    public String getEmbeddingsPath() {
        return embeddingsPath;
    }

    @Override
    public String toString() {
        return "ModelConfig{baseUrl='" + baseUrl + "', chatModel='" + chatModel + "', embeddingModel='" + embeddingModel
                + "', completionsPath='" + completionsPath + "', embeddingsPath='" + embeddingsPath + "'}";
    }
}
