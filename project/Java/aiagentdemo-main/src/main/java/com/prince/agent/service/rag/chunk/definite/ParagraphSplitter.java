package com.prince.agent.service.rag.chunk.definite;

import com.prince.agent.service.rag.Document;
import com.prince.agent.service.rag.chunk.ChunkSplitter;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * 段落分块策略
 * 按段落边界切分，保持段落完整性
 */
public class ParagraphSplitter implements ChunkSplitter {
    private final int chunkSize;
    private final int chunkOverlap;
    private static final Pattern SENTENCE_PATTERN = Pattern.compile(".*?[。！？.!?]\\s*|[^。！？.!?]+$");

    public ParagraphSplitter(int chunkSize, int chunkOverlap) {
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

        List<String> paragraphs = splitIntoParagraphs(text);
        if (paragraphs.isEmpty()) {
            return chunks;
        }

        StringBuilder currentChunk = new StringBuilder();
        int chunkIndex = 0;

        for (String paragraph : paragraphs) {
            String trimmedParagraph = paragraph.trim();
            if (trimmedParagraph.isEmpty()) {
                continue;
            }

            if (trimmedParagraph.length() > chunkSize) {
                if (!currentChunk.isEmpty()) {
                    addChunk(chunks, source, currentChunk.toString(), chunkIndex);
                    chunkIndex++;
                    currentChunk.setLength(0);
                }
                splitLongParagraph(chunks, trimmedParagraph, source, chunkIndex);
                chunkIndex += (trimmedParagraph.length() / chunkSize) + 1;
            } else if (currentChunk.length() + trimmedParagraph.length() > chunkSize) {
                if (!currentChunk.isEmpty()) {
                    addChunk(chunks, source, currentChunk.toString(), chunkIndex);
                    chunkIndex++;
                    
                    String overlapText = getOverlapText(currentChunk.toString());
                    currentChunk.setLength(0);
                    if (!overlapText.isEmpty()) {
                        currentChunk.append(overlapText);
                    }
                }
                currentChunk.append(trimmedParagraph);
            } else {
                if (!currentChunk.isEmpty()) {
                    currentChunk.append("\n\n");
                }
                currentChunk.append(trimmedParagraph);
            }
        }

        if (!currentChunk.isEmpty()) {
            addChunk(chunks, source, currentChunk.toString(), chunkIndex);
        }

        return chunks;
    }

    private List<String> splitIntoParagraphs(String text) {
        String[] paragraphs = text.split("\n\n+");
        List<String> result = new ArrayList<>();
        for (String para : paragraphs) {
            String trimmed = para.trim();
            if (!trimmed.isEmpty()) {
                result.add(trimmed);
            }
        }
        return result;
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

    private void splitLongParagraph(List<Document> chunks, String paragraph, String source, int startIndex) {
        List<String> sentences = splitIntoSentences(paragraph);
        StringBuilder currentChunk = new StringBuilder();
        int index = startIndex;

        for (String sentence : sentences) {
            String trimmedSentence = sentence.trim();
            if (trimmedSentence.isEmpty()) {
                continue;
            }

            if (trimmedSentence.length() > chunkSize) {
                if (!currentChunk.isEmpty()) {
                    addChunk(chunks, source, currentChunk.toString(), index);
                    index++;
                    currentChunk.setLength(0);
                }
                splitLongSentence(chunks, trimmedSentence, source, index);
                index += (trimmedSentence.length() / chunkSize) + 1;
            } else if (currentChunk.length() + trimmedSentence.length() > chunkSize) {
                if (!currentChunk.isEmpty()) {
                    addChunk(chunks, source, currentChunk.toString(), index);
                    index++;
                    
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
            addChunk(chunks, source, currentChunk.toString(), index);
        }
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
        return "段落分块";
    }
}
