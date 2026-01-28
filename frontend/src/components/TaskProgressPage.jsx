import React, { useState, useEffect } from 'react'
import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
} from '@mui/material'
import {
  Refresh as RefreshIcon,
  CheckCircle,
  Error as ErrorIcon,
  Schedule,
  PlayArrow,
  ExpandMore as ExpandMoreIcon,
  Book as BookIcon,
} from '@mui/icons-material'
import { correctionService } from '../services/api'

function TaskProgressPage() {
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadTasks = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await correctionService.getTasks()
      setTasks(data.tasks || [])
    } catch (err) {
      setError(err.message || '加载任务列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTasks()
    // 每3秒自动刷新一次
    const interval = setInterval(loadTasks, 3000)
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'success'
      case 'failed':
        return 'error'
      case 'processing':
        return 'info'
      default:
        return 'default'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle fontSize="small" />
      case 'failed':
        return <ErrorIcon fontSize="small" />
      case 'processing':
        return <PlayArrow fontSize="small" />
      default:
        return <Schedule fontSize="small" />
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  }

  const formatDate = (dateString) => {
    if (!dateString) return '-'
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN')
  }

  return (
    <Box>
      <Paper
        elevation={0}
        sx={{
          p: { xs: 3, sm: 4 },
          border: '1px solid',
          borderColor: 'divider',
          borderRadius: 2,
        }}
      >
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            任务进度
          </Typography>
          <IconButton onClick={loadTasks} disabled={loading} size="small">
            <RefreshIcon />
          </IconButton>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {loading && tasks.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : tasks.length === 0 ? (
          <Box sx={{ textAlign: 'center', p: 4 }}>
            <Typography variant="body2" color="text.secondary">
              暂无任务
            </Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>文件名</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>进度</TableCell>
                  <TableCell>文件大小</TableCell>
                  <TableCell>创建时间</TableCell>
                  <TableCell>完成时间</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {tasks.map((task) => {
                  const progress = task.progress
                  const percentage =
                    progress.total > 0
                      ? Math.round((progress.current / progress.total) * 100)
                      : 0
                  const hasChapters = task.use_chapters && task.chapter_progress

                  return (
                    <React.Fragment key={task.task_id}>
                      <TableRow>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {hasChapters && <BookIcon fontSize="small" color="primary" />}
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {task.filename}
                            </Typography>
                            {hasChapters && (
                              <Chip
                                label={`${Object.keys(task.chapter_progress).length}章`}
                                size="small"
                                color="primary"
                                variant="outlined"
                              />
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip
                            icon={getStatusIcon(task.status)}
                            label={
                              task.status === 'pending'
                                ? '等待中'
                                : task.status === 'processing'
                                ? '处理中'
                                : task.status === 'completed'
                                ? '已完成'
                                : '失败'
                            }
                            color={getStatusColor(task.status)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell sx={{ minWidth: 200 }}>
                          {task.status === 'processing' || task.status === 'completed' ? (
                            <Box>
                              <LinearProgress
                                variant="determinate"
                                value={percentage}
                                sx={{ mb: 0.5, height: 6, borderRadius: 3 }}
                              />
                              <Typography variant="caption" color="text.secondary">
                                {progress.current} / {progress.total} ({percentage}%)
                              </Typography>
                            </Box>
                          ) : (
                            <Typography variant="caption" color="text.secondary">
                              -
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {formatFileSize(task.file_size)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {formatDate(task.created_at)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {formatDate(task.completed_at)}
                          </Typography>
                        </TableCell>
                      </TableRow>
                      {hasChapters && (
                        <TableRow>
                          <TableCell colSpan={6} sx={{ py: 0, borderTop: 'none' }}>
                            <Accordion sx={{ boxShadow: 'none', '&:before': { display: 'none' } }}>
                              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                                <Typography variant="body2" color="text.secondary">
                                  章节进度详情
                                </Typography>
                              </AccordionSummary>
                              <AccordionDetails>
                                <List dense>
                                  {Object.values(task.chapter_progress)
                                    .sort((a, b) => a.chapter_index - b.chapter_index)
                                    .map((chapter) => {
                                      const chProgress = chapter.progress
                                      const chPercentage =
                                        chProgress.total > 0
                                          ? Math.round((chProgress.current / chProgress.total) * 100)
                                          : 0
                                      
                                      return (
                                        <ListItem key={chapter.chapter_index} sx={{ px: 0 }}>
                                          <ListItemText
                                            primary={
                                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                                <Typography variant="body2" sx={{ fontWeight: 500, minWidth: 100 }}>
                                                  {chapter.chapter_title}
                                                </Typography>
                                                <Chip
                                                  label={
                                                    chapter.status === 'completed'
                                                      ? '已完成'
                                                      : chapter.status === 'processing'
                                                      ? '处理中'
                                                      : '等待中'
                                                  }
                                                  size="small"
                                                  color={
                                                    chapter.status === 'completed'
                                                      ? 'success'
                                                      : chapter.status === 'processing'
                                                      ? 'info'
                                                      : 'default'
                                                  }
                                                />
                                              </Box>
                                            }
                                            secondary={
                                              <Box>
                                                <LinearProgress
                                                  variant="determinate"
                                                  value={chPercentage}
                                                  sx={{ mb: 0.5, height: 4, borderRadius: 2 }}
                                                />
                                                <Typography variant="caption" color="text.secondary">
                                                  {chProgress.current} / {chProgress.total} ({chPercentage}%)
                                                </Typography>
                                              </Box>
                                            }
                                          />
                                        </ListItem>
                                      )
                                    })}
                                </List>
                              </AccordionDetails>
                            </Accordion>
                          </TableCell>
                        </TableRow>
                      )}
                    </React.Fragment>
                  )
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  )
}

export default TaskProgressPage
