package com.prince.agent.service.rag.chunk.definite;

import com.prince.agent.service.rag.Document;
import com.prince.agent.service.rag.chunk.ChunkSplitter;

import java.util.ArrayList;
import java.util.List;

/**
 * 滑动窗口分块策略
 * 窗口大小固定，步长固定，每次滑动固定字符数
 */
public class SlidingWindowSplitter implements ChunkSplitter {
    private final int windowSize;
    private final int stepSize;

    public SlidingWindowSplitter(int windowSize, int stepSize) {
        if (windowSize <= 0) {
            throw new IllegalArgumentException("windowSize must be positive");
        }
        if (stepSize <= 0) {
            throw new IllegalArgumentException("stepSize must be positive");
        }
        if (stepSize > windowSize) {
            throw new IllegalArgumentException("stepSize must be less than or equal to windowSize");
        }
        this.windowSize = windowSize;
        this.stepSize = stepSize;
    }

    @Override
    public List<Document> split(String text, String source) {
        List<Document> chunks = new ArrayList<>();
        if (text == null || text.trim().isEmpty()) {
            return chunks;
        }

        int position = 0;
        int chunkIndex = 0;
        int textLength = text.length();

        while (position < textLength) {
            int endPosition = Math.min(position + windowSize, textLength);
            String chunkContent = text.substring(position, endPosition);
            
            if (!chunkContent.trim().isEmpty()) {
                chunks.add(new Document(chunkContent, source, chunkIndex));
                chunkIndex++;
            }
            
            position += stepSize;
            if (position >= textLength) {
                break;
            }
        }

        return chunks;
    }

    @Override
    public String name() {
        return "滑动窗口分块";
    }
}
