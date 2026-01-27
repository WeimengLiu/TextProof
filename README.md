# 小说文本精校系统

一个用于对网络下载的小说进行**最小侵入式精校**的系统，专注于纠错而非润色。

## 系统特性

- ✅ **最小侵入式精校**：只纠正错误，不改变原文风格
- ✅ **多模型支持**：支持 OpenAI、DeepSeek、Ollama 本地模型
- ✅ **智能分段**：自动分段处理，防止上下文污染
- ✅ **差异对比**：可视化展示原文与精校文本的差异
- ✅ **进度追踪**：实时显示校对进度
- ✅ **一键导出**：支持导出精校后的完整文本

## 系统架构

```
TextProof/
├── backend/                 # 后端服务
│   ├── models/             # 模型适配器层
│   │   ├── base.py         # 适配器基类
│   │   ├── openai_adapter.py
│   │   ├── deepseek_adapter.py
│   │   ├── ollama_adapter.py
│   │   └── factory.py      # 工厂模式创建适配器
│   ├── services/           # 业务逻辑层
│   │   └── correction_service.py
│   ├── utils/              # 工具模块
│   │   ├── text_splitter.py    # 文本分段
│   │   ├── prompt_manager.py   # Prompt管理
│   │   └── diff_utils.py       # 差异计算
│   ├── config.py           # 配置管理
│   ├── main.py             # FastAPI主应用
│   └── requirements.txt    # Python依赖
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # React组件
│   │   │   ├── TextUpload.jsx
│   │   │   ├── CorrectionProgress.jsx
│   │   │   └── TextComparison.jsx
│   │   ├── services/       # API服务
│   │   │   └── api.js
│   │   ├── App.jsx         # 主应用组件
│   │   └── main.jsx        # 入口文件
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## 快速开始

### 后端设置

1. **安装依赖**

```bash
cd backend
pip install -r requirements.txt
```

2. **配置环境变量**

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，至少配置一个模型提供商的API密钥：

```env
# OpenAI配置
OPENAI_API_KEY=your_openai_api_key_here

# 或 DeepSeek配置
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# 或 Ollama配置（本地部署）
OLLAMA_BASE_URL=http://localhost:11434
```

3. **启动后端服务**

```bash
python main.py
# 或使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

后端服务将在 `http://localhost:8000` 启动。

### 前端设置

1. **安装依赖**

```bash
cd frontend
npm install
```

2. **启动开发服务器**

```bash
npm run dev
```

前端应用将在 `http://localhost:3000` 启动。

## API 文档

### 1. 健康检查

```http
GET /health?provider=openai&model_name=gpt-4-turbo-preview
```

### 2. 校对文本

```http
POST /api/correct
Content-Type: application/json

{
  "text": "待校对的文本",
  "provider": "openai",  // 可选
  "model_name": "gpt-4-turbo-preview",  // 可选
  "chunk_size": 2000,  // 可选
  "chunk_overlap": 200  // 可选
}
```

响应：

```json
{
  "original": "原文",
  "corrected": "校对后的文本",
  "chunks_processed": 5,
  "total_chunks": 5,
  "has_changes": true
}
```

### 3. 上传文件校对

```http
POST /api/correct/file?provider=openai&model_name=gpt-4-turbo-preview
Content-Type: multipart/form-data

file: [TXT文件]
```

### 4. 获取文本差异

```http
POST /api/diff
Content-Type: application/json

{
  "text": "原文",
  "corrected": "校对后的文本"  // 可选，不提供则先校对
}
```

响应：

```json
{
  "original_segments": [
    {"text": "文本片段", "type": "same|deleted"}
  ],
  "corrected_segments": [
    {"text": "文本片段", "type": "same|added"}
  ],
  "has_changes": true
}
```

### 5. 获取可用提供商

```http
GET /api/providers
```

## 核心模块说明

### 1. Model Adapter 层

统一的模型适配器接口，支持：
- **OpenAI**: 通过 OpenAI API
- **DeepSeek**: 通过 DeepSeek API（兼容 OpenAI 格式）
- **Ollama**: 本地部署的模型

所有适配器实现 `BaseModelAdapter` 接口，提供：
- `correct_text()`: 校对文本
- `health_check()`: 健康检查
- `correct_text_with_retry()`: 带重试的校对

### 2. 文本分段策略

- 优先按段落（`\n\n`）分割
- 超长段落按句子分割
- 支持重叠（overlap）防止上下文丢失
- 智能合并，去除重复的 overlap 部分

### 3. Prompt 管理

默认 Prompt 严格限制：
- ✅ 只纠正错误（错别字、病句、拼音转中文、标点错误）
- ❌ 禁止润色、改写、增删内容
- ❌ 禁止改变文风、语气、措辞

Prompt 可通过文件自定义，便于调整。

### 4. 差异对比

使用 `diff-match-patch` 算法计算差异，支持：
- 高亮显示修改部分
- 删除内容显示删除线
- 新增内容高亮显示

## 使用示例

### 后端直接调用

```python
from services.correction_service import CorrectionService

service = CorrectionService(provider="openai", model_name="gpt-4-turbo-preview")
result = await service.correct_text("待校对的文本")
print(result["corrected"])
```

### 前端使用

1. 打开前端应用 `http://localhost:3000`
2. 选择"粘贴文本"或"上传文件"
3. 选择模型提供商（可选）
4. 点击"开始校对"
5. 查看对比结果并导出

## 配置说明

### 后端配置（`.env`）

- `CHUNK_SIZE`: 文本分段大小（默认 2000）
- `CHUNK_OVERLAP`: 分段重叠大小（默认 200）
- `MAX_RETRIES`: 最大重试次数（默认 3）
- `RETRY_DELAY`: 重试延迟（秒，默认 1.0）

### 前端配置

在 `frontend/.env` 中配置：

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 注意事项

1. **API 密钥安全**：不要将 `.env` 文件提交到版本控制
2. **模型选择**：根据文本长度和预算选择合适的模型
3. **分段大小**：过长可能导致上下文丢失，过短可能增加 API 调用次数
4. **重试机制**：网络不稳定时会自动重试，但可能增加处理时间

## 开发说明

### 添加新的模型提供商

1. 在 `backend/models/` 下创建新的适配器类，继承 `BaseModelAdapter`
2. 实现 `correct_text()` 和 `health_check()` 方法
3. 在 `factory.py` 中注册新适配器

### 自定义 Prompt

1. 创建 Prompt 文件（如 `custom_prompt.txt`）
2. 在代码中初始化：`PromptManager(prompt_file="custom_prompt.txt")`
3. 或直接修改 `prompt_manager.py` 中的 `DEFAULT_PROMPT`

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
