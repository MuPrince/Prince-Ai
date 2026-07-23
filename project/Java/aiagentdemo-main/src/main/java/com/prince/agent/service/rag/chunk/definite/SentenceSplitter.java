package com.prince.agent.service.rag.chunk.definite;

import com.prince.agent.service.rag.Document;
import com.prince.agent.service.rag.chunk.ChunkSplitter;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 句子边界分块策略
 * 按句子边界切分，保证不在句子中间截断
 */
public class SentenceSplitter implements ChunkSplitter {
    private final int chunkSize;
    private final int chunkOverlap;
    private static final Pattern SENTENCE_PATTERN = Pattern.compile(".*?[。！？.!?]\\s*|[^。！？.!?]+$");

    public SentenceSplitter(int chunkSize, int chunkOverlap) {
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

        List<String> sentences = splitIntoSentences(text);
        if (sentences.isEmpty()) {
            return chunks;
        }

        StringBuilder currentChunk = new StringBuilder();
        int chunkIndex = 0;

        for (String sentence : sentences) {
            String trimmedSentence = sentence.trim();
            if (trimmedSentence.isEmpty()) {
                continue;
            }

            if (trimmedSentence.length() > chunkSize) {
                if (!currentChunk.isEmpty()) {
                    addChunk(chunks, source, currentChunk.toString(), chunkIndex);
                    chunkIndex++;
                    currentChunk.setLength(0);
                }
                splitLongSentence(chunks, trimmedSentence, source, chunkIndex);
                chunkIndex += (trimmedSentence.length() / chunkSize) + 1;
            } else if (currentChunk.length() + trimmedSentence.length() > chunkSize) {
                if (!currentChunk.isEmpty()) {
                    addChunk(chunks, source, currentChunk.toString(), chunkIndex);
                    chunkIndex++;
                    
                    String overlapText = getOverlapText(currentChunk.toString());
                    currentChunk.setLength(0);
                    if (!overlapText.isEmpty()) {
                        currentChunk.append(overlapText);
                    }
                }
                currentChunk.append(trimmedSentence);
            } else {
                if (!currentChunk.isEmpty()) {
                    currentChunk.append(" ");
                }
                currentChunk.append(trimmedSentence);
            }
        }

        if (!currentChunk.isEmpty()) {
            addChunk(chunks, source, currentChunk.toString(), chunkIndex);
        }

        return chunks;
    }

    private List<String> splitIntoSentences(String text) {
        List<String> sentences = new ArrayList<>();
        Matcher matcher = SENTENCE_PATTERN.matcher(text);
        while (matcher.find()) {
            String sentence = matcher.group().trim();
            if (!sentence.isEmpty()) {
                sentences.add(sentence);
            }
        }
        return sentences;
    }

    private String getOverlapText(String chunk) {
        if (chunkOverlap <= 0 || chunk.length() <= chunkOverlap) {
            return "";
        }
        return chunk.substring(chunk.length() - chunkOverlap);
    }

    private void addChunk(List<Document> chunks, String source, String content, int index) {
        if (!content.trim().isEmpty()) {
            chunks.add(new Document(content, source, index));
        }
    }

    private void splitLongSentence(List<Document> chunks, String sentence, String source, int startIndex) {
        int position = 0;
        int index = startIndex;
        while (position < sentence.length()) {
            int end = Math.min(position + chunkSize, sentence.length());
            String chunk = sentence.substring(position, end);
            if (!chunk.trim().isEmpty()) {
                chunks.add(new Document(chunk, source, index));
                index++;
            }
            position += (chunkSize - chunkOverlap);
            if (position >= sentence.length()) {
                break;
            }
        }
    }

    @Override
    public String name() {
        return "句子边界分块";
    }
}
