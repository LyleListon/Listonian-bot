import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  useTheme,
} from '@mui/material';
import {
  Line,
  Bar,
  Doughnut,
} from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { useWebSocket } from '../providers/WebSocketProvider';
import { PerformanceMessage } from '../types/websocket';
import { format } from 'date-fns';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const PerformanceCharts: React.FC = () => {
  const theme = useTheme();
  const { lastMessage } = useWebSocket();

  // Cast lastMessage to PerformanceMessage if it's a performance type
  const performanceData = lastMessage?.type === 'performance'
    ? (lastMessage as PerformanceMessage).performance
    : [];

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: theme.palette.text.primary,
        },
      },
    },
    scales: {
      x: {
        grid: {
          color: theme.palette.divider,
        },
        ticks: {
          color: theme.palette.text.secondary,
        },
      },
      y: {
        grid: {
          color: theme.palette.divider,
        },
        ticks: {
          color: theme.palette.text.secondary,
        },
      },
    },
  };

  const profitChartData = {
    labels: performanceData.map(d => format(d.timestamp, 'HH:mm')),
    datasets: [
      {
        label: 'Profit (ETH)',
        data: performanceData.map(d => d.profit),
        borderColor: theme.palette.primary.main,
        backgroundColor: theme.palette.primary.main + '40',
        fill: true,
      },
    ],
  };

  const tradesChartData = {
    labels: performanceData.map(d => format(d.timestamp, 'HH:mm')),
    datasets: [
      {
        label: 'Number of Trades',
        data: performanceData.map(d => d.trades),
        backgroundColor: theme.palette.secondary.main,
      },
    ],
  };

  const successRateData = {
    labels: ['Successful', 'Failed'],
    datasets: [
      {
        data: [
          performanceData[performanceData.length - 1]?.successRate || 0,
          100 - (performanceData[performanceData.length - 1]?.successRate || 0),
        ],
        backgroundColor: [
          theme.palette.success.main,
          theme.palette.error.main,
        ],
      },
    ],
  };

  if (!performanceData.length) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="textSecondary">
          Waiting for performance data...
        </Typography>
      </Box>
    );
  }

  return (
    <Grid container spacing={3}>
      {/* Profit Chart */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Profit Over Time
            </Typography>
            <Box sx={{ height: 300 }}>
              <Line options={chartOptions} data={profitChartData} />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Trades Chart */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Trade Volume
            </Typography>
            <Box sx={{ height: 300 }}>
              <Bar options={chartOptions} data={tradesChartData} />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Success Rate Chart */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Success Rate
            </Typography>
            <Box sx={{ height: 300 }}>
              <Doughnut
                data={successRateData}
                options={{
                  ...chartOptions,
                  cutout: '70%',
                }}
              />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Gas Usage Chart */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Gas Usage
            </Typography>
            <Box sx={{ height: 300 }}>
              <Line
                options={chartOptions}
                data={{
                  labels: performanceData.map(d => format(d.timestamp, 'HH:mm')),
                  datasets: [
                    {
                      label: 'Gas Used (gwei)',
                      data: performanceData.map(d => d.gasUsed),
                      borderColor: theme.palette.warning.main,
                      backgroundColor: theme.palette.warning.main + '40',
                      fill: true,
                    },
                  ],
                }}
              />
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default PerformanceCharts;