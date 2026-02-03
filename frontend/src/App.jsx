import React, { useState, useEffect } from 'react'
import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Chip,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Divider,
  Container,
  Button,
  useMediaQuery,
  Tabs,
  Tab,
  Paper,
} from '@mui/material'
import {
  AutoFixHigh,
  CheckCircle,
  Menu as MenuIcon,
  Description as DescriptionIcon,
  Settings as SettingsIcon,
  Assignment as AssignmentIcon,
  List as ListIcon,
  Close as CloseIcon,
} from '@mui/icons-material'
import { useTheme } from '@mui/material/styles'
import TextUpload from './components/TextUpload'
import CorrectionProgress from './components/CorrectionProgress'
import TextComparison from './components/TextComparison'
import SettingsPage from './components/SettingsPage'
import TaskProgressPage from './components/TaskProgressPage'
import ResultListPage from './components/ResultListPage'
import ComparisonViewPage from './components/ComparisonViewPage'
import { correctionService } from './services/api'

// Tab页面类型定义
const TAB_TYPES = {
  TEXT_CORRECTION: 'text_correction',
  TASK_PROGRESS: 'task_progress',
  RESULT_LIST: 'result_list',
  SETTINGS: 'settings',
  COMPARISON: 'comparison',
}

// Tab页面配置
const TAB_CONFIG = {
  [TAB_TYPES.TEXT_CORRECTION]: {
    id: TAB_TYPES.TEXT_CORRECTION,
    label: '文本校对',
    icon: DescriptionIcon,
    closable: false, // 主页面不可关闭
  },
  [TAB_TYPES.TASK_PROGRESS]: {
    id: TAB_TYPES.TASK_PROGRESS,
    label: '任务进度',
    icon: AssignmentIcon,
    closable: true,
  },
  [TAB_TYPES.RESULT_LIST]: {
    id: TAB_TYPES.RESULT_LIST,
    label: '比对结果',
    icon: ListIcon,
    closable: true,
  },
  [TAB_TYPES.SETTINGS]: {
    id: TAB_TYPES.SETTINGS,
    label: '系统配置',
    icon: SettingsIcon,
    closable: true,
  },
  [TAB_TYPES.COMPARISON]: {
    id: TAB_TYPES.COMPARISON,
    label: '比对结果',
    icon: DescriptionIcon,
    closable: true,
  },
}

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [originalText, setOriginalText] = useState('')
  const [correctedText, setCorrectedText] = useState('')
  const [isProcessing, setIsProcessing] = useState(false)
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const [error, setError] = useState(null)
  const [warning, setWarning] = useState(null)
  // 比对结果页面状态
  const [comparisonData, setComparisonData] = useState(null)
  // 输入框文本状态（提升到App组件，避免切换页面时丢失）
  const [inputText, setInputText] = useState('')
  // 模型选择状态（提升到App组件，避免切换页面时丢失）
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedModelName, setSelectedModelName] = useState('')
  
  // 初始化默认模型配置（只在首次加载时执行）
  useEffect(() => {
    const initDefaultModels = async () => {
      try {
        const modelsData = await correctionService.getModels()
        if (!selectedProvider && modelsData.default_provider) {
          setSelectedProvider(modelsData.default_provider)
        }
        if (!selectedModelName && modelsData.default_model) {
          setSelectedModelName(modelsData.default_model)
        }
      } catch (error) {
        console.error('初始化默认模型配置失败:', error)
      }
    }
    initDefaultModels()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  
  // Tab管理状态
  const [tabs, setTabs] = useState([
    { id: TAB_TYPES.TEXT_CORRECTION, type: TAB_TYPES.TEXT_CORRECTION, label: '文本校对', data: null },
  ])
  const [activeTabId, setActiveTabId] = useState(TAB_TYPES.TEXT_CORRECTION)

  const theme = useTheme()
  const isDesktop = useMediaQuery(theme.breakpoints.up('md'))
  const drawerWidth = 240

  const handleTextSubmit = async (text, options) => {
    setIsProcessing(true)
    setError(null)
    setWarning(null)
    setProgress({ current: 0, total: 0 })
    setOriginalText(text)
    setCorrectedText('')

    try {
      const result = await correctionService.correctText(text, options, (current, total) => {
        setProgress({ current, total })
      })

      // 检查是否有失败
      if (result.has_failures) {
        const failedCount = result.failed_chunks || 0
        const totalCount = result.total_chunks || 0
        if (failedCount === totalCount) {
          // 全部失败：视为失败，不展示结果
          setError(`校对失败：${failedCount}/${totalCount} 个片段全部失败，请检查API配置或网络连接。`)
          setCorrectedText('')
          return
        }
        // 部分失败：视为警告，但仍可展示结果（失败片段使用原文）
        setWarning(`校对完成（有警告）：${failedCount}/${totalCount} 个片段失败，已用原文替代失败片段。`)
      }

      setCorrectedText(result.corrected)

      // 注意：结果已由后端自动保存到比对结果列表
      // 即使前端超时断开，后端完成后也会保存结果
    } catch (err) {
      setError(err.message || '校对失败，请重试')
      console.error('校对错误:', err)
      setCorrectedText('')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleFileSubmit = async (file, options) => {
    setIsProcessing(true)
    setError(null)
    setWarning(null)
    setProgress({ current: 0, total: 0 })
    setOriginalText('')
    setCorrectedText('')

    try {
      const result = await correctionService.correctFile(file, options)

      // 检查是否有失败
      if (result.has_failures) {
        const failedCount = result.failed_chunks || 0
        const totalCount = result.total_chunks || 0
        if (failedCount === totalCount) {
          setError(`校对失败：${failedCount}/${totalCount} 个片段全部失败，请检查API配置或网络连接。`)
          setOriginalText('')
          setCorrectedText('')
          return
        }
        setWarning(`校对完成（有警告）：${failedCount}/${totalCount} 个片段失败，已用原文替代失败片段。`)
      }

      setOriginalText(result.original)
      setCorrectedText(result.corrected)
      setProgress({
        current: result.total_chunks || 0,
        total: result.total_chunks || 0,
      })
    } catch (err) {
      setError(err.message || '校对失败，请重试')
      console.error('文件校对错误:', err)
      setOriginalText('')
      setCorrectedText('')
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

  // Tab管理函数
  const openTab = (tabType, label, data = null) => {
    setTabs((prev) => {
      // 检查是否已存在相同类型的tab（比对结果除外，可以多个）
      if (tabType !== TAB_TYPES.COMPARISON) {
        const existingTab = prev.find((t) => t.type === tabType)
        if (existingTab) {
          setActiveTabId(existingTab.id)
          // 如果传入了新数据，更新tab数据
          if (data) {
            return prev.map((t) => 
              t.id === existingTab.id ? { ...t, data } : t
            )
          }
          return prev
        }
      }
      
      // 创建新tab
      const tabId = tabType === TAB_TYPES.TEXT_CORRECTION 
        ? TAB_TYPES.TEXT_CORRECTION 
        : `${tabType}_${Date.now()}`
      const newTab = {
        id: tabId,
        type: tabType,
        label: label,
        data: data,
      }
      
      setActiveTabId(tabId)
      return [...prev, newTab]
    })
  }

  const closeTab = (tabId, e) => {
    e?.stopPropagation() // 阻止事件冒泡
    
    setTabs((prev) => {
      const newTabs = prev.filter((t) => t.id !== tabId)
      
      // 如果关闭的是当前激活的tab，切换到其他tab
      if (tabId === activeTabId && newTabs.length > 0) {
        // 优先切换到文本校对页面
        const textCorrectionTab = newTabs.find((t) => t.type === TAB_TYPES.TEXT_CORRECTION)
        setActiveTabId(textCorrectionTab ? textCorrectionTab.id : newTabs[newTabs.length - 1].id)
      }
      
      return newTabs
    })
    
    // 如果关闭的是比对结果页面，清除比对数据
    const closedTab = tabs.find((t) => t.id === tabId)
    if (closedTab?.type === TAB_TYPES.COMPARISON) {
      setComparisonData(null)
    }
  }

  const switchTab = (tabId) => {
    setActiveTabId(tabId)
  }

  const openComparisonPage = (data = null) => {
    // 如果没有传入数据，使用当前页面的数据
    if (!data) {
      if (!originalText || !correctedText) return
      const comparisonData = {
        original: originalText,
        corrected: correctedText,
        filename: '当前校对结果',
      }
      openTab(TAB_TYPES.COMPARISON, '比对结果 - 当前校对结果', comparisonData)
    } else {
      const label = data.chapterTitle 
        ? `比对结果 - ${data.chapterTitle}`
        : `比对结果 - ${data.filename || '未知文件'}`
      openTab(TAB_TYPES.COMPARISON, label, data)
    }
  }

  const handleSelectMenu = (index) => {
    if (!isDesktop) {
      setSidebarOpen(false)
    }
    
    // 根据索引打开对应的tab
    const tabTypeMap = {
      0: TAB_TYPES.TEXT_CORRECTION,
      1: TAB_TYPES.TASK_PROGRESS,
      2: TAB_TYPES.RESULT_LIST,
      3: TAB_TYPES.SETTINGS,
    }
    
    const tabType = tabTypeMap[index]
    if (tabType) {
      const config = TAB_CONFIG[tabType]
      openTab(tabType, config.label)
    }
  }

  const handleBackFromComparison = () => {
    // 关闭当前比对结果tab，返回到文本校对页面
    const currentTab = tabs.find((t) => t.id === activeTabId)
    if (currentTab?.type === TAB_TYPES.COMPARISON) {
      closeTab(activeTabId, null)
    }
    // 确保文本校对页面存在
    const textCorrectionTab = tabs.find((t) => t.type === TAB_TYPES.TEXT_CORRECTION)
    if (textCorrectionTab) {
      setActiveTabId(textCorrectionTab.id)
    }
  }
  
  // 获取当前激活的tab
  const activeTab = tabs.find((t) => t.id === activeTabId)
  const mainTab = activeTab?.type || TAB_TYPES.TEXT_CORRECTION

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default', display: 'flex', flexDirection: 'column' }}>
      <AppBar 
        position="fixed" 
        elevation={0}
        sx={{ 
          bgcolor: 'background.paper',
          borderBottom: '1px solid',
          borderColor: 'divider',
          backdropFilter: 'blur(20px)',
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          zIndex: (theme) => theme.zIndex.drawer + 1,
        }}
      >
        <Toolbar 
          sx={{ 
            px: { xs: 2, sm: 3 },
            py: { xs: 1, sm: 1.5 },
            minHeight: { xs: '64px', sm: '72px' },
            justifyContent: 'space-between',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1 }}>
            {!isDesktop && (
              <IconButton
                edge="start"
                onClick={() => setSidebarOpen(true)}
                sx={{ 
                  mr: 1,
                  color: 'text.primary',
                }}
              >
                <MenuIcon />
              </IconButton>
            )}

            {/* Logo/Icon */}
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: { xs: 40, sm: 44 },
                height: { xs: 40, sm: 44 },
                borderRadius: 1.5,
                bgcolor: 'primary.main',
                color: 'white',
                flexShrink: 0,
                boxShadow: (theme) =>
                  `0 2px 8px ${theme.palette.mode === 'light' ? 'rgba(0, 167, 111, 0.35)' : 'rgba(0, 167, 111, 0.5)'}`,
              }}
            >
              <AutoFixHigh sx={{ fontSize: { xs: 22, sm: 26 } }} />
            </Box>

            {/* Title */}
            <Box>
              <Typography 
                variant="h6" 
                component="div" 
                sx={{ 
                  fontWeight: 600,
                  letterSpacing: '-0.01em',
                  color: 'text.primary',
                  fontSize: { xs: '1rem', sm: '1.125rem' },
                  lineHeight: 1.3,
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
                  mt: 0.25,
                }}
              >
                AI 驱动的智能文本校对平台
              </Typography>
            </Box>
          </Box>

          {/* Status Badge */}
          <Box sx={{ display: { xs: 'none', sm: 'flex' }, alignItems: 'center' }}>
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

      {/* 主体区域：左侧菜单 + 右侧内容 */}
      <Box
        sx={{
          display: 'flex',
          flexGrow: 1,
          bgcolor: 'background.default',
        }}
      >
        {/* 侧边菜单 */}
        <Drawer
          variant={isDesktop ? 'permanent' : 'temporary'}
          open={isDesktop ? true : sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              boxSizing: 'border-box',
              borderRight: '1px solid',
              borderColor: 'divider',
              mt: { xs: '64px', sm: '72px' },
              bgcolor: 'background.paper',
              backgroundImage: (theme) =>
                theme.palette.mode === 'light'
                  ? 'linear-gradient(to bottom, #F9FAFB, #FFFFFF)'
                  : 'none',
              boxShadow: 'none',
            },
          }}
        >
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              height: '100%',
              pt: 2,
            }}
          >
            <List
              sx={{
                flexGrow: 1,
                px: 1,
                '& .MuiListItemButton-root': {
                  borderRadius: 1.5,
                  mb: 0.5,
                  minHeight: 48,
                  transition: 'all 0.2s ease-out',
                  px: 1.5,
                  color: 'text.secondary',
                  '& .MuiListItemIcon-root': {
                    minWidth: 40,
                    color: 'text.secondary',
                  },
                  '& .MuiListItemText-primary': {
                    fontSize: 14,
                    fontWeight: 500,
                  },
                  '& .MuiListItemText-secondary': {
                    fontSize: 11,
                  },
                },
                '& .MuiListItemButton-root.Mui-selected': {
                  bgcolor: 'rgba(0, 167, 111, 0.12)',
                  color: 'primary.main',
                  '& .MuiListItemIcon-root': {
                    color: 'primary.main',
                  },
                  '& .MuiListItemText-primary': {
                    fontWeight: 600,
                  },
                  '&:hover': {
                    bgcolor: 'rgba(0, 167, 111, 0.16)',
                  },
                },
                '& .MuiListItemButton-root:not(.Mui-selected):hover': {
                  bgcolor: 'action.hover',
                },
              }}
            >
              <ListItemButton
                selected={mainTab === TAB_TYPES.TEXT_CORRECTION}
                onClick={() => handleSelectMenu(0)}
              >
                <ListItemIcon>
                  <DescriptionIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary="文本校对"
                  secondary="上传与精校文本"
                  primaryTypographyProps={{ 
                    fontSize: 14, 
                    fontWeight: mainTab === TAB_TYPES.TEXT_CORRECTION ? 600 : 500,
                  }}
                  secondaryTypographyProps={{ fontSize: 11 }}
                />
              </ListItemButton>

              <ListItemButton
                selected={mainTab === TAB_TYPES.TASK_PROGRESS}
                onClick={() => handleSelectMenu(1)}
              >
                <ListItemIcon>
                  <AssignmentIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary="任务进度"
                  secondary="查看后台任务状态"
                  primaryTypographyProps={{ 
                    fontSize: 14, 
                    fontWeight: mainTab === TAB_TYPES.TASK_PROGRESS ? 600 : 500,
                  }}
                  secondaryTypographyProps={{ fontSize: 11 }}
                />
              </ListItemButton>

              <ListItemButton
                selected={mainTab === TAB_TYPES.RESULT_LIST}
                onClick={() => handleSelectMenu(2)}
              >
                <ListItemIcon>
                  <ListIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary="比对结果"
                  secondary="查看和管理结果"
                  primaryTypographyProps={{ 
                    fontSize: 14, 
                    fontWeight: mainTab === TAB_TYPES.RESULT_LIST ? 600 : 500,
                  }}
                  secondaryTypographyProps={{ fontSize: 11 }}
                />
              </ListItemButton>

              <ListItemButton
                selected={mainTab === TAB_TYPES.SETTINGS}
                onClick={() => handleSelectMenu(3)}
              >
                <ListItemIcon>
                  <SettingsIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary="系统配置"
                  secondary="模型与参数设置"
                  primaryTypographyProps={{ 
                    fontSize: 14, 
                    fontWeight: mainTab === TAB_TYPES.SETTINGS ? 600 : 500,
                  }}
                  secondaryTypographyProps={{ fontSize: 11 }}
                />
              </ListItemButton>
            </List>
          </Box>
        </Drawer>

        {/* 右侧内容区域：flex 约束高度，避免设置页溢出产生滚动条 */}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
            mt: { xs: '64px', sm: '72px' },
            bgcolor: 'background.default',
          }}
        >
          <Container 
            maxWidth="xl" 
            sx={{ 
              px: { xs: 2, sm: 3 },
              py: { xs: 2, sm: 3 },
              flex: 1,
              minHeight: 0,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            {/* Tab栏 - 常驻显示 */}
            <Box
              sx={{
                mb: 3,
                borderBottom: '1px solid',
                borderColor: 'divider',
                position: 'relative',
              }}
            >
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'flex-end',
                  overflowX: 'auto',
                  overflowY: 'hidden',
                  '&::-webkit-scrollbar': {
                    height: '4px',
                  },
                  '&::-webkit-scrollbar-thumb': {
                    backgroundColor: 'divider',
                    borderRadius: '2px',
                  },
                }}
              >
                {tabs.map((tab, index) => {
                  const isActive = tab.id === activeTabId
                  const config = TAB_CONFIG[tab.type]
                  const Icon = config?.icon || DescriptionIcon
                  const isClosable = config?.closable !== false && tabs.length > 1
                  
                  return (
                    <Box
                      key={tab.id}
                      onClick={() => switchTab(tab.id)}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        px: 2,
                        py: 1.25,
                        minWidth: 120,
                        maxWidth: 240,
                        cursor: 'pointer',
                        position: 'relative',
                        borderBottom: isActive ? '2px solid' : '2px solid transparent',
                        borderColor: isActive ? 'primary.main' : 'transparent',
                        bgcolor: 'transparent',
                        transition: 'all 0.2s ease-out',
                        mb: '-1px', // 与底部边框重叠
                        '&:hover': {
                          bgcolor: isActive ? 'transparent' : 'action.hover',
                        },
                      }}
                    >
                      <Icon 
                        fontSize="small" 
                        sx={{ 
                          color: isActive ? 'primary.main' : 'text.secondary',
                          flexShrink: 0,
                          fontSize: '18px',
                        }} 
                      />
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: isActive ? 600 : 500,
                          color: isActive ? 'text.primary' : 'text.secondary',
                          flex: 1,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          fontSize: '0.875rem',
                          lineHeight: 1.5,
                        }}
                      >
                        {tab.label}
                      </Typography>
                      {isClosable && (
                        <IconButton
                          size="small"
                          onClick={(e) => closeTab(tab.id, e)}
                          sx={{
                            p: 0.25,
                            ml: 0.5,
                            flexShrink: 0,
                            width: 20,
                            height: 20,
                            color: 'text.secondary',
                            transition: 'all 0.15s ease-out',
                            '&:hover': {
                              bgcolor: 'error.light',
                              color: 'error.main',
                            },
                          }}
                        >
                          <CloseIcon sx={{ fontSize: '16px' }} />
                        </IconButton>
                      )}
                    </Box>
                  )
                })}
              </Box>
            </Box>

            {/* 页面内容区：占满剩余高度；设置页内部不溢出，其他页可在此区域内滚动 */}
            <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
            {/* 页面标题区域 */}
            {mainTab !== TAB_TYPES.COMPARISON && (
              <Box
                sx={{
                  mb: 3,
                  flexShrink: 0,
                }}
              >
                <Typography 
                  variant="h5" 
                  sx={{ 
                    mb: 0.5,
                    fontWeight: 600,
                    color: 'text.primary',
                    fontSize: { xs: '1.25rem', sm: '1.5rem' },
                  }}
                >
                  {mainTab === TAB_TYPES.TEXT_CORRECTION
                    ? '文本校对'
                    : mainTab === TAB_TYPES.TASK_PROGRESS
                    ? '任务进度'
                    : mainTab === TAB_TYPES.RESULT_LIST
                    ? '比对结果'
                    : '系统配置'}
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: 'text.secondary',
                    fontSize: '0.875rem',
                  }}
                >
                  {mainTab === TAB_TYPES.TEXT_CORRECTION
                    ? '上传原文、查看 AI 精校进度与对比结果'
                    : mainTab === TAB_TYPES.TASK_PROGRESS
                    ? '查看后台任务处理进度和状态'
                    : mainTab === TAB_TYPES.RESULT_LIST
                    ? '查看和管理已完成的比对结果'
                    : '管理模型、温度等高级参数配置'}
                </Typography>
              </Box>
            )}

            {/* 文本校对页面 */}
            {mainTab === TAB_TYPES.TEXT_CORRECTION && (
              <>
                <TextUpload
                  onSubmit={handleTextSubmit}
                  onFileSubmit={handleFileSubmit}
                  disabled={isProcessing}
                  inputText={inputText}
                  onInputTextChange={setInputText}
                  selectedProvider={selectedProvider}
                  onProviderChange={setSelectedProvider}
                  selectedModelName={selectedModelName}
                  onModelNameChange={setSelectedModelName}
                />

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

                {warning && !error && (
                  <Box 
                    sx={{ 
                      mt: 2, 
                      p: 2.5, 
                      bgcolor: 'warning.light', 
                      color: 'warning.dark',
                      borderRadius: 2,
                      border: '1px solid',
                      borderColor: 'warning.main',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 1,
                    }}
                  >
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {warning}
                    </Typography>
                  </Box>
                )}

                {correctedText && (
                  <Box
                    sx={{
                      mt: 2,
                      p: { xs: 2.5, sm: 3 },
                      borderRadius: 2,
                      border: '1px solid',
                      borderColor: 'divider',
                      bgcolor: 'background.paper',
                      display: 'flex',
                      flexDirection: { xs: 'column', sm: 'row' },
                      alignItems: { xs: 'flex-start', sm: 'center' },
                      justifyContent: 'space-between',
                      gap: 2,
                    }}
                  >
                    <Box>
                      <Typography
                        variant="subtitle1"
                        sx={{ fontWeight: 600, mb: 0.5, color: 'text.primary' }}
                      >
                        {warning ? '文本已生成（部分片段失败）' : '文本已精校完成'}
                      </Typography>
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        {warning
                          ? '你仍可查看比对结果，但失败片段已用原文替代。'
                          : '点击右侧按钮，在新的页面中查看详细比对结果。'}
                      </Typography>
                    </Box>
                    <Button
                      variant="contained"
                      color="primary"
                      onClick={() => openComparisonPage()}
                      sx={{ whiteSpace: 'nowrap' }}
                    >
                      查看比对结果
                    </Button>
                  </Box>
                )}
              </>
            )}

            {/* 任务进度页面 */}
            {mainTab === TAB_TYPES.TASK_PROGRESS && <TaskProgressPage />}

            {/* 比对结果列表页面 */}
            {mainTab === TAB_TYPES.RESULT_LIST && (
              <ResultListPage 
                onViewComparison={(data) => openComparisonPage(data)}
              />
            )}

            {/* 系统配置页面 */}
            {mainTab === TAB_TYPES.SETTINGS && <SettingsPage />}

            {/* 比对结果展示页面 */}
            {mainTab === TAB_TYPES.COMPARISON && activeTab && activeTab.data && (
              <ComparisonViewPage
                original={activeTab.data.original}
                corrected={activeTab.data.corrected}
                filename={activeTab.data.filename}
                chapterTitle={activeTab.data.chapterTitle}
                onBack={handleBackFromComparison}
                onExport={() => {
                  if (activeTab.data?.corrected) {
                    const blob = new Blob([activeTab.data.corrected], { type: 'text/plain;charset=utf-8' })
                    const url = URL.createObjectURL(blob)
                    const link = document.createElement('a')
                    link.href = url
                    const exportFilename = activeTab.data.chapterTitle
                      ? `精校文本_${activeTab.data.chapterTitle}_${activeTab.data.filename || new Date().getTime()}.txt`
                      : `精校文本_${activeTab.data.filename || new Date().getTime()}.txt`
                    link.download = exportFilename
                    document.body.appendChild(link)
                    link.click()
                    document.body.removeChild(link)
                    URL.revokeObjectURL(url)
                  }
                }}
              />
            )}
            </Box>
          </Container>
        </Box>
      </Box>
    </Box>
  )
}

export default App
