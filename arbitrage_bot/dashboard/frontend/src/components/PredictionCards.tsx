import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  LinearProgress,
  useTheme,
} from '@mui/material';
import { useWebSocket } from '../providers/WebSocketProvider';
import { PredictionsMessage } from '../types/websocket';
import { formatDistanceToNow } from 'date-fns';

const PredictionCards: React.FC = () => {
  const theme = useTheme();
  const { lastMessage, lastUpdate } = useWebSocket();

  // Cast lastMessage to PredictionsMessage if it's a predictions type
  const predictionsData = lastMessage?.type === 'predictions' 
    ? (lastMessage as PredictionsMessage).predictions 
    : [];

  const formatPrediction = (value: number) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return theme.palette.success.main;
    if (confidence >= 0.6) return theme.palette.warning.main;
    return theme.palette.error.main;
  };

  const renderPredictionCard = (
    title: string,
    value: string,
    confidence: number,
    timestamp: number
  ) => (
    <Card
      sx={{
        height: '100%',
        backgroundColor: 'rgba(0, 0, 0, 0.1)',
        backdropFilter: 'blur(4px)',
      }}
    >
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <Typography variant="h4" sx={{ mb: 2 }}>
          {value}
        </Typography>
        <Box sx={{ mb: 1 }}>
          <Typography variant="body2" color="textSecondary">
            Confidence
          </Typography>
          <LinearProgress
            variant="determinate"
            value={confidence * 100}
            sx={{
              height: 8,
              borderRadius: 4,
              backgroundColor: theme.palette.grey[800],
              '& .MuiLinearProgress-bar': {
                backgroundColor: getConfidenceColor(confidence),
              },
            }}
          />
        </Box>
        <Typography variant="caption" color="textSecondary">
          Updated {formatDistanceToNow(timestamp)} ago
        </Typography>
      </CardContent>
    </Card>
  );

  if (!predictionsData.length) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography color="textSecondary">
          Waiting for prediction data...
        </Typography>
      </Box>
    );
  }

  return (
    <Grid container spacing={3}>
      {predictionsData.map((prediction, index) => (
        <Grid item xs={12} sm={6} md={4} key={index}>
          {renderPredictionCard(
            'Gas Price Prediction',
            `${prediction.gasPrice} gwei`,
            prediction.confidence,
            prediction.timestamp
          )}
        </Grid>
      ))}
    </Grid>
  );
};

export default PredictionCards;