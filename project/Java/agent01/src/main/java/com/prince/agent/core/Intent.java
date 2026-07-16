package com.prince.agent.core;

/**
 * 用户意图枚举
 * <p>
 * 用于意图识别阶段，区分用户输入的意图类型，以便 Agent 采取不同的处理策略。
 */
public enum Intent {

    /**
     * 知识库检索：用户的问题需要从 RAG 知识库中检索相关信息来回答
     */
    RAG,

    /**
     * 通用对话：闲聊、工具调用、代码生成等，交由大模型自主处理
     */
    GENERAL
}
