import React, { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Button,
  Chip,
  Pagination,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Card,
  CardContent,
  Stack,
  Tooltip,
  alpha,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  Delete as DeleteIcon,
  Visibility as ViewIcon,
  CheckCircle,
  Cancel,
  Book as BookIcon,
  Download as DownloadIcon,
  MoreVert as MoreVertIcon,
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'
import { correctionService } from '../services/api'

function ResultListPage({ onViewComparison }) {
  const theme = useTheme()
  const [results, setResults] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [rowsPerPage, setRowsPerPage] = useState(10)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedResult, setSelectedResult] = useState(null)
  const [viewDialogOpen, setViewDialogOpen] = useState(false)
  const [viewResult, setViewResult] = useState(null)
  const [loadingResult, setLoadingResult] = useState(false)

  const loadResults = async (opts = {}) => {
    setLoading(true)
    setError(null)
    try {
      const nextPage = opts.page !== undefined ? opts.page : page
      const nextRowsPerPage = opts.rowsPerPage !== undefined ? opts.rowsPerPage : rowsPerPage
      const data = await correctionService.getResults({
        limit: nextRowsPerPage,
        offset: nextPage * nextRowsPerPage,
      })
      setResults(data.results || [])
      setTotal(typeof data.total === 'number' ? data.total : (data.results || []).length)
    } catch (err) {
      setError(err.message || '加载结果列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadResults()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, rowsPerPage])

  const handleDelete = (result) => {
    setSelectedResult(result)
    setDeleteDialogOpen(true)
  }

  const confirmDelete = async () => {
    if (!selectedResult) return

    try {
      await correctionService.deleteResult(selectedResult.result_id)
      setDeleteDialogOpen(false)
      setSelectedResult(null)
      // 删除后若当前页已空，尽量回退一页
      const remaining = Math.max(total - 1, 0)
      const lastPage = rowsPerPage > 0 ? Math.max(Math.ceil(remaining / rowsPerPage) - 1, 0) : 0
      if (page > lastPage) {
        setPage(lastPage)
      } else {
        loadResults()
      }
    } catch (err) {
      setError(err.message || '删除失败')
    }
  }

  const handleView = async (result) => {
    setViewDialogOpen(true)
    setLoadingResult(true)
    try {
      // 默认不拉全文，避免大文本导致前端卡顿/内存飙升
      const data = await correctionService.getResult(result.result_id, { include_text: false })
      setViewResult(data)
    } catch (err) {
      setError(err.message || '加载结果详情失败')
    } finally {
      setLoadingResult(false)
    }
  }

  const handleViewChapter = async (resultId, chapterIndex) => {
    setViewDialogOpen(true)
    setLoadingResult(true)
    try {
      const data = await correctionService.getChapterResult(resultId, chapterIndex)
      setViewResult(data)
    } catch (err) {
      setError(err.message || '加载章节结果失败')
    } finally {
      setLoadingResult(false)
    }
  }

  const handleOpenComparison = async () => {
    if (!viewResult) return

    // 章节详情本身就包含全文；非章节需要按需拉全文
    try {
      setLoadingResult(true)
      let data = viewResult
      if (!viewResult.use_chapters && (!viewResult.original || !viewResult.corrected)) {
        data = await correctionService.getResult(viewResult.result_id, { include_text: true })
        setViewResult(data)
      }

      if (onViewComparison) {
        onViewComparison({
          original: data.original,
          corrected: data.corrected,
          filename: data.filename,
          chapterTitle: data.chapter_title,
        })
        setViewDialogOpen(false)
      }
    } catch (err) {
      setError(err.message || '加载全文失败')
    } finally {
      setLoadingResult(false)
    }
  }

  const handleViewChapterComparison = async (resultId, chapterIndex) => {
    try {
      const data = await correctionService.getChapterResult(resultId, chapterIndex)
      if (onViewComparison) {
        onViewComparison({
          original: data.original,
          corrected: data.corrected,
          filename: viewResult?.filename || '未知文件',
          chapterTitle: data.chapter_title,
        })
      }
    } catch (err) {
      setError(err.message || '加载章节结果失败')
    }
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN')
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  const handleChangePage = (event, newPage) => {
    setPage(newPage - 1) // Pagination component uses 1-based index
  }

  const handleChangeRowsPerPage = (event) => {
    const next = parseInt(event.target.value, 10)
    setRowsPerPage(next)
    setPage(0)
  }

  const handleDownload = () => {
    if (!viewResult?.result_id) return
    const url = correctionService.getResultDownloadUrl(viewResult.result_id)
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  const totalPages = Math.ceil(total / rowsPerPage)

  return (
    <Box>
      <Paper
        elevation={0}
        sx={{
          p: { xs: 2, sm: 3 },
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
          bgcolor: 'background.paper',
        }}
      >
        {/* Header */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
              比对结果
            </Typography>
            <Typography variant="body2" color="text.secondary">
              共 {total} 条记录
            </Typography>
          </Box>
          <Tooltip title="刷新">
            <IconButton 
              onClick={loadResults} 
              disabled={loading} 
              sx={{
                bgcolor: 'action.hover',
                '&:hover': {
                  bgcolor: 'action.selected',
                },
              }}
            >
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading && results.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
            <CircularProgress />
          </Box>
        ) : results.length === 0 ? (
          <Box 
            sx={{ 
              textAlign: 'center', 
              py: 8,
              px: 2,
            }}
          >
            <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
              暂无比对结果
            </Typography>
            <Typography variant="body2" color="text.secondary">
              开始校对文本后，结果将显示在这里
            </Typography>
          </Box>
        ) : (
          <Box>
            {/* Card Grid */}
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: {
                  xs: '1fr',
                  sm: 'repeat(2, 1fr)',
                  lg: 'repeat(3, 1fr)',
                },
                gap: 2,
                mb: 3,
              }}
            >
              {results.map((result) => (
                <Card
                  key={result.result_id}
                  elevation={0}
                  sx={{
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 2,
                    transition: 'all 0.2s ease-out',
                    cursor: 'pointer',
                    '&:hover': {
                      borderColor: 'primary.main',
                      boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.15)}`,
                      transform: 'translateY(-2px)',
                    },
                  }}
                  onClick={() => handleView(result)}
                >
                  <CardContent sx={{ p: 2.5, '&:last-child': { pb: 2.5 } }}>
                    {/* Header */}
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                          {result.use_chapters && (
                            <BookIcon 
                              fontSize="small" 
                              sx={{ 
                                color: 'primary.main',
                                flexShrink: 0,
                              }} 
                            />
                          )}
                          <Typography 
                            variant="subtitle2" 
                            sx={{ 
                              fontWeight: 600,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                            }}
                          >
                            {result.filename}
                          </Typography>
                        </Box>
                        {result.use_chapters && result.chapter_count && (
                          <Chip
                            label={`${result.chapter_count} 章`}
                            size="small"
                            sx={{
                              height: 20,
                              fontSize: '0.7rem',
                              bgcolor: alpha(theme.palette.primary.main, 0.1),
                              color: 'primary.main',
                              fontWeight: 500,
                            }}
                          />
                        )}
                      </Box>
                      <Chip
                        icon={result.has_changes ? <CheckCircle sx={{ fontSize: 14 }} /> : <Cancel sx={{ fontSize: 14 }} />}
                        label={result.has_changes ? '有修改' : '无修改'}
                        size="small"
                        color={result.has_changes ? 'success' : 'default'}
                        sx={{
                          height: 24,
                          fontSize: '0.75rem',
                          fontWeight: 500,
                          flexShrink: 0,
                        }}
                      />
                    </Box>

                    {/* Info */}
                    <Stack spacing={1.5} sx={{ mb: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="caption" color="text.secondary">
                          原文长度
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {formatFileSize(result.original_length)}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="caption" color="text.secondary">
                          精校长度
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          {formatFileSize(result.corrected_length)}
                        </Typography>
                      </Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="caption" color="text.secondary">
                          完成时间
                        </Typography>
                        <Typography variant="body2" sx={{ fontWeight: 500, fontSize: '0.8125rem' }}>
                          {formatDate(result.completed_at)}
                        </Typography>
                      </Box>
                    </Stack>

                    {/* Actions */}
                    <Box 
                      sx={{ 
                        display: 'flex', 
                        gap: 1,
                        pt: 1.5,
                        borderTop: '1px solid',
                        borderColor: 'divider',
                      }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Tooltip title="查看详情">
                        <IconButton
                          size="small"
                          onClick={() => handleView(result)}
                          sx={{
                            flex: 1,
                            bgcolor: 'action.hover',
                            '&:hover': {
                              bgcolor: 'primary.main',
                              color: 'white',
                            },
                            transition: 'all 0.2s ease-out',
                          }}
                        >
                          <ViewIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="下载">
                        <IconButton
                          size="small"
                          onClick={() => {
                            const url = correctionService.getResultDownloadUrl(result.result_id)
                            window.open(url, '_blank', 'noopener,noreferrer')
                          }}
                          sx={{
                            flex: 1,
                            bgcolor: 'action.hover',
                            '&:hover': {
                              bgcolor: 'primary.main',
                              color: 'white',
                            },
                            transition: 'all 0.2s ease-out',
                          }}
                        >
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="删除">
                        <IconButton
                          size="small"
                          onClick={() => handleDelete(result)}
                          sx={{
                            flex: 1,
                            bgcolor: 'action.hover',
                            '&:hover': {
                              bgcolor: 'error.main',
                              color: 'white',
                            },
                            transition: 'all 0.2s ease-out',
                          }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </CardContent>
                </Card>
              ))}
            </Box>

            {/* Pagination */}
            {totalPages > 1 && (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 2, mt: 3 }}>
                <Pagination
                  count={totalPages}
                  page={page + 1}
                  onChange={handleChangePage}
                  color="primary"
                  size="large"
                  showFirstButton
                  showLastButton
                  sx={{
                    '& .MuiPaginationItem-root': {
                      fontSize: '0.875rem',
                      fontWeight: 500,
                    },
                  }}
                />
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    每页
                  </Typography>
                  <select
                    value={rowsPerPage}
                    onChange={(e) => handleChangeRowsPerPage({ target: { value: e.target.value } })}
                    style={{
                      padding: '4px 8px',
                      borderRadius: '4px',
                      border: `1px solid ${theme.palette.divider}`,
                      fontSize: '0.875rem',
                      fontFamily: theme.typography.fontFamily,
                      cursor: 'pointer',
                    }}
                  >
                    {[10, 20, 50, 100].map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                  <Typography variant="body2" color="text.secondary">
                    条
                  </Typography>
                </Box>
              </Box>
            )}
          </Box>
        )}
      </Paper>

      {/* 删除确认对话框 */}
      <Dialog 
        open={deleteDialogOpen} 
        onClose={() => setDeleteDialogOpen(false)}
        PaperProps={{
          sx: {
            borderRadius: 2,
            minWidth: 400,
          },
        }}
      >
        <DialogTitle sx={{ pb: 1.5, fontWeight: 600 }}>
          确认删除
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 1 }}>
            确定要删除结果
          </Typography>
          <Typography 
            variant="body2" 
            sx={{ 
              fontWeight: 600,
              color: 'text.primary',
              bgcolor: 'action.hover',
              p: 1.5,
              borderRadius: 1,
              mb: 2,
            }}
          >
            {selectedResult?.filename}
          </Typography>
          <Typography variant="body2" color="error.main" sx={{ fontWeight: 500 }}>
            此操作不可恢复
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button 
            onClick={() => setDeleteDialogOpen(false)}
            variant="outlined"
            sx={{ minWidth: 80 }}
          >
            取消
          </Button>
          <Button 
            onClick={confirmDelete} 
            color="error" 
            variant="contained"
            sx={{ minWidth: 80 }}
          >
            删除
          </Button>
        </DialogActions>
      </Dialog>

      {/* 查看结果对话框 */}
      <Dialog
        open={viewDialogOpen}
        onClose={() => setViewDialogOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 2,
          },
        }}
      >
        <DialogTitle sx={{ pb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              比对结果详情
            </Typography>
            {viewResult && (
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="outlined"
                  color="primary"
                  size="small"
                  startIcon={<DownloadIcon />}
                  onClick={handleDownload}
                >
                  下载
                </Button>
                <Button
                  variant="contained"
                  color="primary"
                  size="small"
                  startIcon={<ViewIcon />}
                  onClick={handleOpenComparison}
                >
                  查看比对
                </Button>
              </Box>
            )}
          </Box>
        </DialogTitle>
        <DialogContent>
          {loadingResult ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 6 }}>
              <CircularProgress />
            </Box>
          ) : viewResult ? (
            <Box>
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  mb: 3,
                  bgcolor: 'action.hover',
                  borderRadius: 1.5,
                  border: '1px solid',
                  borderColor: 'divider',
                }}
              >
                <Typography variant="subtitle2" sx={{ mb: 0.5, fontWeight: 600 }}>
                  文件名
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  {viewResult.filename}
                </Typography>
              </Paper>

              {viewResult.use_chapters && viewResult.chapters ? (
                <Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontWeight: 500 }}>
                    共 {viewResult.chapter_count} 个章节
                  </Typography>
                  <List sx={{ p: 0 }}>
                    {viewResult.chapters.map((chapter, index) => (
                      <Card
                        key={chapter.chapter_index}
                        elevation={0}
                        sx={{
                          mb: 1.5,
                          border: '1px solid',
                          borderColor: 'divider',
                          borderRadius: 1.5,
                          cursor: 'pointer',
                          transition: 'all 0.2s ease-out',
                          '&:hover': {
                            borderColor: 'primary.main',
                            bgcolor: alpha(theme.palette.primary.main, 0.04),
                            transform: 'translateX(4px)',
                          },
                        }}
                        onClick={() => handleViewChapter(viewResult.result_id, chapter.chapter_index)}
                      >
                        <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                            <Typography variant="body1" sx={{ fontWeight: 600, flex: 1 }}>
                              {chapter.chapter_title}
                            </Typography>
                            <Chip
                              icon={chapter.has_changes ? <CheckCircle sx={{ fontSize: 14 }} /> : <Cancel sx={{ fontSize: 14 }} />}
                              label={chapter.has_changes ? '有修改' : '无修改'}
                              size="small"
                              color={chapter.has_changes ? 'success' : 'default'}
                              sx={{
                                height: 24,
                                fontSize: '0.75rem',
                                fontWeight: 500,
                                ml: 1,
                              }}
                            />
                          </Box>
                          <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
                            <Typography variant="caption" color="text.secondary">
                              原文: <strong>{formatFileSize(chapter.original_length)}</strong>
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              精校: <strong>{formatFileSize(chapter.corrected_length)}</strong>
                            </Typography>
                          </Box>
                        </CardContent>
                      </Card>
                    ))}
                  </List>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block', fontStyle: 'italic' }}>
                    点击章节卡片查看详细比对结果
                  </Typography>
                </Box>
              ) : (
                <Box>
                  <Stack spacing={2} sx={{ mb: 3 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        原文长度
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>
                        {formatFileSize(viewResult.original_length ?? viewResult.original?.length ?? 0)}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        精校长度
                      </Typography>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>
                        {formatFileSize(viewResult.corrected_length ?? viewResult.corrected?.length ?? 0)}
                      </Typography>
                    </Box>
                  </Stack>
                  <Box sx={{ display: 'flex', justifyContent: 'center', mb: 2 }}>
                    <Chip
                      icon={viewResult.has_changes ? <CheckCircle /> : <Cancel />}
                      label={viewResult.has_changes ? '有修改' : '无修改'}
                      color={viewResult.has_changes ? 'success' : 'default'}
                      sx={{
                        height: 32,
                        fontSize: '0.875rem',
                        fontWeight: 500,
                      }}
                    />
                  </Box>
                  <Typography 
                    variant="body2" 
                    color="text.secondary" 
                    sx={{ 
                      textAlign: 'center',
                      fontStyle: 'italic',
                    }}
                  >
                    点击上方"查看比对"按钮加载全文并查看比对结果
                  </Typography>
                </Box>
              )}
            </Box>
          ) : null}
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button 
            onClick={() => setViewDialogOpen(false)}
            variant="outlined"
            sx={{ minWidth: 80 }}
          >
            关闭
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default ResultListPage
