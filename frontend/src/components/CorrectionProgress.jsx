import React from 'react'
import { Box, LinearProgress, Typography, Paper } from '@mui/material'

function CorrectionProgress({ current, total }) {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        校对进度
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <Box sx={{ width: '100%', mr: 1 }}>
          <LinearProgress variant="determinate" value={percentage} />
        </Box>
        <Box sx={{ minWidth: 80 }}>
          <Typography variant="body2" color="text.secondary">
            {current} / {total}
          </Typography>
        </Box>
      </Box>
      <Typography variant="body2" color="text.secondary">
        {percentage}% 完成
      </Typography>
    </Paper>
  )
}

export default CorrectionProgress
