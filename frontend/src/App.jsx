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
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            小说文本精校系统
          </Typography>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <TextUpload onSubmit={handleTextSubmit} disabled={isProcessing} />

        {isProcessing && (
          <CorrectionProgress current={progress.current} total={progress.total} />
        )}

        {error && (
          <Box sx={{ mt: 2, p: 2, bgcolor: 'error.light', color: 'error.contrastText', borderRadius: 1 }}>
            {error}
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
