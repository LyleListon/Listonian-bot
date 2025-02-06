import React, { useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Divider,
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
  ChartData,
  ChartOptions,
} from 'chart.js';
import { useWebSocket } from '../providers/WebSocketProvider';

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
  const { lastUpdate } = useWebSocket();

  const chartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          color: theme.palette.text.primary,
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
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

  const profitChartData = useMemo(() => {
    if (!lastUpdate) return null;

    const { trades, profit_loss } = lastUpdate.performance;
    const profitData: ChartData<'line'> = {
      labels: Array.from({ length: 10 }, (_, i) => `${i + 1}m ago`).reverse(),
      datasets: [
        {
          label: 'Cumulative Profit',
          data: Array(10).fill(profit_loss.net_profit / 10),
          borderColor: theme.palette.success.main,
          backgroundColor: theme.palette.success.main + '40',
          fill: true,
          tension: 0.4,
        },
      ],
    };

    return profitData;
  }, [lastUpdate, theme]);

  const winRateChartData = useMemo(() => {
    if (!lastUpdate) return null;

    const { trades } = lastUpdate.performance;
    const winRate = trades.successful / trades.total;
    const lossRate = 1 - winRate;

    const data: ChartData<'doughnut'> = {
      labels: ['Wins', 'Losses'],
      datasets: [
        {
          data: [winRate * 100, lossRate * 100],
          backgroundColor: [
            theme.palette.success.main,
            theme.palette.error.main,
          ],
          borderWidth: 0,
        },
      ],
    };

    return data;
  }, [lastUpdate, theme]);

  const riskMetricsData = useMemo(() => {
    if (!lastUpdate) return null;

    const { risk } = lastUpdate.performance;
    const data: ChartData<'bar'> = {
      labels: ['Drawdown', 'Exposure', 'Volatility'],
      datasets: [
        {
          label: 'Risk Metrics',
          data: [
            risk.drawdown * 100,
            risk.exposure * 100,
            risk.volatility * 100,
          ],
          backgroundColor: [
            theme.palette.warning.main,
            theme.palette.info.main,
            theme.palette.error.main,
          ],
        },
      ],
    };

    return data;
  }, [lastUpdate, theme]);

  if (!lastUpdate) return null;

  const { trades, profit_loss } = lastUpdate.performance;

  return (
    <Grid container spacing={2}>
      {/* Profit Chart */}
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Profit Performance
            </Typography>
            <Box sx={{ height: 300 }}>
              {profitChartData && (
                <Line options={chartOptions} data={profitChartData} />
              )}
            </Box>
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-around' }}>
              <Typography variant="body2" color="textSecondary">
                Total Profit: ${profit_loss.total_profit.toFixed(2)}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Net Profit: ${profit_loss.net_profit.toFixed(2)}
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Win Rate Chart */}
      <Grid item xs={12} md={6}>
        <Card sx={{ height: '100%' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Win Rate
            </Typography>
            <Box sx={{ height: 200, display: 'flex', justifyContent: 'center' }}>
              {winRateChartData && (
                <Doughnut
                  data={winRateChartData}
                  options={{
                    ...chartOptions,
                    cutout: '70%',
                  }}
                />
              )}
            </Box>
            <Box sx={{ mt: 2, textAlign: 'center' }}>
              <Typography variant="h4">
                {((trades.successful / trades.total) * 100).toFixed(1)}%
              </Typography>
              <Typography variant="body2" color="textSecondary">
                {trades.successful} / {trades.total} trades
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Risk Metrics */}
      <Grid item xs={12} md={6}>
        <Card sx={{ height: '100%' }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Risk Metrics
            </Typography>
            <Box sx={{ height: 200 }}>
              {riskMetricsData && (
                <Bar
                  data={riskMetricsData}
                  options={{
                    ...chartOptions,
                    indexAxis: 'y' as const,
                  }}
                />
              )}
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default PerformanceCharts;