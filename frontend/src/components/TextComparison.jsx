import React, { useState, useEffect, useRef, useCallback } from 'react'
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
  const originalScrollRef = useRef(null)
  const correctedScrollRef = useRef(null)
  const isSyncingScrollRef = useRef(false)

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

  const syncScroll = useCallback((sourceEl, targetEl) => {
    if (!sourceEl || !targetEl) return
    if (isSyncingScrollRef.current) return
    isSyncingScrollRef.current = true

    const sourceScrollable = Math.max(1, sourceEl.scrollHeight - sourceEl.clientHeight)
    const targetScrollable = Math.max(1, targetEl.scrollHeight - targetEl.clientHeight)
    const ratio = sourceEl.scrollTop / sourceScrollable
    targetEl.scrollTop = ratio * targetScrollable

    requestAnimationFrame(() => {
      isSyncingScrollRef.current = false
    })
  }, [])

  const handleOriginalScroll = useCallback(() => {
    syncScroll(originalScrollRef.current, correctedScrollRef.current)
  }, [syncScroll])

  const handleCorrectedScroll = useCallback(() => {
    syncScroll(correctedScrollRef.current, originalScrollRef.current)
  }, [syncScroll])

  const renderTextWithDiff = (segments, type, scrollRef, onScroll) => {
    if (!segments) {
      return <Typography>加载中...</Typography>
    }

    return (
      <Box
        ref={scrollRef}
        onScroll={onScroll}
        sx={{
          p: 2.5,
          bgcolor: 'background.paper',
          borderRadius: 2,
          border: '1px solid',
          borderColor: 'divider',
          fontFamily: 'monospace',
          fontSize: '0.9375rem',
          lineHeight: 1.8,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          maxHeight: '600px',
          overflow: 'auto',
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            bgcolor: 'action.hover',
            borderRadius: '4px',
          },
          '&::-webkit-scrollbar-thumb': {
            bgcolor: 'text.disabled',
            borderRadius: '4px',
            '&:hover': {
              bgcolor: 'text.secondary',
            },
          },
        }}
      >
        {segments.map((segment, index) => {
          return (
            <span
              key={index}
              style={{
                backgroundColor: segment.type === 'added' 
                  ? 'rgba(16, 185, 129, 0.15)' 
                  : segment.type === 'deleted'
                  ? 'rgba(239, 68, 68, 0.15)'
                  : 'transparent',
                color: segment.type === 'added' 
                  ? '#059669'
                  : segment.type === 'deleted'
                  ? '#DC2626'
                  : '#1E293B',
                textDecoration: segment.type === 'deleted' ? 'line-through' : 'none',
                padding: segment.type !== 'same' ? '2px 4px' : '0',
                borderRadius: segment.type !== 'same' ? '3px' : '0',
                transition: 'background-color 0.15s ease-out',
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
      <Box 
        sx={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: { xs: 'flex-start', sm: 'center' },
          mb: 3,
          flexDirection: { xs: 'column', sm: 'row' },
          gap: { xs: 2, sm: 0 },
        }}
      >
        <Typography 
          variant="h6"
          sx={{ 
            fontWeight: 600,
          }}
        >
          校对结果
        </Typography>
        <Box 
          sx={{ 
            display: 'flex', 
            gap: 1.5,
            alignItems: 'center',
            flexWrap: 'wrap',
          }}
        >
          {hasChanges && (
            <Chip 
              label="有修改" 
              color="primary" 
              size="small"
              sx={{
                fontWeight: 500,
              }}
            />
          )}
          {!hasChanges && (
            <Chip 
              label="无修改" 
              color="default" 
              size="small"
              sx={{
                fontWeight: 500,
              }}
            />
          )}
          <Button
            variant="contained"
            color="secondary"
            startIcon={<DownloadIcon />}
            onClick={onExport}
            disabled={!corrected}
            sx={{
              fontWeight: 600,
            }}
          >
            导出精校文本
          </Button>
        </Box>
      </Box>

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
            label="对比视图"
            sx={{ 
              fontWeight: tabValue === 0 ? 600 : 400,
            }}
          />
          <Tab 
            label="原文"
            sx={{ 
              fontWeight: tabValue === 1 ? 600 : 400,
            }}
          />
          <Tab 
            label="精校文本"
            sx={{ 
              fontWeight: tabValue === 2 ? 600 : 400,
            }}
          />
        </Tabs>
      </Box>

      {tabValue === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography 
              variant="subtitle2" 
              gutterBottom 
              sx={{ 
                color: 'text.secondary',
                fontWeight: 600,
                mb: 1.5,
              }}
            >
              原文
            </Typography>
            {loadingDiff ? (
              <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography color="text.secondary">加载差异中...</Typography>
              </Box>
            ) : (
              renderTextWithDiff(diffData?.original_segments, 'original', originalScrollRef, handleOriginalScroll)
            )}
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography 
              variant="subtitle2" 
              gutterBottom 
              sx={{ 
                color: 'text.secondary',
                fontWeight: 600,
                mb: 1.5,
              }}
            >
              精校文本
            </Typography>
            {loadingDiff ? (
              <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography color="text.secondary">加载差异中...</Typography>
              </Box>
            ) : (
              renderTextWithDiff(diffData?.corrected_segments, 'corrected', correctedScrollRef, handleCorrectedScroll)
            )}
          </Grid>
        </Grid>
      )}

      {tabValue === 1 && (
        <Box
          sx={{
            p: 2.5,
            bgcolor: 'background.paper',
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'divider',
            fontFamily: 'monospace',
            fontSize: '0.9375rem',
            lineHeight: 1.8,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            maxHeight: '600px',
            overflow: 'auto',
            '&::-webkit-scrollbar': {
              width: '8px',
            },
            '&::-webkit-scrollbar-track': {
              bgcolor: 'action.hover',
              borderRadius: '4px',
            },
            '&::-webkit-scrollbar-thumb': {
              bgcolor: 'text.disabled',
              borderRadius: '4px',
              '&:hover': {
                bgcolor: 'text.secondary',
              },
            },
          }}
        >
          {original}
        </Box>
      )}

      {tabValue === 2 && (
        <Box
          sx={{
            p: 2.5,
            bgcolor: 'background.paper',
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'divider',
            fontFamily: 'monospace',
            fontSize: '0.9375rem',
            lineHeight: 1.8,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            maxHeight: '600px',
            overflow: 'auto',
            '&::-webkit-scrollbar': {
              width: '8px',
            },
            '&::-webkit-scrollbar-track': {
              bgcolor: 'action.hover',
              borderRadius: '4px',
            },
            '&::-webkit-scrollbar-thumb': {
              bgcolor: 'text.disabled',
              borderRadius: '4px',
              '&:hover': {
                bgcolor: 'text.secondary',
              },
            },
          }}
        >
          {corrected}
        </Box>
      )}
    </Paper>
  )
}

export default TextComparison
