# 快速开始指南

## 前置要求

- Python 3.8+
- Node.js 16+
- 至少一个AI模型的API密钥（OpenAI / DeepSeek / Ollama）

## 快速启动

### 1. 后端设置（5分钟）

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（可选但推荐）
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入至少一个API密钥

# 启动服务
python main.py
# 或使用脚本
../start_backend.sh
```

后端将在 `http://localhost:8000` 启动。

### 2. 前端设置（3分钟）

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
# 或使用脚本
../start_frontend.sh
```

前端将在 `http://localhost:3000` 启动。

### 3. 使用系统

1. 打开浏览器访问 `http://localhost:3000`
2. 选择"粘贴文本"或"上传文件"
3. 选择模型提供商（可选）
4. 点击"开始校对"
5. 查看对比结果并导出

## 配置说明

### OpenAI配置

在 `.env` 文件中：

```env
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_MODEL_PROVIDER=openai
DEFAULT_MODEL_NAME=gpt-4-turbo-preview
```

### DeepSeek配置

```env
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEFAULT_MODEL_PROVIDER=deepseek
DEFAULT_MODEL_NAME=deepseek-chat
```

### Ollama配置（本地）

首先确保Ollama已安装并运行：

```bash
# 安装Ollama（如果未安装）
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# 启动Ollama服务
ollama serve

# 下载模型（可选）
ollama pull llama2
```

然后在 `.env` 中配置：

```env
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL_PROVIDER=ollama
DEFAULT_MODEL_NAME=llama2
```

## 测试API

### 使用curl测试

```bash
# 健康检查
curl http://localhost:8000/health

# 校对文本
curl -X POST http://localhost:8000/api/correct \
  -H "Content-Type: application/json" \
  -d '{
    "text": "这是一段需要校对的文本。",
    "provider": "openai"
  }'
```

### 使用Python测试

```bash
cd backend
python example_usage.py
```

## 常见问题

### 1. 后端启动失败

- 检查Python版本：`python --version`（需要3.8+）
- 检查依赖是否安装：`pip list`
- 检查`.env`文件是否存在并配置正确

### 2. 前端无法连接后端

- 检查后端是否运行：访问 `http://localhost:8000`
- 检查CORS配置（开发环境已允许所有来源）
- 检查前端代理配置（`vite.config.js`）

### 3. API调用失败

- 检查API密钥是否正确
- 检查网络连接
- 查看后端日志错误信息
- 尝试健康检查：`curl http://localhost:8000/health?provider=openai`

### 4. 文本分段问题

- 调整 `chunk_size` 和 `chunk_overlap` 参数
- 检查文本编码（应使用UTF-8）

## 下一步

- 阅读 [README.md](README.md) 了解详细功能
- 阅读 [ARCHITECTURE.md](ARCHITECTURE.md) 了解系统架构
- 自定义Prompt：编辑 `backend/utils/prompt_manager.py`
- 添加新模型：参考 `backend/models/` 下的适配器实现
