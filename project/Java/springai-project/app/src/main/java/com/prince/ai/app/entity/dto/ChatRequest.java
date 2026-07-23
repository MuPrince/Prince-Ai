package com.prince.ai.app.entity.dto;

/**
 * 对话请求
 */
public class ChatRequest {

    private String message;
    private String sessionId;

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getSessionId() {
        return sessionId;
    }

    public void setSessionId(String sessionId) {
        this.sessionId = sessionId;
    }
}
