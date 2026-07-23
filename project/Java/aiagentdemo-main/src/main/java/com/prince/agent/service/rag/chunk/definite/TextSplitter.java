package com.prince.agent.service.rag.chunk.definite;

import com.prince.agent.service.rag.Document;
import com.prince.agent.service.rag.chunk.ChunkSplitter;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * 轻量级递归语义分块器（Recursive Semantic Chunking）
 * <p>
 * 按照语义粒度从粗到细依次尝试切分，优先保留语义完整性：
 * <ol>
 *   <li>标题行（Markdown # 或中文章节标题）：天然的语义章节边界</li>
 *   <li>段落（连续两个以上换行）：保留段落完整性</li>
 *   <li>句子（句末标点 。！？.!?）：保证句子不被截断</li>
 *   <li>固定字符数：最终兜底，防止超长文本无法切分</li>
 * </ol>
 * 相邻块之间保留 chunkOverlap 个字符的重叠，维持上下文连贯性。
 */
public class TextSplitter implements ChunkSplitter {

    /** 每个文本块的目标最大字符数 */
    private final int chunkSize;

    /** 相邻文本块之间的重叠字符数 */
    private final int chunkOverlap;

    /**
     * 标题行正则：匹配 Markdown 标题（# 开头）或中文章节标题（第X章/节/部分 开头）
     * 用于识别文档的章节边界
     */
    private static final Pattern HEADING_PATTERN =
            Pattern.compile("^(#{1,6}\\s.+|第[一二三四五六七八九十百千\\d]+[章节部分篇].*)$",
                    Pattern.MULTILINE);

    /** 句末标点正则：中英文句号、感叹号、问号 */
    private static final Pattern SENTENCE_END_PATTERN =
            Pattern.compile("(?<=[。！？!?])");

    public TextSplitter(int chunkSize, int chunkOverlap) {
        if (chunkOverlap >= chunkSize) {
            throw new IllegalArgumentException("chunkOverlap 必须小于 chunkSize");
        }
        this.chunkSize = chunkSize;
        this.chunkOverlap = chunkOverlap;
    }

    @Override
    public String name() {
        return "递归语义分块";
    }

    /**
     * 将文本递归语义分块，返回 Document 列表
     *
     * @param text   原始文档文本
     * @param source 文档来源标识（如文件名）
     * @return 分块后的文档列表
     */
    public List<Document> split(String text, String source) {
        if (text == null || text.isBlank()) {
            return new ArrayList<>();
        }

        List<String> rawChunks = new ArrayList<>();
        splitRecursively(text.trim(), rawChunks);

        // 将原始块合并为不超过 chunkSize 的最终块，并加入重叠
        return mergeAndOverlap(rawChunks, source);
    }

    /**
     * 递归切分：按语义粒度从粗到细依次尝试，直到每段不超过 chunkSize
     */
    private void splitRecursively(String text, List<String> result) {
        if (text.length() <= chunkSize) {
            if (!text.isBlank()) {
                result.add(text.trim());
            }
            return;
        }

        // 第1级：按标题行切分
        List<String> headingSegments = splitByHeading(text);
        if (headingSegments.size() > 1) {
            for (String segment : headingSegments) {
                splitRecursively(segment.trim(), result);
            }
            return;
        }

        // 第2级：按段落（双换行）切分
        List<String> paragraphSegments = splitByParagraph(text);
        if (paragraphSegments.size() > 1) {
            for (String segment : paragraphSegments) {
                splitRecursively(segment.trim(), result);
            }
            return;
        }

        // 第3级：按句子（句末标点）切分
        List<String> sentenceSegments = splitBySentence(text);
        if (sentenceSegments.size() > 1) {
            for (String segment : sentenceSegments) {
                splitRecursively(segment.trim(), result);
            }
            return;
        }

        // 第4级：固定字符数强制切分（兜底）
        int start = 0;
        while (start < text.length()) {
            int end = Math.min(start + chunkSize, text.length());
            String chunk = text.substring(start, end).trim();
            if (!chunk.isBlank()) {
                result.add(chunk);
            }
            start += chunkSize;
        }
    }

    /**
     * 按标题行切分：在每个标题行前断开，标题行归入下一段
     */
    private List<String> splitByHeading(String text) {
        List<String> segments = new ArrayList<>();
        String[] lines = text.split("\n");
        StringBuilder currentSegment = new StringBuilder();

        for (String line : lines) {
            if (HEADING_PATTERN.matcher(line.trim()).matches() && currentSegment.length() > 0) {
                segments.add(currentSegment.toString().trim());
                currentSegment = new StringBuilder();
            }
            if (!currentSegment.isEmpty()) {
                currentSegment.append("\n");
            }
            currentSegment.append(line);
        }

        if (!currentSegment.isEmpty()) {
            segments.add(currentSegment.toString().trim());
        }

        return segments;
    }

    /**
     * 按段落（连续两个以上换行）切分
     */
    private List<String> splitByParagraph(String text) {
        List<String> segments = new ArrayList<>();
        for (String segment : text.split("\n\n+")) {
            String trimmed = segment.trim();
            if (!trimmed.isBlank()) {
                segments.add(trimmed);
            }
        }
        return segments;
    }

    /**
     * 按句末标点切分，将短句合并避免碎片化
     */
    private List<String> splitBySentence(String text) {
        String[] rawSentences = SENTENCE_END_PATTERN.split(text);
        List<String> sentences = new ArrayList<>();
        for (String sentence : rawSentences) {
            String trimmed = sentence.trim();
            if (!trimmed.isBlank()) {
                sentences.add(trimmed);
            }
        }
        return sentences;
    }

    /**
     * 将原始切分结果合并为不超过 chunkSize 的最终块，并在相邻块间加入重叠内容
     *
     * @param rawChunks 递归切分后的原始文本片段列表
     * @param source    文档来源标识
     * @return 最终的 Document 列表
     */
    private List<Document> mergeAndOverlap(List<String> rawChunks, String source) {
        List<Document> documents = new ArrayList<>();
        StringBuilder currentChunk = new StringBuilder();
        int chunkIndex = 0;

        for (String rawChunk : rawChunks) {
            // 当前块加上新片段会超过 chunkSize，先保存当前块
            if (!currentChunk.isEmpty()
                    && currentChunk.length() + rawChunk.length() + 1 > chunkSize) {
                documents.add(new Document(currentChunk.toString().trim(), source, chunkIndex++));
                // 保留末尾 chunkOverlap 个字符作为下一块的开头，维持上下文连贯性
                String overlap = extractOverlap(currentChunk.toString());
                currentChunk = new StringBuilder(overlap);
            }

            if (!currentChunk.isEmpty()) {
                currentChunk.append("\n");
            }
            currentChunk.append(rawChunk);
        }

        // 保存最后一个块
        if (!currentChunk.isEmpty()) {
            documents.add(new Document(currentChunk.toString().trim(), source, chunkIndex));
        }

        return documents;
    }

    /**
     * 从文本末尾提取 chunkOverlap 个字符作为重叠内容
     */
    private String extractOverlap(String text) {
        if (text.length() <= chunkOverlap) {
            return text;
        }
        return text.substring(text.length() - chunkOverlap);
    }
}
