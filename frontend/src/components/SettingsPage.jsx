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
  const [persistPrompt, setPersistPrompt] = useState(true)

  // 模型配置
  const [allModels, setAllModels] = useState({})
  const [defaultProvider, setDefaultProvider] = useState('openai')
  const [defaultModel, setDefaultModel] = useState('')
  const [openaiModels, setOpenaiModels] = useState('')
  const [deepseekModels, setDeepseekModels] = useState('')
  const [ollamaModels, setOllamaModels] = useState('')
  const [availableModels, setAvailableModels] = useState([]) // 当前提供商可用的模型列表

  // 文本分段配置
  const [chunkSize, setChunkSize] = useState(2000)
  const [chunkOverlap, setChunkOverlap] = useState(200)
  // Ollama专用分段配置
  const [ollamaChunkSize, setOllamaChunkSize] = useState(800)
  const [ollamaChunkOverlap, setOllamaChunkOverlap] = useState(100)
  // 云端大模型整段直发阈值
  const [fastProviderMaxChars, setFastProviderMaxChars] = useState(10000)

  // 重试配置
  const [maxRetries, setMaxRetries] = useState(3)
  const [retryDelay, setRetryDelay] = useState(1.0)

  // 持久化选项
  const [persistConfig, setPersistConfig] = useState(true)

  useEffect(() => {
    loadSettings()
  }, [])

  // 当提供商或模型列表变化时，更新可用模型列表
  useEffect(() => {
    let models = []
    if (defaultProvider === 'openai' && openaiModels) {
      models = openaiModels.split(',').map(m => m.trim()).filter(m => m)
    } else if (defaultProvider === 'deepseek' && deepseekModels) {
      models = deepseekModels.split(',').map(m => m.trim()).filter(m => m)
    } else if (defaultProvider === 'ollama' && ollamaModels) {
      models = ollamaModels.split(',').map(m => m.trim()).filter(m => m)
    }
    
    // 如果从 API 获取的模型列表存在，优先使用
    let finalModels = []
    if (allModels[defaultProvider] && allModels[defaultProvider].length > 0) {
      finalModels = allModels[defaultProvider]
    } else if (models.length > 0) {
      finalModels = models
    }
    
    setAvailableModels(finalModels)
    
    // 如果当前选择的模型不在可用列表中，重置
    if (defaultModel && !finalModels.includes(defaultModel)) {
      if (finalModels.length > 0) {
        setDefaultModel(finalModels[0])
      } else {
        setDefaultModel('')
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [defaultProvider, openaiModels, deepseekModels, ollamaModels, allModels])

  const loadSettings = async (reloadPrompt = false) => {
    setLoading(true)
    setMessage({ type: '', text: '' })
    try {
      // 加载Prompt（如果reloadPrompt为true，则重新从文件加载）
      const promptData = await correctionService.getPrompt(reloadPrompt)
      setPrompt(promptData.prompt || '')
      setPromptFile(promptData.prompt_file || '')

      // 加载模型配置
      const modelsData = await correctionService.getModels()
      setAllModels(modelsData.models || {})
      
      // 加载系统配置
      let finalProvider = modelsData.default_provider || 'openai'
      let finalModel = modelsData.default_model || ''
      
      try {
        const configData = await correctionService.getConfig()
        if (configData.chunk_size) setChunkSize(configData.chunk_size)
        if (configData.chunk_overlap) setChunkOverlap(configData.chunk_overlap)
        if (configData.ollama_chunk_size) setOllamaChunkSize(configData.ollama_chunk_size)
        if (configData.ollama_chunk_overlap) setOllamaChunkOverlap(configData.ollama_chunk_overlap)
        if (configData.fast_provider_max_chars) setFastProviderMaxChars(configData.fast_provider_max_chars)
        if (configData.max_retries) setMaxRetries(configData.max_retries)
        if (configData.retry_delay) setRetryDelay(configData.retry_delay)
        if (configData.default_provider) finalProvider = configData.default_provider
        if (configData.default_model) finalModel = configData.default_model
        if (configData.openai_models) setOpenaiModels(configData.openai_models)
        if (configData.deepseek_models) setDeepseekModels(configData.deepseek_models)
        if (configData.ollama_models) setOllamaModels(configData.ollama_models)
      } catch (error) {
        console.warn('获取系统配置失败，使用默认值:', error)
      }
      
      // 设置默认提供商和模型
      setDefaultProvider(finalProvider)
      setDefaultModel(finalModel)
      
      // 更新可用模型列表
      const providerModels = modelsData.models?.[finalProvider] || []
      setAvailableModels(providerModels)
      
      // 如果当前模型不在新提供商的模型列表中，重置为空或选择第一个
      if (finalModel && !providerModels.includes(finalModel)) {
        setDefaultModel(providerModels.length > 0 ? providerModels[0] : '')
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
      const result = await correctionService.updatePrompt(prompt, persistPrompt)
      setMessage({ 
        type: persistPrompt ? (result.persisted ? 'success' : 'warning') : 'info',
        text: result.message || 'Prompt已保存'
      })
      
      // 如果持久化成功，更新prompt_file显示
      if (persistPrompt && result.prompt_file) {
        setPromptFile(result.prompt_file)
      }
      
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

  const handleSaveConfig = async () => {
    setSaving(true)
    setMessage({ type: '', text: '' })
    try {
      const updateData = {
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
        ollama_chunk_size: ollamaChunkSize,
        ollama_chunk_overlap: ollamaChunkOverlap,
        fast_provider_max_chars: fastProviderMaxChars,
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
        elevation={0}
        sx={{
          p: { xs: 3, sm: 4 },
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          transition: 'all 0.2s ease-out',
          '&:hover': {
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
          },
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            系统配置
          </Typography>
          <Button
            startIcon={<RefreshIcon />}
            onClick={() => loadSettings(true)}
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
                
                <Box sx={{ mb: 2 }}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={persistPrompt}
                        onChange={(e) => setPersistPrompt(e.target.checked)}
                      />
                    }
                    label="持久化保存Prompt"
                  />
                  <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
                    {persistPrompt 
                      ? '✅ Prompt将保存到文件并更新.env配置（重启后也会生效）'
                      : '✅ Prompt立即生效，但重启后恢复为配置文件中的Prompt'}
                  </Typography>
                </Box>
                
                <Button
                  variant="contained"
                  startIcon={<SaveIcon />}
                  onClick={handleSavePrompt}
                  disabled={saving}
                >
                  {saving ? '保存中...' : '保存Prompt'}
                </Button>
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
                        onChange={(e) => {
                          const newProvider = e.target.value
                          setDefaultProvider(newProvider)
                          // 更新可用模型列表
                          const providerModels = allModels[newProvider] || []
                          setAvailableModels(providerModels)
                          // 如果当前模型不在新提供商的模型列表中，重置为第一个或空
                          if (!providerModels.includes(defaultModel)) {
                            setDefaultModel(providerModels.length > 0 ? providerModels[0] : '')
                          }
                        }}
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
                    <FormControl fullWidth>
                      <InputLabel>模型名称</InputLabel>
                      <Select 
                        value={defaultModel} 
                        label="模型名称"
                        onChange={(e) => setDefaultModel(e.target.value)}
                        disabled={availableModels.length === 0}
                      >
                        {availableModels.length === 0 ? (
                          <MenuItem disabled>
                            请先配置该提供商的模型列表
                          </MenuItem>
                        ) : (
                          availableModels.map((model) => (
                            <MenuItem key={model} value={model}>
                              {model}
                            </MenuItem>
                          ))
                        )}
                      </Select>
                      {availableModels.length === 0 && (
                        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                          请先在下方配置 {defaultProvider} 的模型列表
                        </Typography>
                      )}
                    </FormControl>
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
                <Grid container spacing={2}>
                  {/* 通用处理配置：分段 + 整段直发 + 重试 */}
                  <Grid item xs={12} md={4}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      文本分段大小
                    </Typography>
                    <TextField
                      fullWidth
                      type="number"
                      value={chunkSize}
                      onChange={(e) => setChunkSize(parseInt(e.target.value) || 2000)}
                      inputProps={{ min: 100, max: 10000 }}
                      helperText="建议: 1000-5000"
                    />
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      分段重叠大小
                    </Typography>
                    <TextField
                      fullWidth
                      type="number"
                      value={chunkOverlap}
                      onChange={(e) => setChunkOverlap(parseInt(e.target.value) || 200)}
                      inputProps={{ min: 0, max: chunkSize }}
                      helperText={`建议: 0-${chunkSize}`}
                    />
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      整段直发阈值（字符）
                    </Typography>
                    <TextField
                      fullWidth
                      type="number"
                      value={fastProviderMaxChars}
                      onChange={(e) => setFastProviderMaxChars(parseInt(e.target.value) || 10000)}
                      inputProps={{ min: 1000, max: 50000 }}
                      helperText="OpenAI / DeepSeek 建议: 6000-12000"
                    />
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      最大重试次数
                    </Typography>
                    <TextField
                      fullWidth
                      type="number"
                      value={maxRetries}
                      onChange={(e) => setMaxRetries(parseInt(e.target.value) || 3)}
                      inputProps={{ min: 0, max: 10 }}
                      helperText="建议: 1-5"
                    />
                  </Grid>

                  <Grid item xs={12} md={4}>
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
                      helperText="建议: 0.5-5.0"
                    />
                  </Grid>

                  {/* Ollama 专用分段配置 */}
                  <Grid item xs={12}>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="subtitle1" sx={{ mb: 1.25, fontWeight: 600, color: 'primary.main' }}>
                      Ollama 专用分段配置
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                      针对本地部署大模型（如 32B），显存有限时建议使用较小分段，仅在提供商为 Ollama 时生效
                    </Typography>
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      Ollama 分段大小
                    </Typography>
                    <TextField
                      fullWidth
                      type="number"
                      value={ollamaChunkSize}
                      onChange={(e) => setOllamaChunkSize(parseInt(e.target.value) || 800)}
                      inputProps={{ min: 100, max: 2000 }}
                      helperText="32B + 16GB 建议: 800-1000"
                    />
                  </Grid>

                  <Grid item xs={12} md={4}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      Ollama 分段重叠大小
                    </Typography>
                    <TextField
                      fullWidth
                      type="number"
                      value={ollamaChunkOverlap}
                      onChange={(e) => setOllamaChunkOverlap(parseInt(e.target.value) || 100)}
                      inputProps={{ min: 0, max: ollamaChunkSize }}
                      helperText={`建议: 0-${ollamaChunkSize}（约10-15%）`}
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
                      label="持久化到.env文件"
                    />
                    <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
                      {persistConfig 
                        ? '✅ 配置立即生效，同时保存到.env文件（重启后也会生效）'
                        : '✅ 配置立即生效，但重启后恢复为.env文件中的值'}
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
