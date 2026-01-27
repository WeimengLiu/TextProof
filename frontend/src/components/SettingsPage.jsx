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

  // 文本分段配置
  const [chunkSize, setChunkSize] = useState(2000)
  const [chunkOverlap, setChunkOverlap] = useState(200)

  // 重试配置
  const [maxRetries, setMaxRetries] = useState(3)
  const [retryDelay, setRetryDelay] = useState(1.0)

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

      // 注意：chunk_size, chunk_overlap, max_retries, retry_delay 需要后端API支持
      // 暂时使用默认值
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
      // 注意：需要后端API支持更新这些配置
      // 目前只能更新Prompt
      setMessage({ type: 'info', text: '其他配置项需要修改.env文件并重启服务' })
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
                      <Select value={defaultProvider} label="提供商" disabled>
                        {Object.keys(allModels).map((p) => (
                          <MenuItem key={p} value={p}>
                            {p}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
                      在.env文件中设置DEFAULT_MODEL_PROVIDER
                    </Typography>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" sx={{ mb: 2, color: 'text.secondary' }}>
                      默认模型名称
                    </Typography>
                    <TextField
                      fullWidth
                      value={defaultModel}
                      disabled
                      helperText="在.env文件中设置DEFAULT_MODEL_NAME"
                    />
                  </Grid>

                  {Object.entries(allModels).map(([provider, models]) => (
                    <Grid item xs={12} key={provider}>
                      <Divider sx={{ my: 2 }} />
                      <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
                        {provider.toUpperCase()} 模型列表
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {models.map((model) => (
                          <Chip
                            key={model}
                            label={model}
                            size="small"
                            color={model === defaultModel && provider === defaultProvider ? 'primary' : 'default'}
                          />
                        ))}
                      </Box>
                      <Typography variant="caption" sx={{ display: 'block', mt: 1, color: 'text.secondary' }}>
                        在.env文件中设置{provider.toUpperCase()}_MODELS（逗号分隔）
                      </Typography>
                    </Grid>
                  ))}
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
                      disabled
                      helperText="在.env文件中设置CHUNK_SIZE"
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
                      disabled
                      helperText="在.env文件中设置CHUNK_OVERLAP"
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
                      disabled
                      helperText="在.env文件中设置MAX_RETRIES"
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
                      disabled
                      helperText="在.env文件中设置RETRY_DELAY"
                    />
                  </Grid>
                </Grid>

                <Alert severity="info" sx={{ mt: 3 }}>
                  这些配置项需要修改.env文件并重启后端服务才能生效。
                  当前显示的是默认值，实际值请查看.env文件。
                </Alert>
              </Box>
            )}
          </>
        )}
      </Paper>
    </Box>
  )
}

export default SettingsPage
