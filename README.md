# 小说文本精校系统

一个用于对网络下载的小说进行**最小侵入式精校**的系统，专注于纠错而非润色。

## 系统特性

- ✅ **最小侵入式精校**：只纠正错误，不改变原文风格
- ✅ **多模型支持**：支持 OpenAI、DeepSeek、Ollama 本地模型
- ✅ **智能分段**：自动分段处理，支持通用分段和 Ollama 专用小分段
- ✅ **整段直发**：对 OpenAI / DeepSeek 等云端模型，短文本可整段发送，减少切片合并
- ✅ **差异对比**：可视化展示原文与精校文本的差异，忽略纯格式改动
- ✅ **任务与结果管理**：后台任务队列 + 任务进度页 + 比对结果列表页
- ✅ **Ollama 预纠错**：可选先经 pycorrector（Kenlm/MacBert/Gpt）一轮纠错再送 Ollama，提升本地模型效果；可在设置页开关并选择预纠错模型（默认 Kenlm）
- ✅ **系统配置面板**：前端实时调整分段、重试、默认模型、Prompt 文件等配置
- ✅ **一键导出**：支持导出精校后的完整文本或单章节

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
│   │   ├── correction_service.py   # 文本精校主服务
│   │   ├── task_manager.py         # 异步任务管理
│   │   └── storage/sqlite_store.py # 结果持久化存储
│   ├── utils/              # 工具模块
│   │   ├── text_splitter.py       # 文本分段（支持overlap与智能合并）
│   │   ├── chapter_splitter.py    # 按章节拆分长篇小说
│   │   ├── prompt_manager.py      # Prompt管理（支持文件与热更新）
│   │   ├── diff_utils.py          # 差异计算，忽略纯空白改动
│   │   ├── cost_estimator.py      # 调用成本预估
│   │   └── time_estimator.py      # 处理时间预估
│   ├── config.py           # 配置管理
│   ├── main.py             # FastAPI主应用
│   └── requirements.txt    # Python依赖
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # React组件
│   │   │   ├── TextUpload.jsx             # 文本上传/输入 + 模型选择
│   │   │   ├── CorrectionProgress.jsx     # 精校进度条
│   │   │   ├── TextComparison.jsx         # 旧版对比组件
│   │   │   ├── ComparisonViewPage.jsx     # 独立比对结果页面（章节/整本）
│   │   │   ├── ResultListPage.jsx         # 比对结果列表（卡片 + 分页）
│   │   │   ├── TaskProgressPage.jsx       # 后台任务进度列表
│   │   │   └── SettingsPage.jsx           # 系统配置（模型/分段/Prompt等）
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

响应（简化示例）：

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

### 6. 配置与 Prompt 相关接口（简要）

- 获取/更新运行时配置（分段、重试、默认模型等，可选持久化到 `.env`）：

```http
GET  /api/config
POST /api/config
```

- 获取/更新 Prompt（可选择仅更新内存，或写入默认 Prompt 文件并更新 `PROMPT_FILE`）：

```http
GET  /api/prompt?reload=false
POST /api/prompt
```

- 任务与结果相关：
  - `GET /api/tasks` / `GET /api/tasks/{task_id}`：查看异步任务进度
  - `GET /api/results`：比对结果列表（分页）
  - `GET /api/results/{id}`：结果详情
  - `GET /api/results/{id}/download`：下载原文或精校文本

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
- 智能合并，去除重复的 overlap 部分，兼容模型对文本的轻微改写
- 对 Ollama 可使用更小的 `OLLAMA_CHUNK_SIZE`，适配本地大模型显存
- 对 OpenAI / DeepSeek，当单段长度不超过 `FAST_PROVIDER_MAX_CHARS` 时可整段直发

### 3. Prompt 管理

默认 Prompt 严格限制：
- ✅ 只纠正错误（错别字、病句、拼音转中文、标点错误）
- ❌ 禁止润色、改写、增删内容
- ❌ 禁止改变文风、语气、措辞

