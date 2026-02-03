# Prompt 配置说明

## 两套 Prompt

- **云端模型（OpenAI / DeepSeek）**：使用 `PROMPT_FILE` 指向的文件，默认 `custom_prompt.txt`。
- **本地模型（Ollama）**：使用 `OLLAMA_PROMPT_FILE` 指向的文件（如 `ollama_custom_prompt.txt`）；**不设置则与云端共用同一份 Prompt**，便于针对本地模型单独调优。

## 使用方式

### 方式1：通过环境变量配置（推荐）

在 `.env` 中设置：

```env
PROMPT_FILE=./prompts/custom_prompt.txt
# 可选：Ollama 专用，不设置则与云端相同
OLLAMA_PROMPT_FILE=./prompts/ollama_custom_prompt.txt
```

### 方式2：使用默认 Prompt

若不设置 `PROMPT_FILE`，系统使用内置默认 Prompt；若不设置 `OLLAMA_PROMPT_FILE`，Ollama 使用与云端相同的内容。

## 自定义 Prompt 文件

1. 在此目录下创建 `.txt` 文件（如 `custom_prompt.txt`、`ollama_custom_prompt.txt`）
2. 编写你的自定义 Prompt
3. 在 `.env` 中配置对应路径

## Prompt 编写要求

- 必须明确说明只纠正错误，不改变原文风格
- 禁止润色、改写、增删内容
- 要求直接输出校对后的文本，不添加说明

## 示例

- 云端：参考 `custom_prompt.txt.example`
- Ollama：参考 `ollama_custom_prompt.txt.example`（可与云端不同以便针对本地模型调优）
