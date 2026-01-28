import React from 'react'
import { Box, LinearProgress, Typography, Paper } from '@mui/material'

function CorrectionProgress({ current, total }) {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0

  return (
    <Paper 
      elevation={0}
      sx={{ 
        p: { xs: 3, sm: 3.5 },
        mb: 3,
        bgcolor: (theme) => theme.palette.mode === 'light' 
          ? 'rgba(0, 167, 111, 0.04)' 
          : 'rgba(0, 167, 111, 0.12)',
        border: '1px solid',
        borderColor: 'primary.light',
        borderRadius: 2,
      }}
    >
      <Typography 
        variant="h6" 
        gutterBottom
        sx={{ 
          fontWeight: 600,
          color: 'primary.dark',
        }}
      >
        校对进度
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
        <Box sx={{ width: '100%', mr: 2 }}>
          <LinearProgress 
            variant="determinate" 
            value={percentage}
            sx={{
              height: 8,
              borderRadius: 4,
              bgcolor: (theme) => theme.palette.mode === 'light'
                ? 'rgba(0, 167, 111, 0.12)'
                : 'rgba(0, 167, 111, 0.24)',
              '& .MuiLinearProgress-bar': {
                borderRadius: 4,
                bgcolor: 'primary.main',
              },
            }}
          />
        </Box>
        <Box sx={{ minWidth: 80, textAlign: 'right' }}>
          <Typography 
            variant="body2" 
            sx={{ 
              color: 'primary.dark',
              fontWeight: 600,
            }}
          >
            {current} / {total}
          </Typography>
        </Box>
      </Box>
      <Typography 
        variant="body2" 
        sx={{ 
          color: 'text.secondary',
          fontWeight: 500,
        }}
      >
        {percentage}% 完成
      </Typography>
    </Paper>
  )
}

export default CorrectionProgress
