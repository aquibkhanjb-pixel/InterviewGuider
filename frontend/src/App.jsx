import React, { useState, useEffect } from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { CssBaseline, Box, Alert, Snackbar, CircularProgress, Typography } from '@mui/material';
import Dashboard from './components/Dashboard/Dashboard.jsx';
import CompanyComparison from './components/CompanyComparison/CompanyComparison.jsx';
import { interviewAPI } from './services/api.js';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const theme = createTheme({
  palette: {
    primary: {
      main: '#2563eb',
      light: '#60a5fa',
      dark: '#1d4ed8',
    },
    secondary: {
      main: '#7c3aed',
      light: '#a78bfa',
      dark: '#5b21b6',
    },
    error: {
      main: '#dc2626',
      light: '#f87171',
    },
    warning: {
      main: '#f59e0b',
      light: '#fbbf24',
    },
    success: {
      main: '#059669',
      light: '#34d399',
    },
    background: {
      default: '#f8fafc',
      paper: '#ffffff',
    },
    text: {
      primary: '#1e293b',
      secondary: '#64748b',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 700,
      fontSize: '2.125rem',
    },
    h5: {
      fontWeight: 600,
      fontSize: '1.5rem',
    },
    h6: {
      fontWeight: 600,
      fontSize: '1.25rem',
    },
  },
  shape: {
    borderRadius: 12,
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
          borderRadius: 16,
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 600,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
  },
});

function App() {
  const [apiHealthy, setApiHealthy] = useState(null);
  const [notification, setNotification] = useState({ 
    open: false, 
    message: '', 
    severity: 'info' 
  });

  useEffect(() => {
    checkAPIHealth();
  }, []);

  const checkAPIHealth = async (retries = 4, delayMs = 8000) => {
    for (let attempt = 1; attempt <= retries; attempt++) {
      try {
        const response = await interviewAPI.healthCheck();
        if (response.data.status === 'healthy') {
          setApiHealthy(true);
          return;
        }
      } catch (_) {
        // swallow — will retry
      }
      if (attempt < retries) {
        await new Promise(res => setTimeout(res, delayMs));
      }
    }
    // all retries exhausted
    setApiHealthy(false);
    showNotification('Unable to connect to backend API. It may be waking up — please refresh in 30 seconds.', 'warning');
  };

  const showNotification = (message, severity = 'info') => {
    setNotification({ open: true, message, severity });
  };

  const handleCloseNotification = () => {
    setNotification({ ...notification, open: false });
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default' }}>
          {apiHealthy === null && (
            <Box display="flex" alignItems="center" justifyContent="center" sx={{ py: 1, bgcolor: '#fff8e1' }}>
              <CircularProgress size={16} sx={{ mr: 1 }} />
              <Typography variant="body2" color="text.secondary">
                Connecting to backend — Render free tier may take up to 30 s to wake up…
              </Typography>
            </Box>
          )}
          {apiHealthy === false && (
            <Alert severity="warning" sx={{ mb: 0 }}>
              Backend is not responding. It may still be waking up — please wait 30 s and refresh.
            </Alert>
          )}
          
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route 
              path="/dashboard" 
              element={<Dashboard onNotification={showNotification} />} 
            />
            <Route 
              path="/compare" 
              element={<CompanyComparison onNotification={showNotification} />} 
            />
          </Routes>

          <Snackbar
            open={notification.open}
            autoHideDuration={6000}
            onClose={handleCloseNotification}
          >
            <Alert 
              onClose={handleCloseNotification} 
              severity={notification.severity}
              sx={{ width: '100%' }}
            >
              {notification.message}
            </Alert>
          </Snackbar>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;