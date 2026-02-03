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
  Snackbar,
  Grow,
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
  // Snackbar：open 与内容分离，避免关闭动画期间“回落到 info(蓝色)”导致闪一下
  const [snackbarOpen, setSnackbarOpen] = useState(false)
  const [snackbarMessage, setSnackbarMessage] = useState({ type: 'info', text: '' })

  // Prompt配置（云端 OpenAI/DeepSeek）
  const [prompt, setPrompt] = useState('')
  const [promptFile, setPromptFile] = useState('')
  const [persistPrompt, setPersistPrompt] = useState(true)
  // 本地模型 Prompt（Ollama）
  const [ollamaPrompt, setOllamaPrompt] = useState('')
  const [ollamaPromptFile, setOllamaPromptFile] = useState('')
  const [persistOllamaPrompt, setPersistOllamaPrompt] = useState(true)

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
  // Ollama 预纠错（pycorrector 第一轮 + Ollama 第二轮）
  const [ollamaUsePycorrector, setOllamaUsePycorrector] = useState(true)
  const [ollamaPycorrectorModel, setOllamaPycorrectorModel] = useState('kenlm')
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
    setSnackbarOpen(false)
    try {
      await refreshData(reloadPrompt)
    } catch (error) {
      setSnackbarMessage({ type: 'error', text: `加载配置失败: ${error.message}` })
      setSnackbarOpen(true)
    } finally {
      setLoading(false)
    }
  }

  /** 仅拉取并更新数据，不显示 loading，避免保存后整页闪烁 */
  const refreshData = async (reloadPrompt = false) => {
    const promptData = await correctionService.getPrompt(reloadPrompt)
    setPrompt(promptData.prompt || '')
    setPromptFile(promptData.prompt_file || '')
    setOllamaPrompt(promptData.ollama_prompt ?? promptData.prompt ?? '')
    setOllamaPromptFile(promptData.ollama_prompt_file || '')

    const modelsData = await correctionService.getModels()
    setAllModels(modelsData.models || {})

    let finalProvider = modelsData.default_provider || 'openai'
    let finalModel = modelsData.default_model || ''
    try {
      const configData = await correctionService.getConfig()
      if (configData.chunk_size) setChunkSize(configData.chunk_size)
      if (configData.chunk_overlap) setChunkOverlap(configData.chunk_overlap)
      if (configData.ollama_chunk_size) setOllamaChunkSize(configData.ollama_chunk_size)
      if (configData.ollama_chunk_overlap) setOllamaChunkOverlap(configData.ollama_chunk_overlap)
      if (configData.ollama_use_pycorrector !== undefined) setOllamaUsePycorrector(!!configData.ollama_use_pycorrector)
      if (configData.ollama_pycorrector_model) setOllamaPycorrectorModel(configData.ollama_pycorrector_model)
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

    setDefaultProvider(finalProvider)
    setDefaultModel(finalModel)
    const providerModels = modelsData.models?.[finalProvider] || []
    setAvailableModels(providerModels)
    if (finalModel && !providerModels.includes(finalModel)) {
      setDefaultModel(providerModels.length > 0 ? providerModels[0] : '')
    }
  }

  /** 仅保存云模型相关配置（Prompt + 分段/整段直发/重试） */
  const handleSaveCloudConfig = async () => {
    setSaving(true)
    setSnackbarOpen(false)
    try {
      await correctionService.updatePrompt(prompt, persistPrompt)
      const updateData = {
        chunk_size: chunkSize,
        chunk_overlap: chunkOverlap,
        fast_provider_max_chars: fastProviderMaxChars,
        max_retries: maxRetries,
        retry_delay: retryDelay,
        persist: persistConfig,
      }
      const result = await correctionService.updateConfig(updateData)
      setSnackbarMessage({
        type: persistConfig ? (result.persisted ? 'success' : 'warning') : 'info',
        text: result.message || '云端模型配置已保存',
      })
      setSnackbarOpen(true)
      if (persistPrompt) setPromptFile((await correctionService.getPrompt()).prompt_file || '')
      setTimeout(() => refreshData(), 1000)
    } catch (error) {
      setSnackbarMessage({ type: 'error', text: `保存失败: ${error.message}` })
      setSnackbarOpen(true)
    } finally {
      setSaving(false)
    }
  }

  /** 仅保存模型配置（默认提供商/模型、各提供商模型列表） */
  const handleSaveModelConfig = async () => {
    setSaving(true)
    setSnackbarOpen(false)
    try {
      const updateData = {
        default_provider: defaultProvider,
        default_model: defaultModel,
        openai_models: openaiModels,
        deepseek_models: deepseekModels,
        ollama_models: ollamaModels,
        persist: persistConfig,
      }
      const result = await correctionService.updateConfig(updateData)
      setSnackbarMessage({
        type: persistConfig ? (result.persisted ? 'success' : 'warning') : 'info',
        text: result.message || '模型配置已保存',
      })
      setSnackbarOpen(true)
      setTimeout(() => refreshData(), 1000)
    } catch (error) {
      setSnackbarMessage({ type: 'error', text: `保存失败: ${error.message}` })
      setSnackbarOpen(true)
    } finally {
      setSaving(false)
    }
  }

  /** 仅保存 Ollama 相关配置（Prompt + 分段 + 预纠错） */
  const handleSaveOllamaConfig = async () => {
    setSaving(true)
    setSnackbarOpen(false)
    try {
      await correctionService.updatePrompt(ollamaPrompt, persistOllamaPrompt, 'ollama')
      const updateData = {
        ollama_chunk_size: ollamaChunkSize,
        ollama_chunk_overlap: ollamaChunkOverlap,
        ollama_use_pycorrector: ollamaUsePycorrector,
        ollama_pycorrector_model: ollamaPycorrectorModel,
        persist: persistConfig,
      }
      const result = await correctionService.updateConfig(updateData)
      setSnackbarMessage({
        type: persistConfig ? (result.persisted ? 'success' : 'warning') : 'info',
        text: result.message || 'Ollama 配置已保存',
      })
      setSnackbarOpen(true)
      if (persistOllamaPrompt) setOllamaPromptFile((await correctionService.getPrompt()).ollama_prompt_file || '')
      setTimeout(() => refreshData(), 1000)
    } catch (error) {
      setSnackbarMessage({ type: 'error', text: `保存失败: ${error.message}` })
      setSnackbarOpen(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <Paper
        elevation={0}
        sx={{
          p: { xs: 3, sm: 4 },
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
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

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Box sx={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <Box sx={{ mb: 3, flexShrink: 0 }}>
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
                  label="云模型配置"
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
                  label="Ollama 配置"
                  sx={{
                    fontWeight: tabValue === 2 ? 600 : 400,
                  }}
                />
              </Tabs>
            </Box>

            {/* 云模型配置：左 Prompt 右参数，填满父级剩余高度，不溢出 */}
            {tabValue === 0 && (
              <Box sx={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2, flexShrink: 0 }}>云端模型（OpenAI / DeepSeek）的 Prompt 与处理参数，仅在选择云端提供商时生效。</Typography>
                <Grid container spacing={3} sx={{ flex: 1, minHeight: 0, alignItems: 'stretch' }}>
                  <Grid item xs={12} md={5} sx={{ display: 'flex', flexDirection: 'column', minHeight: 0, order: { xs: 1, md: 0 } }}>
                    <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2, borderColor: 'divider', flex: 1, minHeight: 320, maxHeight: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5, flexShrink: 0 }}>Prompt</Typography>
                      {promptFile && <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, flexShrink: 0 }}>{promptFile}</Typography>}
                      <Box sx={{ flex: 1, minHeight: 180, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                        <TextField
                          fullWidth
                          multiline
                          minRows={8}
                          value={prompt}
                          onChange={(e) => setPrompt(e.target.value)}
                          placeholder="请输入云端模型 Prompt..."
                          size="small"
                          sx={{ flex: 1, minHeight: 0, '& .MuiOutlinedInput-root': { fontFamily: 'monospace', fontSize: '0.8125rem', alignItems: 'flex-start', height: '100%' }, '& textarea': { overflow: 'auto !important' } }}
                        />
                      </Box>
                      <Box sx={{ mt: 1.5, pt: 1.5, borderTop: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
                        <FormControlLabel control={<Switch checked={persistPrompt} onChange={(e) => setPersistPrompt(e.target.checked)} size="small" />} label="持久化到文件" />
                        <Typography variant="caption" color="text.secondary">{persistPrompt ? 'custom_prompt.txt' : '仅内存'}</Typography>
                      </Box>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={7} sx={{ display: 'flex', flexDirection: 'column', minHeight: 0, order: { xs: 2, md: 0 }, mt: { xs: 2, md: 0 } }}>
                    <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2, borderColor: 'divider', flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
                      <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, color: 'text.secondary' }}>分段（仅云端）</Typography>
                        <Grid container spacing={2}>
                          <Grid item xs={12} sm={6}>
                            <TextField fullWidth type="number" label="分段大小" value={chunkSize} onChange={(e) => setChunkSize(parseInt(e.target.value) || 2000)} inputProps={{ min: 100, max: 10000 }} helperText="建议 1000-5000 字符" />
                          </Grid>
                          <Grid item xs={12} sm={6}>
                            <TextField fullWidth type="number" label="分段重叠" value={chunkOverlap} onChange={(e) => setChunkOverlap(parseInt(e.target.value) || 200)} inputProps={{ min: 0, max: chunkSize }} helperText={`0-${chunkSize}`} />
                          </Grid>
                        </Grid>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, mt: 2, color: 'text.secondary' }}>整段与重试</Typography>
                        <Grid container spacing={2}>
                          <Grid item xs={12} sm={6}>
                            <TextField fullWidth type="number" label="整段直发阈值（字符）" value={fastProviderMaxChars} onChange={(e) => setFastProviderMaxChars(parseInt(e.target.value) || 10000)} inputProps={{ min: 1000, max: 50000 }} helperText="≤ 该长度时整段发送" />
                          </Grid>
                          <Grid item xs={12} sm={6}>
                            <TextField fullWidth type="number" label="最大重试次数" value={maxRetries} onChange={(e) => setMaxRetries(parseInt(e.target.value) || 3)} inputProps={{ min: 0, max: 10 }} helperText="建议 1-5" />
                          </Grid>
                          <Grid item xs={12} sm={6}>
                            <TextField fullWidth type="number" step="0.1" label="重试延迟（秒）" value={retryDelay} onChange={(e) => setRetryDelay(parseFloat(e.target.value) || 1.0)} inputProps={{ min: 0.1, max: 10, step: 0.1 }} helperText="建议 0.5-5" />
                          </Grid>
                          <Grid item xs={12} sm={6} sx={{ display: 'flex', alignItems: 'center' }}>
                            <FormControlLabel control={<Switch checked={persistConfig} onChange={(e) => setPersistConfig(e.target.checked)} />} label="持久化到 .env" />
                          </Grid>
                        </Grid>
                      </Box>
                      <Box sx={{ pt: 2, flexShrink: 0, borderTop: 1, borderColor: 'divider' }}>
                        <Button variant="contained" startIcon={<SaveIcon />} onClick={handleSaveCloudConfig} disabled={saving}>
                          {saving ? '保存中...' : '保存云模型配置'}
                        </Button>
                      </Box>
                    </Paper>
                  </Grid>
                </Grid>
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
                    <FormControlLabel control={<Switch checked={persistConfig} onChange={(e) => setPersistConfig(e.target.checked)} />} label="持久化到 .env" />
                    <Typography variant="caption" sx={{ display: 'block', mt: 0.5, color: 'text.secondary' }}>
                      {persistConfig ? '配置会写入 .env，重启后生效' : '仅运行时生效'}
                    </Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Button variant="contained" startIcon={<SaveIcon />} onClick={handleSaveModelConfig} disabled={saving} sx={{ mt: 2 }}>
                      {saving ? '保存中...' : '保存模型配置'}
                    </Button>
                  </Grid>
                </Grid>
              </Box>
            )}

            {/* Ollama 配置：左 Prompt 右参数，填满父级剩余高度，不溢出 */}
            {tabValue === 2 && (
              <Box sx={{ flex: 1, minHeight: 0, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2, flexShrink: 0 }}>本地模型（Ollama）的 Prompt 与处理参数，仅在选择 Ollama 时生效。</Typography>
                <Grid container spacing={3} sx={{ flex: 1, minHeight: 0, alignItems: 'stretch' }}>
                  <Grid item xs={12} md={5} sx={{ display: 'flex', flexDirection: 'column', minHeight: 0, order: { xs: 1, md: 0 } }}>
                    <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2, borderColor: 'divider', flex: 1, minHeight: 320, maxHeight: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5, flexShrink: 0 }}>Prompt</Typography>
                      {ollamaPromptFile ? <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, flexShrink: 0 }}>{ollamaPromptFile}</Typography> : <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, flexShrink: 0 }}>未配置时与云端共用</Typography>}
                      <Box sx={{ flex: 1, minHeight: 180, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                        <TextField
                          fullWidth
                          multiline
                          minRows={8}
                          value={ollamaPrompt}
                          onChange={(e) => setOllamaPrompt(e.target.value)}
                          placeholder="Ollama 专用 Prompt（可与云端不同）..."
                          size="small"
                          sx={{ flex: 1, minHeight: 0, '& .MuiOutlinedInput-root': { fontFamily: 'monospace', fontSize: '0.8125rem', alignItems: 'flex-start', height: '100%' }, '& textarea': { overflow: 'auto !important' } }}
                        />
                      </Box>
                      <Box sx={{ mt: 1.5, pt: 1.5, borderTop: 1, borderColor: 'divider', display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
                        <FormControlLabel control={<Switch checked={persistOllamaPrompt} onChange={(e) => setPersistOllamaPrompt(e.target.checked)} size="small" />} label="持久化到文件" />
                        <Typography variant="caption" color="text.secondary">{persistOllamaPrompt ? 'ollama_custom_prompt.txt' : '仅内存'}</Typography>
                      </Box>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={7} sx={{ display: 'flex', flexDirection: 'column', minHeight: 0, order: { xs: 2, md: 0 }, mt: { xs: 2, md: 0 } }}>
                    <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 2, borderColor: 'divider', flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
                      <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, color: 'text.secondary' }}>分段（仅 Ollama）</Typography>
                        <Grid container spacing={2}>
                          <Grid item xs={12} sm={6}>
                            <TextField fullWidth type="number" label="分段大小" value={ollamaChunkSize} onChange={(e) => setOllamaChunkSize(parseInt(e.target.value) || 800)} inputProps={{ min: 100, max: 2000 }} helperText="32B+16GB 建议 800-1000" />
                          </Grid>
                          <Grid item xs={12} sm={6}>
                            <TextField fullWidth type="number" label="分段重叠" value={ollamaChunkOverlap} onChange={(e) => setOllamaChunkOverlap(parseInt(e.target.value) || 100)} inputProps={{ min: 0, max: ollamaChunkSize }} helperText={`0-${ollamaChunkSize}`} />
                          </Grid>
                        </Grid>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5, mt: 2, color: 'text.secondary' }}>预纠错（pycorrector 第一轮 + Ollama 第二轮）</Typography>
                        <Grid container spacing={2}>
                          <Grid item xs={12} sm={6} sx={{ display: 'flex', alignItems: 'center' }}>
                            <FormControlLabel control={<Switch checked={ollamaUsePycorrector} onChange={(e) => setOllamaUsePycorrector(e.target.checked)} />} label="启用 pycorrector 预纠错" />
                          </Grid>
                          <Grid item xs={12} sm={6}>
                            <FormControl fullWidth>
                              <InputLabel>预纠错模型</InputLabel>
                              <Select value={ollamaPycorrectorModel} label="预纠错模型" onChange={(e) => setOllamaPycorrectorModel(e.target.value)}>
                                <MenuItem value="kenlm">kenlm（轻量）</MenuItem>
                                <MenuItem value="macbert">macbert</MenuItem>
                                <MenuItem value="gpt">gpt</MenuItem>
                              </Select>
                            </FormControl>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>kenlm 轻量；macbert/gpt 需更多资源</Typography>
                          </Grid>
                          <Grid item xs={12} sm={6} sx={{ display: 'flex', alignItems: 'center' }}>
                            <FormControlLabel control={<Switch checked={persistConfig} onChange={(e) => setPersistConfig(e.target.checked)} />} label="持久化到 .env" />
                          </Grid>
                        </Grid>
                      </Box>
                      <Box sx={{ pt: 2, flexShrink: 0, borderTop: 1, borderColor: 'divider' }}>
                        <Button variant="contained" startIcon={<SaveIcon />} onClick={handleSaveOllamaConfig} disabled={saving}>
                          {saving ? '保存中...' : '保存 Ollama 配置'}
                        </Button>
                      </Box>
                    </Paper>
                  </Grid>
                </Grid>
              </Box>
            )}
          </Box>
        )}
      </Paper>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={2000}
        onClose={(_, reason) => {
          if (reason === 'clickaway') return
          setSnackbarOpen(false)
        }}
        // 使用 Grow：原位淡入+微缩放，无位移，避免滑动导致的跳动
        TransitionComponent={Grow}
        TransitionProps={{
          timeout: { enter: 240, exit: 180 },
          style: { transformOrigin: 'center top' },
        }}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        sx={{
          '&.MuiSnackbar-root': {
            top: { xs: 76, sm: 88 },
          },
        }}
      >
        <Alert
          severity={snackbarMessage.type || 'info'}
          onClose={() => setSnackbarOpen(false)}
          variant="filled"
          sx={{
            width: '100%',
            minWidth: 320,
            maxWidth: 'min(720px, calc(100vw - 32px))',
            borderRadius: 2,
            boxShadow: '0 10px 30px rgba(0, 0, 0, 0.18)',
            // 关闭按钮不要出现默认蓝色 ripple/focus 闪烁
            '& .MuiAlert-action .MuiIconButton-root': {
              color: 'inherit',
              borderRadius: 999,
            },
            '& .MuiAlert-action .MuiTouchRipple-root': {
              display: 'none',
            },
          }}
        >
          {snackbarMessage.text}
        </Alert>
      </Snackbar>
    </Box>
  )
}

export default SettingsPage
