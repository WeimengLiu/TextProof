# 系统架构设计文档

## 一、整体架构说明

### 1.1 系统分层架构

```
┌─────────────────────────────────────────┐
│           前端层 (React + MUI)          │
│  - 文本上传组件                          │
│  - 进度展示组件                          │
│  - 对比展示组件                          │
└─────────────────┬───────────────────────┘
                  │ HTTP/REST API
┌─────────────────▼───────────────────────┐
│         API层 (FastAPI)                 │
│  - RESTful接口                           │
│  - 请求验证                              │
│  - 错误处理                              │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│        服务层 (CorrectionService)       │
│  - 文本分段                              │
│  - 调用模型适配器                        │
│  - 结果合并                              │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│    模型适配器层 (Model Adapter)         │
│  - OpenAI Adapter                       │
│  - DeepSeek Adapter                     │
│  - Ollama Adapter                       │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│         外部AI服务                       │
│  - OpenAI API                           │
│  - DeepSeek API                         │
│  - Ollama (本地)                        │
└─────────────────────────────────────────┘
```

### 1.2 核心模块划分

1. **模型适配器层** (`backend/models/`)
   - 统一的适配器接口 (`BaseModelAdapter`)
   - 各模型的具体实现
   - 工厂模式创建适配器实例

2. **服务层** (`backend/services/`)
   - 文本校对服务 (`CorrectionService`)
   - 协调分段、调用、合并流程

3. **工具层** (`backend/utils/`)
   - 文本分段器 (`TextSplitter`)
   - Prompt管理器 (`PromptManager`)
   - 差异计算工具 (`diff_utils`)

4. **API层** (`backend/main.py`)
   - FastAPI路由定义
   - 请求/响应模型
   - 错误处理

5. **前端层** (`frontend/src/`)
   - React组件
   - API服务封装
   - UI交互逻辑

## 二、后端API设计

### 2.1 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 根路径，返回系统信息 |
| GET | `/health` | 健康检查 |
| POST | `/api/correct` | 校对文本 |
| POST | `/api/correct/file` | 上传文件校对 |
| POST | `/api/diff` | 获取文本差异 |
| GET | `/api/providers` | 获取可用模型提供商 |

### 2.2 接口详细说明

#### 2.2.1 校对文本

**请求示例：**
```json
POST /api/correct
Content-Type: application/json

{
  "text": "这是一段需要校对的文本。",
  "provider": "openai",
  "model_name": "gpt-4-turbo-preview",
  "chunk_size": 2000,
  "chunk_overlap": 200
}
```

**响应示例：**
```json
{
  "original": "原文",
  "corrected": "校对后的文本",
  "chunks_processed": 5,
  "total_chunks": 5,
  "has_changes": true
}
```

#### 2.2.2 上传文件校对

**请求示例：**
```
POST /api/correct/file?provider=openai&model_name=gpt-4-turbo-preview
Content-Type: multipart/form-data

file: [TXT文件]
```

#### 2.2.3 获取文本差异

**请求示例：**
```json
POST /api/diff
Content-Type: application/json

{
  "text": "原文",
  "corrected": "校对后的文本"
}
```

**响应示例：**
```json
{
  "original_segments": [
    {"text": "文本片段", "type": "same"},
    {"text": "错误文本", "type": "deleted"}
  ],
  "corrected_segments": [
    {"text": "文本片段", "type": "same"},
    {"text": "正确文本", "type": "added"}
  ],
  "has_changes": true
}
```

## 三、多模型Adapter设计

### 3.1 设计思路

采用**适配器模式**，定义统一的接口，各模型提供商实现该接口：

```python
BaseModelAdapter (抽象基类)
├── OpenAIAdapter
├── DeepSeekAdapter
└── OllamaAdapter
```

### 3.2 核心接口

```python
class BaseModelAdapter(ABC):
    @abstractmethod
    async def correct_text(text: str, prompt: str) -> str:
        """校对文本"""
        pass
    
    @abstractmethod
    async def health_check() -> bool:
        """健康检查"""
        pass
    
    async def correct_text_with_retry(...):
        """带重试的校对"""
        pass
```

### 3.3 工厂模式创建

```python
adapter = ModelAdapterFactory.create_adapter(
    provider="openai",
    model_name="gpt-4-turbo-preview"
)
```

### 3.4 各模型实现要点

- **OpenAI**: 使用 `openai` 库，标准Chat API
- **DeepSeek**: 兼容OpenAI格式，使用相同库
- **Ollama**: HTTP请求，使用 `httpx` 库

## 四、文本分段与合并策略

### 4.1 分段策略

1. **优先按段落分割** (`\n\n`)
2. **超长段落按句子分割** (`。`)
3. **支持重叠** (overlap) 防止上下文丢失
4. **智能截断**：尽量在句号或换行处截断

### 4.2 合并策略

1. **去除重复的overlap部分**
2. **在句号处匹配**：如果overlap部分匹配，跳过重复
3. **保持段落结构**：用 `\n\n` 连接段落

