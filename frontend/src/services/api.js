import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 1800000, // 30分钟超时（针对大文本和慢模型）
})

export const correctionService = {
  /**
   * 校对文本
   * @param {string} text - 待校对的文本
   * @param {object} options - 选项
   * @param {function} progressCallback - 进度回调
   */
  async correctText(text, options = {}, progressCallback = null) {
    try {
      const response = await api.post('/api/correct', {
        text,
        ...options,
      })

      // 注意：由于HTTP请求是一次性的，无法实时获取进度
      // 这里使用模拟进度（实际项目中可以使用WebSocket或Server-Sent Events）
      if (progressCallback) {
        progressCallback(response.data.total_chunks, response.data.total_chunks)
      }

      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || '校对失败')
      } else if (error.request) {
        throw new Error('无法连接到服务器，请检查后端服务是否运行')
      } else {
        throw new Error(error.message || '校对失败')
      }
    }
  },

  /**
   * 上传文件进行校对
   * @param {File} file - 文件对象
   * @param {object} options - 选项
   */
  async correctFile(file, options = {}) {
    const formData = new FormData()
    formData.append('file', file)

    const params = new URLSearchParams()
    if (options.provider) params.append('provider', options.provider)
    if (options.model_name) params.append('model_name', options.model_name)
    if (options.async_task !== undefined) params.append('async_task', options.async_task)

    try {
      const response = await api.post(`/api/correct/file?${params.toString()}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || '校对失败')
      } else if (error.request) {
        throw new Error('无法连接到服务器')
      } else {
        throw new Error(error.message || '校对失败')
      }
    }
  },

  /**
   * 获取文本差异
   * @param {string} original - 原文
   * @param {string} corrected - 校对后的文本
   */
  async getDiff(original, corrected) {
    try {
      const response = await api.post('/api/diff', {
        text: original,
        corrected,
      })

      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || '差异计算失败')
      } else {
        throw new Error(error.message || '差异计算失败')
      }
    }
  },

  /**
   * 健康检查
   */
  async healthCheck(provider = null, modelName = null) {
    const params = new URLSearchParams()
    if (provider) params.append('provider', provider)
    if (modelName) params.append('model_name', modelName)

    try {
      const response = await api.get(`/health?${params.toString()}`)
      return response.data
    } catch (error) {
      return { available: false, status: 'error' }
    }
  },

  /**
   * 获取可用的模型提供商
   */
  async getProviders() {
    try {
      const response = await api.get('/api/providers')
      return response.data
    } catch (error) {
      return { providers: [], default: 'openai' }
    }
  },

  /**
   * 获取可用的模型列表
   * @param {string} provider - 模型提供商（可选）
   */
  async getModels(provider = null) {
    try {
      const params = provider ? { provider } : {}
      const response = await api.get('/api/models', { params })
      return response.data
    } catch (error) {
      console.error('获取模型列表失败:', error)
      return provider 
        ? { provider, models: [], default: null }
        : { models: {}, default_provider: 'openai', default_model: null }
    }
  },

  /**
   * 获取当前使用的 Prompt（云端 + Ollama 两套）
   * @param {boolean} reload - 是否重新从文件加载（默认false）
   */
  async getPrompt(reload = false) {
    try {
      const response = await api.get('/api/prompt', {
        params: { reload: reload }
      })
      return response.data
    } catch (error) {
      console.error('获取Prompt失败:', error)
      return {
        prompt: '',
        ollama_prompt: '',
        is_custom: false,
        prompt_file: null,
        ollama_is_custom: false,
        ollama_prompt_file: null
      }
    }
  },

  /**
   * 更新 Prompt
   * @param {string} prompt - 新的 Prompt 文本
   * @param {boolean} persist - 是否持久化保存
   * @param {string} [provider] - 'ollama' 表示更新本地模型 Prompt，不传则更新云端 Prompt
   */
  async updatePrompt(prompt, persist = false, provider = null) {
    try {
      const body = { prompt, persist }
      if (provider) body.provider = provider
      const response = await api.post('/api/prompt', body)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || '更新Prompt失败')
      } else {
        throw new Error(error.message || '更新Prompt失败')
      }
    }
  },

  /**
   * 获取系统配置
   */
  async getConfig() {
    try {
      const response = await api.get('/api/config')
      return response.data
    } catch (error) {
      console.error('获取系统配置失败:', error)
      return {}
    }
  },

  /**
   * 更新系统配置
   * @param {object} config - 配置对象
   */
  async updateConfig(config) {
    try {
      const response = await api.post('/api/config', config)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || '更新配置失败')
      } else {
        throw new Error(error.message || '更新配置失败')
      }
    }
  },

  /**
   * 获取所有任务列表
   */
  async getTasks() {
    try {
      const response = await api.get('/api/tasks')
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || '获取任务列表失败')
      } else {
        throw new Error(error.message || '获取任务列表失败')
      }
    }
  },

  /**
   * 获取任务详情
   * @param {string} taskId - 任务ID
   */
  async getTask(taskId) {
    try {
      const response = await api.get(`/api/tasks/${taskId}`)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || '获取任务详情失败')
      } else {
        throw new Error(error.message || '获取任务详情失败')
      }
    }
  },

  /**
   * 获取所有比对结果列表
   * 支持分页：{ limit, offset }
   */
  async getResults(options = {}) {
    try {
      const params = {}
      if (options.limit !== undefined) params.limit = options.limit
      if (options.offset !== undefined) params.offset = options.offset
      const response = await api.get('/api/results', { params })
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || '获取结果列表失败')
      } else {
        throw new Error(error.message || '获取结果列表失败')
      }
    }
  },

  /**
   * 获取比对结果详情
   * @param {string} resultId - 结果ID
   * @param {object} options - { include_text?: boolean }
   */
  async getResult(resultId, options = {}) {
    try {
      const includeText = options.include_text !== undefined ? options.include_text : false
      const response = await api.get(`/api/results/${resultId}`, {
        params: { include_text: includeText },
      })
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || '获取结果详情失败')
      } else {
        throw new Error(error.message || '获取结果详情失败')
      }
    }
  },

  /**
   * 生成下载URL（后端应提供流式下载接口）
   * @param {string} resultId - 结果ID
   */
  getResultDownloadUrl(resultId) {
    return `${API_BASE_URL}/api/results/${encodeURIComponent(resultId)}/download`
  },

  /**
   * 删除比对结果
   * @param {string} resultId - 结果ID
   */
  async deleteResult(resultId) {
    try {
      const response = await api.delete(`/api/results/${resultId}`)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || '删除结果失败')
      } else {
        throw new Error(error.message || '删除结果失败')
      }
    }
  },

  /**
   * 获取指定章节的比对结果
   * @param {string} resultId - 结果ID
   * @param {number} chapterIndex - 章节索引
   */
  async getChapterResult(resultId, chapterIndex) {
    try {
      const response = await api.get(`/api/results/${resultId}/chapters/${chapterIndex}`)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || '获取章节结果失败')
      } else {
        throw new Error(error.message || '获取章节结果失败')
      }
    }
  },

  /**
   * 保存“输入框直接校对”的结果到结果列表
   * @param {object} payload - { original, corrected, filename?, provider?, model_name? }
   */
  async saveManualResult(payload) {
    try {
      const response = await api.post('/api/results/manual', payload)
      return response.data
    } catch (error) {
      if (error.response) {
        throw new Error(error.response.data.detail || '保存结果失败')
      } else {
        throw new Error(error.message || '保存结果失败')
      }
    }
  },
}
