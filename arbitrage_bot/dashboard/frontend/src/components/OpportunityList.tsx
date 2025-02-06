import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Box,
  Chip,
  useTheme,
} from '@mui/material';
import { useWebSocket } from '../providers/WebSocketProvider';
import { OpportunityMessage } from '../types/websocket';
import { formatDistanceToNow } from 'date-fns';

const OpportunityList: React.FC = () => {
  const theme = useTheme();
  const { lastMessage } = useWebSocket();

  // Keep track of recent opportunities (last 10)
  const [opportunities, setOpportunities] = React.useState<OpportunityMessage[]>([]);

  React.useEffect(() => {
    if (lastMessage?.type === 'opportunity') {
      const newOpportunity = lastMessage as OpportunityMessage;
      setOpportunities(prev => {
        const updated = [newOpportunity, ...prev].slice(0, 10);
        return updated;
      });
    }
  }, [lastMessage]);

  if (!opportunities.length) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="textSecondary">
          Waiting for arbitrage opportunities...
        </Typography>
      </Box>
    );
  }

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Route</TableCell>
            <TableCell align="right">Profit</TableCell>
            <TableCell align="right">Gas Cost</TableCell>
            <TableCell align="right">Net Profit</TableCell>
            <TableCell align="right">Time</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {opportunities.map((opportunity, index) => {
            const estimatedProfit = parseFloat(opportunity.profit);
            const gasCost = opportunity.estimatedGas * 1e-9; // Convert to ETH
            const netProfit = estimatedProfit - gasCost;

            return (
              <TableRow
                key={index}
                sx={{
                  '&:last-child td, &:last-child th': { border: 0 },
                  backgroundColor: netProfit > 0 
                    ? theme.palette.success.dark + '20'
                    : theme.palette.error.dark + '20',
                }}
              >
                <TableCell component="th" scope="row">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {opportunity.route.map((token, i) => (
                      <React.Fragment key={i}>
                        {i > 0 && (
                          <Typography color="textSecondary" sx={{ mx: 1 }}>
                            →
                          </Typography>
                        )}
                        <Chip
                          label={token.split('/').pop()?.toUpperCase()}
                          size="small"
                          sx={{
                            backgroundColor: theme.palette.primary.dark + '40',
                          }}
                        />
                      </React.Fragment>
                    ))}
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <Typography
                    color={estimatedProfit > 0 ? 'success.main' : 'error.main'}
                  >
                    {estimatedProfit.toFixed(6)} ETH
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography color="warning.main">
                    {gasCost.toFixed(6)} ETH
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography
                    color={netProfit > 0 ? 'success.main' : 'error.main'}
                    sx={{ fontWeight: 'bold' }}
                  >
                    {netProfit.toFixed(6)} ETH
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography color="textSecondary" variant="body2">
                    {formatDistanceToNow(opportunity.timestamp)} ago
                  </Typography>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default OpportunityList;