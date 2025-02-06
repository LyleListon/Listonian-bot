import React, { useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  LocalGasStation as GasIcon,
  Timeline as TimelineIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { useWebSocket } from '../providers/WebSocketProvider';
import { Opportunity } from '../types';

const OpportunityList: React.FC = () => {
  const { lastUpdate } = useWebSocket();

  const opportunities = useMemo(() => {
    return lastUpdate?.detector.opportunities || [];
  }, [lastUpdate]);

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  const formatProfit = (profit: number): string => {
    return `$${profit.toFixed(2)}`;
  };

  const formatGas = (gas: number): string => {
    return `${(gas / 1e9).toFixed(1)} gwei`;
  };

  const formatTimestamp = (timestamp: string): string => {
    return format(new Date(timestamp), 'HH:mm:ss');
  };

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" component="div">
            Active Opportunities ({opportunities.length})
          </Typography>
          <Tooltip title="Real-time updates">
            <TimelineIcon color="primary" />
          </Tooltip>
        </Box>

        <TableContainer sx={{ maxHeight: 400 }}>
          <Table stickyHeader size="small">
            <TableHead>
              <TableRow>
                <TableCell>Time</TableCell>
                <TableCell>Profit</TableCell>
                <TableCell>Gas</TableCell>
                <TableCell>Size</TableCell>
                <TableCell>Confidence</TableCell>
                <TableCell>Risk</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {opportunities.map((opp: Opportunity) => (
                <TableRow
                  key={`${opp.timestamp}-${opp.path.join('-')}`}
                  sx={{
                    '&:hover': {
                      backgroundColor: 'action.hover',
                    },
                  }}
                >
                  <TableCell>{formatTimestamp(opp.timestamp)}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <TrendingUpIcon
                        fontSize="small"
                        sx={{ mr: 1, color: 'success.main' }}
                      />
                      {formatProfit(opp.expected_profit)}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <GasIcon
                        fontSize="small"
                        sx={{ mr: 1, color: 'info.main' }}
                      />
                      {formatGas(opp.gas_cost)}
                    </Box>
                  </TableCell>
                  <TableCell>{formatProfit(opp.position_size)}</TableCell>
                  <TableCell>
                    <Chip
                      label={`${(opp.confidence * 100).toFixed(0)}%`}
                      color={getConfidenceColor(opp.confidence)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      {opp.risk_score > 0.7 && (
                        <Tooltip title="High Risk">
                          <WarningIcon
                            fontSize="small"
                            sx={{ mr: 1, color: 'warning.main' }}
                          />
                        </Tooltip>
                      )}
                      {(opp.risk_score * 100).toFixed(0)}%
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Tooltip title="View Details">
                      <IconButton size="small" onClick={() => console.log('View details', opp)}>
                        <TimelineIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
              {opportunities.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <Typography variant="body2" color="textSecondary">
                      No active opportunities
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </CardContent>
    </Card>
  );
};

export default OpportunityList;