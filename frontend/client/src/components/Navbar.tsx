import React, { useState } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Chip,
  useTheme,
  alpha,
} from '@mui/material';
import {
  Sports,
  Dashboard,
  EmojiEvents,
  Person,
  Settings,
  MoreVert,
  Refresh,
  Psychology,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { nflApi } from '../services/api';

const Navbar: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);

  // Get system status for the status indicator
  const { data: systemStatus, refetch: refetchStatus } = useQuery({
    queryKey: ['systemStatus'],
    queryFn: () => nflApi.healthCheck(),
    refetchInterval: 30000, // Refetch every 30 seconds
    retry: 1,
  });

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setMenuAnchor(event.currentTarget);
  };

  const handleMenuClose = () => {
    setMenuAnchor(null);
  };

  const handleNavigation = (path: string) => {
    navigate(path);
    handleMenuClose();
  };

  const getStatusColor = (): 'success' | 'warning' | 'error' | 'default' => {
    if (!systemStatus) return 'default';
    switch (systemStatus.status) {
      case 'healthy':
        return 'success';
      case 'degraded':
        return 'warning';
      case 'down':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusText = () => {
    if (!systemStatus) return 'Unknown';
    switch (systemStatus.status) {
      case 'healthy':
        return 'All Systems Operational';
      case 'degraded':
        return 'Service Degraded';
      case 'down':
        return 'Service Down';
      default:
        return 'Status Unknown';
    }
  };

  const isActivePage = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path);
  };

  return (
    <AppBar 
      position="sticky" 
      sx={{ 
        background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.9)} 0%, ${alpha(theme.palette.primary.dark, 0.9)} 100%)`,
        backdropFilter: 'blur(10px)',
        borderBottom: `1px solid ${alpha(theme.palette.primary.light, 0.2)}`,
      }}
    >
      <Toolbar>
        {/* Logo and Title */}
        <Box 
          sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            cursor: 'pointer',
            '&:hover': {
              opacity: 0.8,
            },
          }}
          onClick={() => navigate('/')}
        >
          <Sports sx={{ mr: 1, fontSize: 32, color: theme.palette.secondary.main }} />
          <Typography 
            variant="h5" 
            component="div" 
            sx={{ 
              fontWeight: 700,
              background: `linear-gradient(45deg, ${theme.palette.secondary.main}, ${theme.palette.secondary.light})`,
              backgroundClip: 'text',
              textFillColor: 'transparent',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            NFL Elite Assistant
          </Typography>
        </Box>

        {/* Navigation Buttons */}
        <Box sx={{ flexGrow: 1, display: 'flex', ml: 4 }}>
          <Button
            color="inherit"
            startIcon={<Dashboard />}
            onClick={() => navigate('/')}
            sx={{
              mr: 2,
              fontWeight: isActivePage('/') ? 600 : 400,
              backgroundColor: isActivePage('/') ? alpha(theme.palette.secondary.main, 0.2) : 'transparent',
              '&:hover': {
                backgroundColor: alpha(theme.palette.secondary.main, 0.1),
              },
            }}
          >
            Dashboard
          </Button>
          
          <Button
            color="inherit"
            startIcon={<EmojiEvents />}
            onClick={() => navigate('/rankings')}
            sx={{
              mr: 2,
              fontWeight: isActivePage('/rankings') ? 600 : 400,
              backgroundColor: isActivePage('/rankings') ? alpha(theme.palette.secondary.main, 0.2) : 'transparent',
              '&:hover': {
                backgroundColor: alpha(theme.palette.secondary.main, 0.1),
              },
            }}
          >
            Rankings
          </Button>

          <Button
            color="inherit"
            startIcon={<Psychology />}
            onClick={() => navigate('/analysis')}
            sx={{
              mr: 2,
              fontWeight: isActivePage('/analysis') ? 600 : 400,
              backgroundColor: isActivePage('/analysis') ? alpha(theme.palette.secondary.main, 0.2) : 'transparent',
              '&:hover': {
                backgroundColor: alpha(theme.palette.secondary.main, 0.1),
              },
            }}
          >
            Analysis
          </Button>

          <Button
            color="inherit"
            startIcon={<Person />}
            onClick={() => navigate('/player/search')}
            sx={{
              mr: 2,
              fontWeight: isActivePage('/player') ? 600 : 400,
              backgroundColor: isActivePage('/player') ? alpha(theme.palette.secondary.main, 0.2) : 'transparent',
              '&:hover': {
                backgroundColor: alpha(theme.palette.secondary.main, 0.1),
              },
            }}
          >
            Players
          </Button>
        </Box>

        {/* System Status Indicator */}
        <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
          <Chip
            label={getStatusText()}
            color={getStatusColor()}
            size="small"
            variant="outlined"
            sx={{
              fontWeight: 500,
              backgroundColor: (() => {
                const status = getStatusColor();
                return status !== 'default' 
                  ? alpha((theme.palette as any)[status].main, 0.1)
                  : alpha(theme.palette.grey[500], 0.1);
              })(),
              borderColor: (() => {
                const status = getStatusColor();
                return status !== 'default'
                  ? (theme.palette as any)[status].main
                  : theme.palette.grey[500];
              })(),
            }}
          />
          <IconButton
            color="inherit"
            onClick={() => refetchStatus()}
            size="small"
            sx={{ ml: 1 }}
            title="Refresh System Status"
          >
            <Refresh fontSize="small" />
          </IconButton>
        </Box>

        {/* More Menu */}
        <IconButton
          color="inherit"
          onClick={handleMenuOpen}
          size="large"
        >
          <MoreVert />
        </IconButton>

        <Menu
          anchorEl={menuAnchor}
          open={Boolean(menuAnchor)}
          onClose={handleMenuClose}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: 'right',
          }}
          transformOrigin={{
            vertical: 'top',
            horizontal: 'right',
          }}
        >
          <MenuItem onClick={() => handleNavigation('/status')}>
            <Settings sx={{ mr: 1 }} />
            System Status
          </MenuItem>
          <MenuItem onClick={() => handleNavigation('/settings')}>
            <Settings sx={{ mr: 1 }} />
            Settings
          </MenuItem>
          <MenuItem onClick={() => window.open('https://github.com/anthropics/claude-code', '_blank')}>
            <Person sx={{ mr: 1 }} />
            About
          </MenuItem>
        </Menu>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;