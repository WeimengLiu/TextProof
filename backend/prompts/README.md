# Prompt 配置说明

## 使用方式

### 方式1：通过环境变量配置（推荐）

在 `.env` 文件中设置：

```env
PROMPT_FILE=./prompts/custom_prompt.txt
```

### 方式2：使用默认Prompt

如果不设置 `PROMPT_FILE`，系统将使用内置的默认Prompt。

## 自定义Prompt文件

1. 在此目录下创建 `.txt` 文件
2. 编写你的自定义Prompt
3. 在 `.env` 中配置文件路径

## Prompt编写要求

- 必须明确说明只纠正错误，不改变原文风格
- 禁止润色、改写、增删内容
- 要求直接输出校对后的文本，不添加说明

## 示例

参考 `custom_prompt.txt.example` 文件。
