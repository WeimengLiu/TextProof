import React, { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  Divider,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  FormControlLabel,
  Switch,
} from '@mui/material'
import { Save as SaveIcon, Refresh as RefreshIcon } from '@mui/icons-material'
import { correctionService } from '../services/api'

function SettingsPage() {
  const [tabValue, setTabValue] = useState(0)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState({ type: '', text: '' })

  // Prompt配置
  const [prompt, setPrompt] = useState('')
  const [promptFile, setPromptFile] = useState('')

  // 模型配置
  const [allModels, setAllModels] = useState({})
  const [defaultProvider, setDefaultProvider] = useState('openai')
  const [defaultModel, setDefaultModel] = useState('')
  const [openaiModels, setOpenaiModels] = useState('')
  const [deepseekModels, setDeepseekModels] = useState('')
  const [ollamaModels, setOllamaModels] = useState('')

  // 文本分段配置
  const [chunkSize, setChunkSize] = useState(2000)
  const [chunkOverlap, setChunkOverlap] = useState(200)

  // 重试配置
  const [maxRetries, setMaxRetries] = useState(3)
  const [retryDelay, setRetryDelay] = useState(1.0)

  // 持久化选项
  const [persistConfig, setPersistConfig] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    setLoading(true)
    setMessage({ type: '', text: '' })
    try {
      // 加载Prompt
      const promptData = await correctionService.getPrompt()
      setPrompt(promptData.prompt || '')
      setPromptFile(promptData.prompt_file || '')

      // 加载模型配置
      const modelsData = await correctionService.getModels()
      setAllModels(modelsData.models || {})
      setDefaultProvider(modelsData.default_provider || 'openai')
      setDefaultModel(modelsData.default_model || '')

      // 加载系统配置
      try {
        const configData = await correctionService.getConfig()
        if (configData.chunk_size) setChunkSize(configData.chunk_size)
        if (configData.chunk_overlap) setChunkOverlap(configData.chunk_overlap)
        if (configData.max_retries) setMaxRetries(configData.max_retries)
        if (configData.retry_delay) setRetryDelay(configData.retry_delay)
        if (configData.default_provider) setDefaultProvider(configData.default_provider)
        if (configData.default_model) setDefaultModel(configData.default_model)
        if (configData.openai_models) setOpenaiModels(configData.openai_models)
        if (configData.deepseek_models) setDeepseekModels(configData.deepseek_models)
        if (configData.ollama_models) setOllamaModels(configData.ollama_models)
      } catch (error) {
        console.warn('获取系统配置失败，使用默认值:', error)
      }
    } catch (error) {
      setMessage({ type: 'error', text: `加载配置失败: ${error.message}` })
    } finally {
      setLoading(false)
    }
  }

  const handleSavePrompt = async () => {
    setSaving(true)
    setMessage({ type: '', text: '' })
    try {
      await correctionService.updatePrompt(prompt)
      setMessage({ type: 'success', text: 'Prompt已保存（运行时有效，重启后恢复为配置文件中的Prompt）' })
    } catch (error) {
      setMessage({ type: 'error', text: `保存失败: ${error.message}` })
    } finally {
      setSaving(false)
    }
  }

  const handleSaveConfig = async () => {
    setSaving(true)
    setMessage({ type: '', text: '' })
    try {
      const updateData = {
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
        max_retries: maxRetries,
        retry_delay: retryDelay,
        default_provider: defaultProvider,
        default_model: defaultModel,
        openai_models: openaiModels,
        deepseek_models: deepseekModels,
        ollama_models: ollamaModels,
        persist: persistConfig,
      }
      
      const result = await correctionService.updateConfig(updateData)
      setMessage({ 
        type: persistConfig ? (result.persisted ? 'success' : 'warning') : 'info', 
        text: result.message || (persistConfig 
          ? '配置已保存到.env文件，请重启服务使配置生效'
          : '配置已更新（运行时有效，重启后恢复）')
      })
      
      // 重新加载配置
      setTimeout(() => {
        loadSettings()
      }, 1000)
    } catch (error) {
      setMessage({ type: 'error', text: `保存失败: ${error.message}` })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Box>
      <Paper
        sx={{
          p: { xs: 2.5, sm: 3.5 },
          transition: 'all 0.2s ease-out',
          '&:hover': {
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
          },
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            系统配置
          </Typography>
          <Button
            startIcon={<RefreshIcon />}
            onClick={loadSettings}
            disabled={loading}
            size="small"
          >
            刷新
          </Button>
        </Box>

        {message.text && (
          <Alert severity={message.type || 'info'} sx={{ mb: 3 }}>
            {message.text}
          </Alert>
        )}

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <Box sx={{ mb: 3 }}>
              <Tabs
                value={tabValue}
                onChange={(e, v) => setTabValue(v)}
                sx={{
                  '& .MuiTabs-indicator': {
                    bgcolor: 'primary.main',
                  },
                }}
              >
                <Tab
                  label="Prompt配置"
                  sx={{
                    fontWeight: tabValue === 0 ? 600 : 400,
                  }}
                />
                <Tab
                  label="模型配置"
                  sx={{
                    fontWeight: tabValue === 1 ? 600 : 400,
                  }}
                />
                <Tab
                  label="处理配置"
                  sx={{
                    fontWeight: tabValue === 2 ? 600 : 400,
                  }}
                />
              </Tabs>
            </Box>

            {/* Prompt配置 */}
            {tabValue === 0 && (
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                  Prompt文件路径
                </Typography>
                <TextField
                  fullWidth
                  value={promptFile || '使用默认Prompt'}
                  disabled
                  sx={{ mb: 3 }}
                  helperText="如需修改，请在.env文件中设置PROMPT_FILE"
                />

                <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                  Prompt内容
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  rows={15}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="请输入Prompt内容..."
                  sx={{
                    mb: 3,
                    '& .MuiOutlinedInput-root': {
                      fontFamily: 'monospace',
                      fontSize: '0.875rem',
                    },
                  }}
                />
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={handleSavePrompt}
                  disabled={saving}
                >
                  {saving ? '保存中...' : '保存Prompt'}
                </Button>
                <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
                  注意：此修改仅在运行时有效，重启服务后会恢复为配置文件中的Prompt
                </Typography>
              </Box>
            )}

            {/* 模型配置 */}
            {tabValue === 1 && (
              <Box>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      默认模型提供商
                    </Typography>
                    <FormControl fullWidth>
                      <InputLabel>提供商</InputLabel>
                      <Select 
                        value={defaultProvider} 
                        label="提供商"
                        onChange={(e) => setDefaultProvider(e.target.value)}
                      >
                        {Object.keys(allModels).map((p) => (
                          <MenuItem key={p} value={p}>
                            {p}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      默认模型名称
                    </Typography>
                    <TextField
                      fullWidth
                      value={defaultModel}
                      onChange={(e) => setDefaultModel(e.target.value)}
                      placeholder="如: gpt-4-turbo-preview"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
                      OpenAI 模型列表
                    </Typography>
                    <TextField
                      fullWidth
                      value={openaiModels}
                      onChange={(e) => setOpenaiModels(e.target.value)}
                      placeholder="用逗号分隔，如: gpt-4-turbo-preview,gpt-4,gpt-3.5-turbo"
                      helperText="用逗号分隔多个模型名称"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
                      DeepSeek 模型列表
                    </Typography>
                    <TextField
                      fullWidth
                      value={deepseekModels}
                      onChange={(e) => setDeepseekModels(e.target.value)}
                      placeholder="用逗号分隔，如: deepseek-chat,deepseek-coder"
                      helperText="用逗号分隔多个模型名称"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
                      Ollama 模型列表
                    </Typography>
                    <TextField
                      fullWidth
                      value={ollamaModels}
                      onChange={(e) => setOllamaModels(e.target.value)}
                      placeholder="用逗号分隔，如: llama2,llama3,qwen"
                      helperText="用逗号分隔多个模型名称"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Button
                      variant="contained"
                      startIcon={<SaveIcon />}
                      onClick={handleSaveConfig}
                      disabled={saving}
                      sx={{ mt: 2 }}
                    >
                      {saving ? '保存中...' : '保存模型配置'}
                    </Button>
                  </Grid>
                </Grid>
              </Box>
            )}

            {/* 处理配置 */}
            {tabValue === 2 && (
              <Box>
                <Grid container spacing={3}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      文本分段大小
                    </Typography>
                    <TextField
                      fullWidth
                      type="number"
                      value={chunkSize}
                      onChange={(e) => setChunkSize(parseInt(e.target.value) || 2000)}
                      inputProps={{ min: 100, max: 10000 }}
                      helperText="建议范围: 1000-5000"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      分段重叠大小
                    </Typography>
                    <TextField
                      fullWidth
                      type="number"
                      value={chunkOverlap}
                      onChange={(e) => setChunkOverlap(parseInt(e.target.value) || 200)}
                      inputProps={{ min: 0, max: chunkSize }}
                      helperText={`建议范围: 0-${chunkSize}`}
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      最大重试次数
                    </Typography>
                    <TextField
                      fullWidth
                      type="number"
                      value={maxRetries}
                      onChange={(e) => setMaxRetries(parseInt(e.target.value) || 3)}
                      inputProps={{ min: 0, max: 10 }}
                      helperText="建议范围: 1-5"
                    />
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      重试延迟（秒）
                    </Typography>
                    <TextField
                      fullWidth
                      type="number"
                      step="0.1"
                      value={retryDelay}
                      onChange={(e) => setRetryDelay(parseFloat(e.target.value) || 1.0)}
                      inputProps={{ min: 0.1, max: 10, step: 0.1 }}
                      helperText="建议范围: 0.5-5.0"
                    />
                  </Grid>

                  <Grid item xs={12}>
                    <Divider sx={{ my: 2 }} />
                    <FormControlLabel
                      control={
                        <Switch
                          checked={persistConfig}
                          onChange={(e) => setPersistConfig(e.target.checked)}
                        />
                      }
                      label="持久化到.env文件（重启后生效）"
                    />
                    <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
                      {persistConfig 
                        ? '配置将保存到.env文件，重启服务后生效'
                        : '配置仅在运行时有效，重启后恢复为.env文件中的值'}
                    </Typography>
                  </Grid>

                  <Grid item xs={12}>
                    <Button
                      variant="contained"
                      startIcon={<SaveIcon />}
                      onClick={handleSaveConfig}
                      disabled={saving}
                      sx={{ mt: 2 }}
                    >
                      {saving ? '保存中...' : '保存处理配置'}
                    </Button>
                  </Grid>
                </Grid>
              </Box>
            )}
          </>
        )}
      </Paper>
    </Box>
  )
}

export default SettingsPage
