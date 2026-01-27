import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5分钟超时
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
}