Prompt 支持通过文件和前端界面自定义：

- 在后端 `.env` 中设置：

```env
PROMPT_FILE=./prompts/custom_prompt.txt
```

- 在前端「系统配置 → Prompt配置」：
  - 直接编辑 Prompt 文本
  - 选择是否持久化到默认 Prompt 文件并自动更新 `PROMPT_FILE`
  - 点击「刷新」可强制从 Prompt 文件重新加载（无需重启后端）

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

- 模型与列表：
  - `DEFAULT_MODEL_PROVIDER`: 默认模型提供商（如 `openai` / `deepseek` / `ollama`）
  - `DEFAULT_MODEL_NAME`: 默认模型名称
  - `OPENAI_MODELS` / `DEEPSEEK_MODELS` / `OLLAMA_MODELS`: 各提供商可用模型列表，逗号分隔
- 分段与上下文：
  - `CHUNK_SIZE`: 全局文本分段大小（默认 2000）
  - `CHUNK_OVERLAP`: 全局分段重叠大小（默认 200）
  - `OLLAMA_CHUNK_SIZE`: Ollama 专用分段大小，适配本地大模型（建议 800–1000）
  - `OLLAMA_CHUNK_OVERLAP`: Ollama 专用分段重叠
  - `OLLAMA_USE_PYCORRECTOR`: 是否对 Ollama 启用 pycorrector 预纠错（默认 `true`）
  - `OLLAMA_PYCORRECTOR_MODEL`: 预纠错模型，可选 `kenlm`（轻量，默认）、`macbert`、`gpt`；macbert/gpt 需额外依赖与资源
  - `FAST_PROVIDER_MAX_CHARS`: 对 OpenAI / DeepSeek 等云端模型的整段直发阈值（字符数）
- 重试策略：
  - `MAX_RETRIES`: 最大重试次数（默认 3）
  - `RETRY_DELAY`: 重试延迟（秒，默认 1.0）
- Prompt：
  - `PROMPT_FILE`: 自定义 Prompt 文件路径（相对 `backend` 目录）

> 建议优先通过前端「系统配置」页面修改配置并选择是否持久化到 `.env`，  
> 直接编辑 `.env` 后需重启后端服务才能生效。

### 前端配置

在 `frontend/.env` 中配置：

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Ollama 预纠错（pycorrector）

当使用 **Ollama** 时，可在设置页开启「Ollama 预纠错」：先经 [pycorrector](https://github.com/shibing624/pycorrector) 一轮纠错，再将结果送入 Ollama 做二次纠错，以提升本地模型效果。

- **预纠错模型**：默认 `kenlm`（统计模型，CPU、轻量；首次使用会下载语言模型到 `~/.pycorrector/`）。可选 `macbert`、`gpt`，效果更好但需更多依赖与显存。
- **依赖**：`pip install pycorrector torch`（见 `requirements.txt`；pycorrector 依赖 PyTorch）。**kenlm** 未放入默认依赖，因在 Windows 下需 C++ 编译环境且易构建失败。Linux/Mac 若需 kenlm 预纠错：`pip install kenlm` 或 `pip install -r requirements-ollama.txt`。Windows 下请使用设置中的 **macbert** 预纠错或关闭预纠错。
- **配置**：前端「系统配置 → 处理配置」中「Ollama 预纠错」区块可开关并选择预纠错模型；或通过 `.env` 设置 `OLLAMA_USE_PYCORRECTOR`、`OLLAMA_PYCORRECTOR_MODEL`。

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

1. 在 `backend/prompts/` 下创建 Prompt 文件（如 `custom_prompt.txt`）
2. 在 `.env` 中设置 `PROMPT_FILE=./prompts/custom_prompt.txt`
3. 通过前端「系统配置 → Prompt配置」编辑和持久化 Prompt

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
