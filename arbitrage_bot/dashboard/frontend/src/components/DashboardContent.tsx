import React from 'react';
import { Box, Grid, Paper, Typography, useTheme } from '@mui/material';
import PredictionCards from './PredictionCards';
import PerformanceCharts from './PerformanceCharts';
import OpportunityList from './OpportunityList';
import { useWebSocket } from '../providers/WebSocketProvider';

const DashboardContent: React.FC = () => {
  const theme = useTheme();
  const { connected, lastUpdate } = useWebSocket();

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      {/* Connection Status */}
      <Paper
        sx={{
          p: 2,
          mb: 3,
          backgroundColor: connected
            ? theme.palette.success.dark
            : theme.palette.error.dark,
        }}
      >
        <Typography variant="h6" color="white">
          {connected ? 'Connected to Network' : 'Disconnected'}
        </Typography>
        <Typography variant="body2" color="white" sx={{ opacity: 0.8 }}>
          Last Update: {new Date(lastUpdate).toLocaleTimeString()}
        </Typography>
      </Paper>

      <Grid container spacing={3}>
        {/* Predictions Section */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h5" gutterBottom>
              ML Predictions
            </Typography>
            <PredictionCards />
          </Paper>
        </Grid>

        {/* Performance Charts */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2, mb: 3 }}>
            <Typography variant="h5" gutterBottom>
              Performance Metrics
            </Typography>
            <PerformanceCharts />
          </Paper>
        </Grid>

        {/* Opportunities List */}
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h5" gutterBottom>
              Active Opportunities
            </Typography>
            <OpportunityList />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardContent;