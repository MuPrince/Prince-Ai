package com.prince.agent.service.rag.chunk.intellegent;

import com.prince.agent.service.rag.Document;
import com.prince.agent.service.rag.chunk.ChunkSplitter;
import org.springframework.ai.embedding.EmbeddingModel;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * 语义分块器（Semantic Chunking）
 * <p>
 * 利用 Embedding 模型计算相邻句子的语义相似度，在语义断裂处（相似度骤降）切分文档。
 * 同一主题的内容会被聚合到同一个块中，不同主题之间自然分离。
 *
 * <p>算法流程：
 * <ol>
 *   <li>按句末标点将文本切分为句子列表</li>
 *   <li>用 EmbeddingModel 计算每个句子的向量</li>
 *   <li>计算相邻句子之间的余弦相似度</li>
 *   <li>当相似度低于阈值（动态计算：均值 - 标准差 × 系数）时，视为语义边界</li>
 *   <li>在语义边界处切分，合并同一语义段内的句子为一个块</li>
 *   <li>如果合并后的块超过 maxChunkSize，按句子边界再次拆分</li>
 * </ol>
 */
public class SemanticChunkSplitter implements ChunkSplitter {

    /** 句末标点正则：中英文句号、感叹号、问号 */
    private static final Pattern SENTENCE_END_PATTERN =
            Pattern.compile("(?<=[。！？!?.])");

    /** 断裂阈值系数：均值 - 标准差 × 此系数 = 断裂阈值，越大越不容易切分 */
    private static final double BREAKPOINT_THRESHOLD_FACTOR = 1.0;

    private final EmbeddingModel embeddingModel;

    /** 单个块的最大字符数，超过此值会按句子边界再次拆分 */
    private final int maxChunkSize;

    /**
     * @param embeddingModel Embedding 模型，用于计算句子向量
     * @param maxChunkSize   单个块的最大字符数（防止语义段过长）
     */
    public SemanticChunkSplitter(EmbeddingModel embeddingModel, int maxChunkSize) {
        if (maxChunkSize <= 0) {
            throw new IllegalArgumentException("maxChunkSize 必须大于 0");
        }
        this.embeddingModel = embeddingModel;
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

        // 2. 计算每个句子的 embedding 向量
        double[][] embeddings = computeEmbeddings(sentences);

        // 3. 计算相邻句子的余弦相似度
        double[] similarities = computeAdjacentSimilarities(embeddings);

        // 4. 动态计算断裂阈值：均值 - 标准差 × 系数
        double breakpointThreshold = computeBreakpointThreshold(similarities);
        System.out.println("  语义分块阈值: " + String.format("%.4f", breakpointThreshold));

        // 5. 在相似度低于阈值处切分
        List<List<String>> semanticGroups = groupBySimilarity(sentences, similarities, breakpointThreshold);

        // 6. 合并每组句子为一个块，超长的再拆分
        return buildDocuments(semanticGroups, source);
    }

    /**
     * 按句末标点切分文本为句子列表，过滤空白句子
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
     * 批量计算句子的 embedding 向量
     */
    private double[][] computeEmbeddings(List<String> sentences) {
        double[][] embeddings = new double[sentences.size()][];
        for (int i = 0; i < sentences.size(); i++) {
            float[] floatEmbedding = embeddingModel.embed(sentences.get(i));
            double[] embedding = new double[floatEmbedding.length];
            for (int j = 0; j < floatEmbedding.length; j++) {
                embedding[j] = floatEmbedding[j];
            }
            embeddings[i] = embedding;
        }
        return embeddings;
    }

    /**
     * 计算相邻句子之间的余弦相似度
     *
     * @return 长度为 sentences.size()-1 的相似度数组，similarities[i] 表示第 i 句和第 i+1 句的相似度
     */
    private double[] computeAdjacentSimilarities(double[][] embeddings) {
        double[] similarities = new double[embeddings.length - 1];
        for (int i = 0; i < similarities.length; i++) {
            similarities[i] = cosineSimilarity(embeddings[i], embeddings[i + 1]);
        }
        return similarities;
    }

    /**
     * 动态计算断裂阈值：均值 - 标准差 × 系数
     * 相似度低于此阈值的位置被视为语义边界
     */
    private double computeBreakpointThreshold(double[] similarities) {
        if (similarities.length == 0) {
            return 0.0;
        }

        double sum = 0.0;
        for (double similarity : similarities) {
            sum += similarity;
        }
        double mean = sum / similarities.length;

        double varianceSum = 0.0;
        for (double similarity : similarities) {
            varianceSum += (similarity - mean) * (similarity - mean);
        }
        double standardDeviation = Math.sqrt(varianceSum / similarities.length);

        return mean - standardDeviation * BREAKPOINT_THRESHOLD_FACTOR;
    }

    /**
     * 根据相似度和阈值将句子分组
     * 当相邻句子的相似度低于阈值时，在此处断开，开始新的一组
     */
    private List<List<String>> groupBySimilarity(
            List<String> sentences,
            double[] similarities,
            double threshold) {

        List<List<String>> groups = new ArrayList<>();
        List<String> currentGroup = new ArrayList<>();
        currentGroup.add(sentences.get(0));

        for (int i = 0; i < similarities.length; i++) {
            if (similarities[i] < threshold) {
                // 语义断裂，保存当前组，开始新组
                groups.add(currentGroup);
                currentGroup = new ArrayList<>();
            }
            currentGroup.add(sentences.get(i + 1));
        }

        if (!currentGroup.isEmpty()) {
            groups.add(currentGroup);
        }

        return groups;
    }

    /**
     * 将语义分组转换为 Document 列表
     * 如果某组合并后超过 maxChunkSize，按句子边界再次拆分
     */
    private List<Document> buildDocuments(List<List<String>> semanticGroups, String source) {
        List<Document> documents = new ArrayList<>();
        int chunkIndex = 0;

        for (List<String> group : semanticGroups) {
            String mergedContent = String.join("\n", group);

            if (mergedContent.length() <= maxChunkSize) {
                documents.add(new Document(mergedContent, source, chunkIndex++));
            } else {
                // 超长语义段按句子边界再拆分
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

    /**
     * 计算两个向量的余弦相似度
     */
    private double cosineSimilarity(double[] vectorA, double[] vectorB) {
        double dotProduct = 0.0;
        double normA = 0.0;
        double normB = 0.0;

        for (int i = 0; i < vectorA.length; i++) {
            dotProduct += vectorA[i] * vectorB[i];
            normA += vectorA[i] * vectorA[i];
            normB += vectorB[i] * vectorB[i];
        }

        double denominator = Math.sqrt(normA) * Math.sqrt(normB);
        if (denominator == 0) {
            return 0.0;
        }
        return dotProduct / denominator;
    }

    @Override
    public String name() {
        return "语义分块";
    }
}
