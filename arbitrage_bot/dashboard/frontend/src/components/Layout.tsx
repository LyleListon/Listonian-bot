import React from 'react';
import { Box, AppBar, Toolbar, Typography, IconButton, Drawer, List, ListItem, ListItemIcon, ListItemText, useTheme } from '@mui/material';
import { styled } from '@mui/material/styles';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
} from '@mui/icons-material';
import { useState } from 'react';
import { useWebSocket } from '../providers/WebSocketProvider';

// Custom styled components
const drawerWidth = 240;

const Main = styled('main', { shouldForwardProp: (prop) => prop !== 'open' })<{
  open?: boolean;
}>(({ theme, open }) => ({
  flexGrow: 1,
  padding: theme.spacing(3),
  transition: theme.transitions.create('margin', {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  marginLeft: `-${drawerWidth}px`,
  ...(open && {
    transition: theme.transitions.create('margin', {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen,
    }),
    marginLeft: 0,
  }),
}));

const Layout: React.FC = () => {
  const [drawerOpen, setDrawerOpen] = useState(true);
  const theme = useTheme();
  const { connected, lastUpdate } = useWebSocket();

  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
  };

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
    { text: 'Opportunities', icon: <TimelineIcon />, path: '/opportunities' },
    { text: 'Performance', icon: <AssessmentIcon />, path: '/performance' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
  ];

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* App Bar */}
      <AppBar position="fixed" sx={{ zIndex: theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2 }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Arbitrage Dashboard
          </Typography>
          {/* Connection Status */}
          <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
            <Box
              sx={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                bgcolor: connected ? 'success.main' : 'error.main',
                mr: 1,
              }}
            />
            <Typography variant="body2">
              {connected ? 'Connected' : 'Disconnected'}
            </Typography>
          </Box>
          {/* Notifications */}
          <IconButton color="inherit">
            <NotificationsIcon />
          </IconButton>
        </Toolbar>
      </AppBar>

      {/* Side Drawer */}
      <Drawer
        variant="persistent"
        anchor="left"
        open={drawerOpen}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            bgcolor: 'background.paper',
          },
        }}
      >
        <Toolbar /> {/* Spacer for AppBar */}
        <List>
          {menuItems.map((item) => (
            <ListItem button key={item.text}>
              <ListItemIcon sx={{ color: 'primary.main' }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.text} />
            </ListItem>
          ))}
        </List>
      </Drawer>

      {/* Main Content */}
      <Main open={drawerOpen}>
        <Toolbar /> {/* Spacer for AppBar */}
        <Box sx={{ p: 3 }}>
          {/* Dashboard Content */}
          {lastUpdate && (
            <Box sx={{ display: 'grid', gap: 3, gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}>
              {/* Opportunity Cards */}
              <Box>
                <Typography variant="h6" gutterBottom>
                  Active Opportunities
                </Typography>
                {/* Add OpportunityList component here */}
              </Box>

              {/* Prediction Cards */}
              <Box>
                <Typography variant="h6" gutterBottom>
                  ML Predictions
                </Typography>
                {/* Add PredictionCards component here */}
              </Box>

              {/* Performance Charts */}
              <Box>
                <Typography variant="h6" gutterBottom>
                  Performance
                </Typography>
                {/* Add PerformanceCharts component here */}
              </Box>
            </Box>
          )}
        </Box>
      </Main>
    </Box>
  );
};

export default Layout;