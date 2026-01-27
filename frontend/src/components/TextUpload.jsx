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
} from '@mui/material'
import { Upload as UploadIcon } from '@mui/icons-material'
import { correctionService } from '../services/api'

function TextUpload({ onSubmit, disabled }) {
  const [tabValue, setTabValue] = useState(0)
  const [text, setText] = useState('')
  const [file, setFile] = useState(null)
  const [provider, setProvider] = useState('openai')
  const [modelName, setModelName] = useState('')
  const [providers, setProviders] = useState([])
  const [loadingProviders, setLoadingProviders] = useState(false)

  React.useEffect(() => {
    loadProviders()
  }, [])

  const loadProviders = async () => {
    setLoadingProviders(true)
    try {
      const data = await correctionService.getProviders()
      setProviders(data.providers || [])
      setProvider(data.default || 'openai')
    } catch (error) {
      console.error('加载提供商失败:', error)
    } finally {
      setLoadingProviders(false)
    }
  }

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0]
    if (selectedFile && selectedFile.name.endsWith('.txt')) {
      setFile(selectedFile)
      const reader = new FileReader()
      reader.onload = (e) => {
        setText(e.target.result)
      }
      reader.readAsText(selectedFile, 'UTF-8')
    } else {
      alert('请选择TXT文件')
    }
  }

  const handleSubmit = () => {
    if (!text.trim()) {
      alert('请输入或上传文本')
      return
    }

    const options = {
      provider: provider || undefined,
      model_name: modelName || undefined,
    }

    onSubmit(text, options)
  }

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        输入文本
      </Typography>

      <Box sx={{ mb: 2 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="粘贴文本" />
          <Tab label="上传文件" />
        </Tabs>
      </Box>

      {tabValue === 0 ? (
        <TextField
          fullWidth
          multiline
          rows={10}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="请粘贴需要校对的文本..."
          variant="outlined"
          disabled={disabled}
          sx={{ mb: 2 }}
        />
      ) : (
        <Box sx={{ mb: 2 }}>
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
            >
              选择TXT文件
            </Button>
          </label>
          {file && (
            <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>
              已选择: {file.name}
            </Typography>
          )}
          {text && (
            <TextField
              fullWidth
              multiline
              rows={6}
              value={text}
              onChange={(e) => setText(e.target.value)}
              variant="outlined"
              disabled={disabled}
              sx={{ mt: 2 }}
            />
          )}
        </Box>
      )}

      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
        <FormControl sx={{ minWidth: 150 }} disabled={loadingProviders || disabled}>
          <InputLabel>模型提供商</InputLabel>
          <Select
            value={provider}
            label="模型提供商"
            onChange={(e) => setProvider(e.target.value)}
          >
            {providers.map((p) => (
              <MenuItem key={p} value={p}>
                {p}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          label="模型名称（可选）"
          value={modelName}
          onChange={(e) => setModelName(e.target.value)}
          placeholder="如: gpt-4-turbo-preview"
          disabled={disabled}
          sx={{ flexGrow: 1 }}
        />
      </Box>

      <Button
        variant="contained"
        color="primary"
        onClick={handleSubmit}
        disabled={disabled || !text.trim()}
        fullWidth
        size="large"
      >
        {disabled ? '校对中...' : '开始校对'}
      </Button>
    </Paper>
  )
}

export default TextUpload
