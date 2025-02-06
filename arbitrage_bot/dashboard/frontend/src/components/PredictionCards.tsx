import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  LocalGasStation as GasIcon,
  WaterDrop as LiquidityIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useWebSocket } from '../providers/WebSocketProvider';
import { formatDistanceToNow } from 'date-fns';

interface PredictionCardProps {
  title: string;
  value: string;
  confidence: number;
  uncertainty: number;
  icon: React.ReactNode;
  trend?: number;
  info?: string;
}

const PredictionCard: React.FC<PredictionCardProps> = ({
  title,
  value,
  confidence,
  uncertainty,
  icon,
  trend,
  info,
}) => (
  <Card sx={{ height: '100%' }}>
    <CardContent>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box sx={{ mr: 1, color: 'primary.main' }}>{icon}</Box>
          <Typography variant="h6" component="div">
            {title}
          </Typography>
        </Box>
        {info && (
          <Tooltip title={info}>
            <IconButton size="small">
              <InfoIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      <Typography variant="h4" component="div" sx={{ mb: 2 }}>
        {value}
        {trend !== undefined && (
          <Box
            component="span"
            sx={{
              ml: 1,
              color: trend >= 0 ? 'success.main' : 'error.main',
              display: 'inline-flex',
              alignItems: 'center',
              typography: 'body2',
            }}
          >
            <TrendingUpIcon
              sx={{
                transform: trend >= 0 ? 'none' : 'rotate(180deg)',
                fontSize: '1rem',
                mr: 0.5,
              }}
            />
            {Math.abs(trend).toFixed(1)}%
          </Box>
        )}
      </Typography>

      <Box sx={{ mb: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
          <Typography variant="body2" color="textSecondary">
            Confidence
          </Typography>
          <Typography variant="body2" color="textSecondary">
            {(confidence * 100).toFixed(0)}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={confidence * 100}
          color={confidence >= 0.8 ? 'success' : confidence >= 0.6 ? 'warning' : 'error'}
          sx={{ height: 6, borderRadius: 1 }}
        />
      </Box>

      {uncertainty > 0.3 && (
        <Box sx={{ display: 'flex', alignItems: 'center', color: 'warning.main', mt: 1 }}>
          <WarningIcon fontSize="small" sx={{ mr: 0.5 }} />
          <Typography variant="body2">High uncertainty: {(uncertainty * 100).toFixed(0)}%</Typography>
        </Box>
      )}
    </CardContent>
  </Card>
);

const PredictionCards: React.FC = () => {
  const { lastUpdate } = useWebSocket();

  if (!lastUpdate) return null;

  const { gas, liquidity } = lastUpdate.predictions;

  const formatGasPrice = (price: number): string => {
    return `${(price / 1e9).toFixed(1)} gwei`;
  };

  const formatLiquidity = (amount: number): string => {
    return `$${(amount / 1e6).toFixed(2)}M`;
  };

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} md={6}>
        <PredictionCard
          title="Gas Price"
          value={formatGasPrice(gas.price)}
          confidence={gas.confidence}
          uncertainty={gas.uncertainty}
          icon={<GasIcon />}
          trend={-5.2} // Example trend, replace with actual calculation
          info="Predicted gas price for the next block"
        />
      </Grid>
      <Grid item xs={12} md={6}>
        <PredictionCard
          title="Liquidity"
          value={formatLiquidity(liquidity.total)}
          confidence={liquidity.confidence}
          uncertainty={liquidity.uncertainty}
          icon={<LiquidityIcon />}
          trend={2.8} // Example trend, replace with actual calculation
          info="Predicted available liquidity across monitored pools"
        />
      </Grid>
      {lastUpdate.timestamp && (
        <Grid item xs={12}>
          <Typography variant="caption" color="textSecondary">
            Last updated {formatDistanceToNow(new Date(lastUpdate.timestamp))} ago
          </Typography>
        </Grid>
      )}
    </Grid>
  );
};

export default PredictionCards;