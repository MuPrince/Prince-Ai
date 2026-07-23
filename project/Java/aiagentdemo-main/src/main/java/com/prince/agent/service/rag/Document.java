package com.prince.agent.service.rag;

/**
 * 文档模型，表示知识库中的一个文本片段
 */
public class Document {

    /** 文档内容 */
    private final String content;

    /** 文档来源（文件名或标识符） */
    private final String source;

    /** 文档在原始文件中的块索引 */
    private final int chunkIndex;

    public Document(String content, String source, int chunkIndex) {
        this.content = content;
        this.source = source;
        this.chunkIndex = chunkIndex;
    }

    public String getContent() {
        return content;
    }

    public String getSource() {
        return source;
    }

    public int getChunkIndex() {
        return chunkIndex;
    }

    @Override
    public String toString() {
        return "Document{source='" + source + "', chunkIndex=" + chunkIndex + ", content='" + content + "'}";
    }
}