### 4.3 分段参数

- `chunk_size`: 默认 2000 字符
- `chunk_overlap`: 默认 200 字符

## 五、Prompt管理与调用

### 5.1 Prompt设计原则

1. **明确禁止润色**：明确说明只纠错，不改变风格
2. **具体规则**：列出允许和禁止的操作
3. **输出要求**：要求直接输出文本，不添加说明

### 5.2 Prompt结构

```
【核心原则】
- 只纠正错误
- 禁止润色、改写

【具体规则】
- 错别字：修正
- 病句：修正语法
- 拼音转中文：转换
- 标点错误：修正

【输出要求】
直接输出校对后的文本
```

### 5.3 Prompt管理

- 默认Prompt存储在 `PromptManager` 中
- 支持从文件加载自定义Prompt
- 可在运行时修改Prompt

## 六、前端页面结构与组件

### 6.1 组件层次

```
App
├── TextUpload (文本上传)
│   ├── Tabs (粘贴/上传切换)
│   ├── TextField (文本输入)
│   └── FormControl (模型选择)
├── CorrectionProgress (进度展示)
│   └── LinearProgress (进度条)
└── TextComparison (对比展示)
    ├── Tabs (对比/原文/精校切换)
    ├── Grid (左右对比)
    └── Button (导出)
```

### 6.2 主要组件说明

1. **TextUpload**
   - 支持粘贴文本和上传文件
   - 模型提供商选择
   - 提交校对请求

2. **CorrectionProgress**
   - 显示当前进度
   - 进度条可视化
   - 百分比显示

3. **TextComparison**
   - 对比视图：左右分栏，高亮差异
   - 原文视图：显示原始文本
   - 精校视图：显示校对后文本
   - 导出功能：下载精校文本

### 6.3 状态管理

使用React Hooks管理状态：
- `useState`: 文本内容、进度、错误等
- `useEffect`: 加载提供商列表、计算差异等

## 七、关键代码示例

### 7.1 后端：模型适配器使用

```python
from services.correction_service import CorrectionService

# 创建服务实例
service = CorrectionService(
    provider="openai",
    model_name="gpt-4-turbo-preview"
)

# 校对文本
result = await service.correct_text("待校对的文本")
print(result["corrected"])
```

### 7.2 后端：文本分段

```python
from utils.text_splitter import TextSplitter

splitter = TextSplitter(chunk_size=2000, chunk_overlap=200)
chunks = splitter.split(long_text)
corrected_chunks = [await correct(chunk) for chunk in chunks]
merged = splitter.merge(corrected_chunks)
```

### 7.3 前端：API调用

```javascript
import { correctionService } from './services/api'

// 校对文本
const result = await correctionService.correctText(text, {
  provider: 'openai',
  model_name: 'gpt-4-turbo-preview'
})

// 获取差异
const diff = await correctionService.getDiff(original, corrected)
```

### 7.4 前端：差异高亮

```javascript
// 渲染差异片段
{segments.map((segment, index) => (
  <span
    key={index}
    style={{
      backgroundColor: segment.type === 'added' ? '#c8e6c9' : 
                       segment.type === 'deleted' ? '#ffcdd2' : 'transparent',
      textDecoration: segment.type === 'deleted' ? 'line-through' : 'none'
    }}
  >
    {segment.text}
  </span>
))}
```

## 八、错误处理与降级方案

### 8.1 模型调用失败

- **重试机制**：自动重试3次，指数退避
- **降级方案**：重试失败后使用原文
- **错误日志**：记录失败原因

### 8.2 网络错误

- **超时设置**：5分钟超时
- **错误提示**：前端显示友好错误信息
- **重试按钮**：允许用户手动重试

### 8.3 文本处理错误

- **编码错误**：提示使用UTF-8编码
- **文件格式错误**：仅支持TXT文件
- **空文本处理**：返回空结果

## 九、扩展性设计

### 9.1 添加新模型提供商

1. 创建新的Adapter类，继承 `BaseModelAdapter`
2. 实现 `correct_text()` 和 `health_check()` 方法
3. 在 `ModelAdapterFactory` 中注册

### 9.2 自定义分段策略

- 继承 `TextSplitter` 类
- 重写 `split()` 方法
- 在 `CorrectionService` 中使用自定义splitter

### 9.3 自定义Prompt

- 创建Prompt文件
- 使用 `PromptManager(prompt_file="...")` 加载
- 或直接修改 `DEFAULT_PROMPT`

## 十、性能优化

### 10.1 并发处理

- 可以考虑并发处理多个chunk（需要模型支持）
- 当前实现为串行处理，保证顺序

### 10.2 缓存机制

- 可以考虑缓存相同文本的校对结果
- 当前未实现，每次重新校对

### 10.3 分段优化

- 根据模型上下文窗口调整chunk_size
- 根据文本特点调整overlap大小
