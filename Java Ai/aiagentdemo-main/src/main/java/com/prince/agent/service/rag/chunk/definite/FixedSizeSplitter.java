package com.prince.agent.service.rag.chunk.definite;

import com.prince.agent.service.rag.Document;
import com.prince.agent.service.rag.chunk.ChunkSplitter;

import java.util.ArrayList;
import java.util.List;

/**
 * 固定大小分块策略
 * 最简单的分块策略，按固定字符数切分，支持重叠
 */
public class FixedSizeSplitter implements ChunkSplitter {
    private final int chunkSize;
    private final int chunkOverlap;

    public FixedSizeSplitter(int chunkSize, int chunkOverlap) {
        if (chunkSize <= 0) {
            throw new IllegalArgumentException("chunkSize must be positive");
        }
        if (chunkOverlap < 0) {
            throw new IllegalArgumentException("chunkOverlap must be non-negative");
        }
        if (chunkOverlap >= chunkSize) {
            throw new IllegalArgumentException("chunkOverlap must be less than chunkSize");
        }
        this.chunkSize = chunkSize;
        this.chunkOverlap = chunkOverlap;
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
            int endPosition = Math.min(position + chunkSize, textLength);
            String chunkContent = text.substring(position, endPosition);
            
            if (!chunkContent.trim().isEmpty()) {
                chunks.add(new Document(chunkContent, source, chunkIndex));
                chunkIndex++;
            }
            
            position += (chunkSize - chunkOverlap);
            if (position >= textLength) {
                break;
            }
        }

        return chunks;
    }

    @Override
    public String name() {
        return "固定大小分块";
    }
}
