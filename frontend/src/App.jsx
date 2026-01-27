import React, { useState } from 'react'
import { Container, AppBar, Toolbar, Typography, Box } from '@mui/material'
import TextUpload from './components/TextUpload'
import CorrectionProgress from './components/CorrectionProgress'
import TextComparison from './components/TextComparison'
import { correctionService } from './services/api'

function App() {
  const [originalText, setOriginalText] = useState('')
  const [correctedText, setCorrectedText] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const [error, setError] = useState(null)

  const handleTextSubmit = async (text, options) => {
    setIsProcessing(true)
    setError(null)
    setProgress({ current: 0, total: 0 })
    setOriginalText(text)
    setCorrectedText('')

    try {
      const result = await correctionService.correctText(text, options, (current, total) => {
        setProgress({ current, total })
      })

      setCorrectedText(result.corrected)
    } catch (err) {
      setError(err.message || '校对失败，请重试')
      console.error('校对错误:', err)
    } finally {
      setIsProcessing(false)
    }
  }

  const handleExport = () => {
    if (!correctedText) return

    const blob = new Blob([correctedText], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `精校文本_${new Date().getTime()}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      <AppBar 
        position="sticky" 
        elevation={0}
        sx={{ 
          bgcolor: 'background.paper',
          borderBottom: '1px solid',
          borderColor: 'divider',
          backdropFilter: 'blur(8px)',
          backgroundColor: 'rgba(255, 255, 255, 0.9)',
          color: 'text.primary', // 明确设置文字颜色
        }}
      >
        <Toolbar sx={{ maxWidth: '1400px', width: '100%', mx: 'auto', px: { xs: 2, sm: 3 } }}>
          <Typography 
            variant="h6" 
            component="div" 
            sx={{ 
              flexGrow: 1,
              fontWeight: 600,
              letterSpacing: '-0.01em',
              color: 'text.primary', // 明确设置文字颜色
            }}
          >
            小说文本精校系统
          </Typography>
        </Toolbar>
      </AppBar>

      <Container 
        maxWidth="lg" 
        sx={{ 
          mt: { xs: 3, sm: 4 },
          mb: 4,
          px: { xs: 2, sm: 3 },
        }}
      >
        <TextUpload onSubmit={handleTextSubmit} disabled={isProcessing} />

        {isProcessing && (
          <CorrectionProgress current={progress.current} total={progress.total} />
        )}

        {error && (
          <Box 
            sx={{ 
              mt: 2, 
              p: 2.5, 
              bgcolor: 'error.light', 
              color: 'error.dark',
              borderRadius: 2,
              border: '1px solid',
              borderColor: 'error.main',
              display: 'flex',
              alignItems: 'center',
              gap: 1,
            }}
          >
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {error}
            </Typography>
          </Box>
        )}

        {correctedText && (
          <TextComparison
            original={originalText}
            corrected={correctedText}
            onExport={handleExport}
          />
        )}
      </Container>
    </Box>
  )
}

export default App
