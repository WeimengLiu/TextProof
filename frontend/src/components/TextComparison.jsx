import React, { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Tabs,
  Tab,
  Grid,
  Chip,
} from '@mui/material'
import { Download as DownloadIcon } from '@mui/icons-material'
import { correctionService } from '../services/api'

function TextComparison({ original, corrected, onExport }) {
  const [tabValue, setTabValue] = useState(0)
  const [diffData, setDiffData] = useState(null)
  const [loadingDiff, setLoadingDiff] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    // 检查是否有变化
    setHasChanges(original !== corrected)

    // 加载差异数据
    if (original && corrected) {
      loadDiff()
    }
  }, [original, corrected])

  const loadDiff = async () => {
    setLoadingDiff(true)
    try {
      const data = await correctionService.getDiff(original, corrected)
      setDiffData(data)
      setHasChanges(data.has_changes)
    } catch (error) {
      console.error('加载差异失败:', error)
    } finally {
      setLoadingDiff(false)
    }
  }

  const renderTextWithDiff = (segments, type) => {
    if (!segments) {
      return <Typography>加载中...</Typography>
    }

    return (
      <Box
        sx={{
          p: 2,
          bgcolor: 'background.paper',
          borderRadius: 1,
          border: '1px solid',
          borderColor: 'divider',
          fontFamily: 'monospace',
          fontSize: '14px',
          lineHeight: 1.8,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {segments.map((segment, index) => {
          const bgColor =
            segment.type === 'added'
              ? 'success.light'
              : segment.type === 'deleted'
              ? 'error.light'
              : 'transparent'
          const textColor =
            segment.type === 'added'
              ? 'success.dark'
              : segment.type === 'deleted'
              ? 'error.dark'
              : 'text.primary'

          return (
            <span
              key={index}
              style={{
                backgroundColor: segment.type === 'added' 
                  ? 'rgba(76, 175, 80, 0.2)' 
                  : segment.type === 'deleted'
                  ? 'rgba(244, 67, 54, 0.2)'
                  : 'transparent',
                color: textColor,
                textDecoration: segment.type === 'deleted' ? 'line-through' : 'none',
              }}
            >
              {segment.text}
            </span>
          )
        })}
      </Box>
    )
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">校对结果</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {hasChanges && (
            <Chip label="有修改" color="primary" size="small" />
          )}
          {!hasChanges && (
            <Chip label="无修改" color="default" size="small" />
          )}
          <Button
            variant="contained"
            startIcon={<DownloadIcon />}
            onClick={onExport}
            disabled={!corrected}
          >
            导出精校文本
          </Button>
        </Box>
      </Box>

      <Box sx={{ mb: 2 }}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)}>
          <Tab label="对比视图" />
          <Tab label="原文" />
          <Tab label="精校文本" />
        </Tabs>
      </Box>

      {tabValue === 0 && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom color="text.secondary">
              原文
            </Typography>
            {loadingDiff ? (
              <Typography>加载差异中...</Typography>
            ) : (
              renderTextWithDiff(diffData?.original_segments, 'original')
            )}
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom color="text.secondary">
              精校文本
            </Typography>
            {loadingDiff ? (
              <Typography>加载差异中...</Typography>
            ) : (
              renderTextWithDiff(diffData?.corrected_segments, 'corrected')
            )}
          </Grid>
        </Grid>
      )}

      {tabValue === 1 && (
        <Box
          sx={{
            p: 2,
            bgcolor: 'background.paper',
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'divider',
            fontFamily: 'monospace',
            fontSize: '14px',
            lineHeight: 1.8,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            maxHeight: '600px',
            overflow: 'auto',
          }}
        >
          {original}
        </Box>
      )}

      {tabValue === 2 && (
        <Box
          sx={{
            p: 2,
            bgcolor: 'background.paper',
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'divider',
            fontFamily: 'monospace',
            fontSize: '14px',
            lineHeight: 1.8,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            maxHeight: '600px',
            overflow: 'auto',
          }}
        >
          {corrected}
        </Box>
      )}
    </Paper>
  )
}

export default TextComparison
