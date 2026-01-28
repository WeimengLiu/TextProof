import React, { useState } from 'react'
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Tabs,
  Tab,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
} from '@mui/material'
import { Upload as UploadIcon } from '@mui/icons-material'
import { correctionService } from '../services/api'

// 输入框最大字符数限制（建议使用文件上传处理大文本）
const MAX_TEXT_LENGTH = 50000 // 5万字符

function TextUpload({ 
  onSubmit, 
  onFileSubmit, 
  disabled, 
  inputText, 
  onInputTextChange,
  selectedProvider,
  onProviderChange,
  selectedModelName,
  onModelNameChange,
}) {
  const [tabValue, setTabValue] = useState(0)
  // 如果父组件传入了 inputText 和 onInputTextChange，使用父组件的状态
  // 否则使用组件内部状态（向后兼容）
  const [internalText, setInternalText] = useState('')
  const text = inputText !== undefined ? inputText : internalText
  const setText = onInputTextChange || setInternalText
  const [file, setFile] = useState(null)
  
  // 如果父组件传入了 provider 和 modelName，使用父组件的状态
  // 否则使用组件内部状态（向后兼容）
  const [internalProvider, setInternalProvider] = useState('openai')
  const [internalModelName, setInternalModelName] = useState('')
  const provider = selectedProvider !== undefined ? selectedProvider : internalProvider
  const setProvider = onProviderChange || setInternalProvider
  const modelName = selectedModelName !== undefined ? selectedModelName : internalModelName
  const setModelName = onModelNameChange || setInternalModelName
  
  const [providers, setProviders] = useState([])
  const [models, setModels] = useState([])
  const [loadingProviders, setLoadingProviders] = useState(false)
  const [loadingModels, setLoadingModels] = useState(false)

  React.useEffect(() => {
    loadProviders()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  React.useEffect(() => {
    // 当提供商改变时，加载对应的模型列表
    if (provider && providers.length > 0) {
      loadModels(provider)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider])

  const loadProviders = async () => {
    setLoadingProviders(true)
    try {
      const data = await correctionService.getProviders()
      const providersList = data.providers || []
      setProviders(providersList)
      
      // 只有在没有设置 provider 时才设置默认值
      if (!provider) {
        const defaultProvider = data.default || 'openai'
        setProvider(defaultProvider)
      } else if (provider && providersList.length > 0) {
        // 如果 provider 已设置，加载对应的模型列表
        loadModels(provider)
      }
    } catch (error) {
      console.error('加载提供商失败:', error)
    } finally {
      setLoadingProviders(false)
    }
  }

  const loadModels = async (providerName) => {
    setLoadingModels(true)
    try {
      const data = await correctionService.getModels(providerName)
      const modelList = data.models || []
      setModels(modelList)
      
      // 只有在当前 modelName 不在新列表或为空时，才设置默认值
      if (!modelName || !modelList.includes(modelName)) {
        if (data.default && modelList.includes(data.default)) {
          setModelName(data.default)
        } else if (modelList.length > 0) {
          // 否则选择第一个模型
          setModelName(modelList[0])
        } else {
          setModelName('')
        }
      }
    } catch (error) {
      console.error('加载模型列表失败:', error)
      setModels([])
      // 只有在 modelName 不在空列表时才清空
      if (modelName) {
        setModelName('')
      }
    } finally {
      setLoadingModels(false)
    }
  }

  const handleProviderChange = (newProvider) => {
    setProvider(newProvider)
    // 重置模型名称，等待加载新列表（但如果父组件管理状态，会通过 loadModels 自动设置）
    if (!onModelNameChange) {
      setModelName('')
    }
  }

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0]
    if (selectedFile && selectedFile.name.endsWith('.txt')) {
      setFile(selectedFile)
      // 对于大文件，不在前端全部读取到内存，只提示文件名
      // 如果之前是“粘贴文本”模式，保留已输入的 text，不强制清空
    } else {
      alert('请选择TXT文件')
    }
  }

  const handleSubmit = async () => {
    const options = {
      provider: provider || undefined,
      model_name: modelName || undefined,
    }

    if (tabValue === 0) {
      // 粘贴文本：直接同步执行
      if (!text.trim()) {
        alert('请输入需要校对的文本')
        return
      }
      if (text.length > MAX_TEXT_LENGTH) {
        alert(`文本长度超过限制（${MAX_TEXT_LENGTH.toLocaleString()}字符），请使用文件上传功能处理大文本`)
        return
      }
      if (onSubmit) {
        onSubmit(text, options)
      }
    } else {
      // 文件上传：使用后台任务
      if (!file) {
        alert('请选择要上传的TXT文件')
        return
      }
      
      // 文件上传始终使用后台任务
      try {
        const result = await correctionService.correctFile(file, {
          ...options,
          async_task: true,
        })
        
        if (result.task_id) {
          alert(`任务已创建！任务ID: ${result.task_id}\n请前往"任务进度"页面查看处理状态。`)
          // 可以在这里触发页面跳转到任务进度页面
        }
      } catch (err) {
        alert(`创建任务失败: ${err.message}`)
      }
    }
  }

  return (
    <Paper 
      elevation={0}
      sx={{ 
        p: { xs: 3, sm: 4 },
        mb: 3,
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: 2,
        transition: 'all 0.2s ease-out',
        '&:hover': {
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.06)',
        },
      }}
    >
      <Typography 
        variant="h6" 
        gutterBottom
        sx={{ 
          mb: 3,
          fontWeight: 600,
          color: 'text.primary',
        }}
      >
        输入文本
      </Typography>

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
            label="粘贴文本" 
            sx={{ 
              fontWeight: tabValue === 0 ? 600 : 400,
            }}
          />
          <Tab 
            label="上传文件"
            sx={{ 
              fontWeight: tabValue === 1 ? 600 : 400,
            }}
          />
        </Tabs>
      </Box>

      {tabValue === 0 ? (
        <TextField
          fullWidth
          multiline
          rows={12}
          value={text}
          onChange={(e) => {
            const newValue = e.target.value
            if (newValue.length <= MAX_TEXT_LENGTH) {
              setText(newValue)
            }
          }}
          placeholder="请粘贴需要校对的文本..."
          variant="outlined"
          disabled={disabled}
          helperText={
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>字符数: {text.length.toLocaleString()} / {MAX_TEXT_LENGTH.toLocaleString()}</span>
              {text.length >= MAX_TEXT_LENGTH && (
                <span style={{ color: '#d32f2f', fontSize: '0.75rem' }}>
                  已达到最大长度限制，请使用文件上传处理大文本
                </span>
              )}
            </Box>
          }
          error={text.length >= MAX_TEXT_LENGTH}
          sx={{ 
            mb: 3,
            '& .MuiOutlinedInput-root': {
              fontFamily: 'monospace',
              fontSize: '0.9375rem',
            },
          }}
        />
      ) : (
        <Box sx={{ mb: 3 }}>
          <input
            accept=".txt"
            style={{ display: 'none' }}
            id="file-upload"
            type="file"
            onChange={handleFileChange}
            disabled={disabled}
          />
          <label htmlFor="file-upload">
            <Button
              variant="outlined"
              component="span"
              startIcon={<UploadIcon />}
              disabled={disabled}
              sx={{
                mb: 2,
                borderStyle: 'dashed',
                borderWidth: 2,
                borderColor: 'divider',
                '&:hover': {
                  borderStyle: 'dashed',
                  borderWidth: 2,
                  borderColor: 'primary.main',
                  bgcolor: 'action.hover',
                },
              }}
            >
              选择TXT文件
            </Button>
          </label>
          {file && (
            <Box 
              sx={{ 
                mt: 2,
                p: 1.5,
                bgcolor: 'action.hover',
                borderRadius: 1,
                mb: 2,
              }}
            >
              <Typography variant="body2" sx={{ color: 'text.secondary', fontWeight: 500 }}>
                已选择: {file.name}
              </Typography>
            </Box>
          )}
        </Box>
      )}

      <Box 
        sx={{ 
          display: 'flex', 
          gap: 2, 
          mb: 3,
          flexDirection: { xs: 'column', sm: 'row' },
        }}
      >
        <FormControl 
          sx={{ 
            minWidth: { xs: '100%', sm: 180 },
          }} 
          disabled={loadingProviders || disabled}
        >
          <InputLabel>模型提供商</InputLabel>
          <Select
            value={provider}
            label="模型提供商"
            onChange={(e) => handleProviderChange(e.target.value)}
          >
            {providers.map((p) => (
              <MenuItem key={p} value={p}>
                {p}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl 
          sx={{ 
            flexGrow: 1,
            minWidth: { xs: '100%', sm: 200 },
          }} 
          disabled={loadingModels || disabled || models.length === 0}
        >
          <InputLabel>模型名称</InputLabel>
          <Select
            value={modelName}
            label="模型名称"
            onChange={(e) => setModelName(e.target.value)}
          >
            {models.map((model) => (
              <MenuItem key={model} value={model}>
                {model}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {tabValue === 1 && (
        <Box sx={{ mb: 3 }}>
          <Alert severity="info">
            文件上传将自动使用后台任务处理，您可以在"任务进度"页面查看处理状态，完成后可在"比对结果"页面查看结果。
          </Alert>
        </Box>
      )}

      <Button
        variant="contained"
        color="primary"
        onClick={handleSubmit}
        disabled={
          disabled ||
          (tabValue === 0 ? !text.trim() : !file)
        }
        fullWidth
        size="large"
        sx={{
          py: 1.5,
          fontSize: '1rem',
          fontWeight: 600,
        }}
      >
        {disabled ? '校对中...' : '开始校对'}
      </Button>
    </Paper>
  )
}

export default TextUpload
