# LangChain 项目（阿里云百炼）

基于阿里云百炼平台的 LangChain 项目。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置环境变量

复制 `.env.example` 为 `.env` 并填入你的 API Key：

```bash
cp .env.example .env
```

然后编辑 `.env` 文件，填入你的 `DASHSCOPE_API_KEY`。

## 运行项目

```bash
python main.py
```

## 可用模型

- `qwen-turbo`（默认）
- `qwen-plus`
- `qwen-max`
- 其他阿里云百炼支持的模型
