import React, { useState } from 'react'
import { Container, AppBar, Toolbar, Typography, Box, Chip, Tabs, Tab } from '@mui/material'
import { AutoFixHigh, CheckCircle } from '@mui/icons-material'
import TextUpload from './components/TextUpload'
import CorrectionProgress from './components/CorrectionProgress'
import TextComparison from './components/TextComparison'
import SettingsPage from './components/SettingsPage'
import { correctionService } from './services/api'

function App() {
  const [mainTab, setMainTab] = useState(0)
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
          backdropFilter: 'blur(12px)',
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          color: 'text.primary',
          zIndex: 1100,
        }}
      >
        <Toolbar 
          sx={{ 
            maxWidth: '1400px', 
            width: '100%', 
            mx: 'auto', 
            px: { xs: 2, sm: 3 },
            py: { xs: 1, sm: 1.5 },
            minHeight: { xs: '64px', sm: '72px' },
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 2,
              flexGrow: 1,
            }}
          >
            {/* Logo/Icon */}
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: { xs: 40, sm: 48 },
                height: { xs: 40, sm: 48 },
                borderRadius: 2,
                bgcolor: 'primary.main',
                color: 'white',
                flexShrink: 0,
              }}
            >
              <AutoFixHigh sx={{ fontSize: { xs: 24, sm: 28 } }} />
            </Box>

            {/* Title */}
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              <Typography 
                variant="h6" 
                component="div" 
                sx={{ 
                  fontWeight: 700,
                  letterSpacing: '-0.02em',
                  color: 'text.primary',
                  fontSize: { xs: '1.1rem', sm: '1.25rem' },
                  lineHeight: 1.2,
                  mb: 0.25,
                }}
              >
                小说文本精校系统
              </Typography>
              <Typography 
                variant="caption" 
                sx={{ 
                  color: 'text.secondary',
                  fontSize: { xs: '0.7rem', sm: '0.75rem' },
                  display: { xs: 'none', sm: 'block' },
                }}
              >
                最小侵入式精校 · 专注纠错
              </Typography>
            </Box>
          </Box>

          {/* Status Badge */}
          <Box sx={{ display: { xs: 'none', sm: 'flex' }, alignItems: 'center', gap: 1 }}>
            <Chip
              icon={<CheckCircle sx={{ fontSize: 16 }} />}
              label="AI 驱动"
              size="small"
              sx={{
                bgcolor: 'success.light',
                color: 'success.dark',
                fontWeight: 500,
                '& .MuiChip-icon': {
                  color: 'success.dark',
                },
              }}
            />
          </Box>
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
        {/* 主Tab切换 */}
        <Box sx={{ mb: 3 }}>
          <Tabs
            value={mainTab}
            onChange={(e, v) => setMainTab(v)}
            sx={{
              mb: 3,
              '& .MuiTabs-indicator': {
                bgcolor: 'primary.main',
              },
            }}
          >
            <Tab
              label="文本校对"
              sx={{
                fontWeight: mainTab === 0 ? 600 : 400,
                fontSize: '1rem',
              }}
            />
            <Tab
              label="系统配置"
              sx={{
                fontWeight: mainTab === 1 ? 600 : 400,
                fontSize: '1rem',
              }}
            />
          </Tabs>
        </Box>

        {/* 文本校对页面 */}
        {mainTab === 0 && (
          <>
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
          </>
        )}

        {/* 系统配置页面 */}
        {mainTab === 1 && <SettingsPage />}
      </Container>
    </Box>
  )
}

export default App
