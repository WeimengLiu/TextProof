import React from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
} from '@mui/material'
import {
  ArrowBack as ArrowBackIcon,
  Download as DownloadIcon,
} from '@mui/icons-material'
import TextComparison from './TextComparison'

function ComparisonViewPage({ original, corrected, filename, chapterTitle, onBack, onExport }) {
  const handleExport = () => {
    if (!corrected) return
    const blob = new Blob([corrected], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const exportFilename = chapterTitle
      ? `精校文本_${chapterTitle}_${filename || new Date().getTime()}.txt`
      : `精校文本_${filename || new Date().getTime()}.txt`
    link.download = exportFilename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    
    if (onExport) {
      onExport()
    }
  }

  return (
    <Box>
      {/* 顶部导航栏 */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          mb: 3,
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <IconButton onClick={onBack} size="small" sx={{ mr: 1 }}>
            <ArrowBackIcon />
          </IconButton>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {chapterTitle ? `${chapterTitle} - ${filename}` : filename || '比对结果'}
            </Typography>
            {chapterTitle && (
              <Typography variant="body2" color="text.secondary">
                {filename}
              </Typography>
            )}
          </Box>
        </Box>
        <Button
          variant="contained"
          color="primary"
          startIcon={<DownloadIcon />}
          onClick={handleExport}
          disabled={!corrected}
        >
          导出精校文本
        </Button>
      </Paper>

      {/* 比对结果 */}
      {original && corrected ? (
        <TextComparison
          original={original}
          corrected={corrected}
          onExport={handleExport}
        />
      ) : (
        <Paper
          elevation={0}
          sx={{
            p: 4,
            textAlign: 'center',
            border: '1px solid',
            borderColor: 'divider',
            borderRadius: 2,
          }}
        >
          <Typography variant="body1" color="text.secondary">
            暂无比对数据
          </Typography>
        </Paper>
      )}
    </Box>
  )
}

export default ComparisonViewPage
