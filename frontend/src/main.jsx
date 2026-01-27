import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import App from './App'

// 导入Google字体
const link = document.createElement('link')
link.href = 'https://fonts.googleapis.com/css2?family=Open+Sans:wght@300;400;500;600;700&family=Poppins:wght@400;500;600;700&display=swap'
link.rel = 'stylesheet'
document.head.appendChild(link)

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2563EB', // Trust blue
      light: '#3B82F6',
      dark: '#1E40AF',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#F97316', // Orange CTA
      light: '#FB923C',
      dark: '#EA580C',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#F8FAFC', // Light gray background
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1E293B', // Dark slate
      secondary: '#64748B', // Medium slate
    },
    divider: '#E2E8F0', // Light border
    error: {
      main: '#EF4444',
      light: '#FEE2E2',
      dark: '#DC2626',
    },
    success: {
      main: '#10B981',
      light: '#D1FAE5',
      dark: '#059669',
    },
  },
  typography: {
    fontFamily: '"Open Sans", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontFamily: '"Poppins", sans-serif',
      fontWeight: 600,
      letterSpacing: '-0.02em',
    },
    h2: {
      fontFamily: '"Poppins", sans-serif',
      fontWeight: 600,
      letterSpacing: '-0.01em',
    },
    h3: {
      fontFamily: '"Poppins", sans-serif',
      fontWeight: 600,
    },
    h4: {
      fontFamily: '"Poppins", sans-serif',
      fontWeight: 600,
    },
    h5: {
      fontFamily: '"Poppins", sans-serif',
      fontWeight: 600,
    },
    h6: {
      fontFamily: '"Poppins", sans-serif',
      fontWeight: 600,
    },
    button: {
      fontWeight: 600,
      textTransform: 'none',
      letterSpacing: '0.01em',
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '10px 24px',
          transition: 'all 0.2s ease-out',
          '&:hover': {
            transform: 'translateY(-1px)',
            boxShadow: '0 4px 12px rgba(37, 99, 235, 0.2)',
          },
        },
        contained: {
          boxShadow: '0 2px 8px rgba(37, 99, 235, 0.15)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.1)',
          transition: 'all 0.2s ease-out',
        },
        elevation1: {
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.1)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            transition: 'all 0.2s ease-out',
            '&:hover': {
              '& .MuiOutlinedInput-notchedOutline': {
                borderColor: '#3B82F6',
              },
            },
            '&.Mui-focused': {
              '& .MuiOutlinedInput-notchedOutline': {
                borderWidth: '2px',
              },
            },
          },
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        root: {
          minHeight: 48,
        },
        indicator: {
          height: 3,
          borderRadius: '3px 3px 0 0',
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          fontSize: '0.9375rem',
          minHeight: 48,
          transition: 'color 0.2s ease-out',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
          borderRadius: 6,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          // 确保AppBar文字颜色正确
          color: 'inherit',
        },
      },
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <App />
    </ThemeProvider>
  </React.StrictMode>
)
