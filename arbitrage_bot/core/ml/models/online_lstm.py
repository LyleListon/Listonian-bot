"""Online LSTM model with continuous learning capabilities."""

import logging
import torch
import torch.nn as nn
import torch.optim as optim
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
from datetime import datetime
from collections import deque

class OnlineLSTM(nn.Module):
    """LSTM model with online learning capabilities."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize online LSTM model.
        
        Args:
            config: Configuration dictionary containing:
                - input_size: Number of input features
                - hidden_size: Size of LSTM hidden layers
                - num_layers: Number of LSTM layers
                - output_size: Number of outputs to predict
                - sequence_length: Length of input sequences
                - learning_rate: Learning rate for optimization
                - batch_size: Mini-batch size for updates
                - memory_size: Size of memory buffer
        """
        super().__init__()
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Model architecture
        self.lstm = nn.LSTM(
            input_size=config['input_size'],
            hidden_size=config['hidden_size'],
            num_layers=config['num_layers'],
            batch_first=True,
            dropout=config.get('dropout', 0.1)
        )
        
        # Output layers with skip connection
        self.fc1 = nn.Linear(config['hidden_size'], config['hidden_size'])
        self.fc2 = nn.Linear(config['hidden_size'], config['output_size'])
        self.skip = nn.Linear(config['input_size'], config['output_size'])
        
        # Activation functions
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(config.get('dropout', 0.1))
        
        # Initialize optimizer
        self.optimizer = optim.Adam(
            self.parameters(),
            lr=config['learning_rate'],
            weight_decay=config.get('weight_decay', 1e-5)
        )
        
        # Loss function with prediction interval
        self.loss_fn = nn.GaussianNLLLoss()
        
        # Memory buffer for experience replay
        self.memory = deque(maxlen=config['memory_size'])
        
        # Training statistics
        self.train_stats = {
            'losses': [],
            'predictions': [],
            'updates': 0,
            'last_update': None
        }
        
        # Initialize device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.to(self.device)
        
    def forward(
        self,
        x: torch.Tensor,
        hidden: Optional[Tuple[torch.Tensor, torch.Tensor]] = None
    ) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Forward pass through the model.
        
        Args:
            x: Input tensor of shape (batch_size, sequence_length, input_size)
            hidden: Optional initial hidden state
            
        Returns:
            Tuple of (predictions, hidden_state)
        """
        # LSTM layers
        lstm_out, hidden = self.lstm(x, hidden)
        
        # Get last sequence output
        last_output = lstm_out[:, -1, :]
        
        # Skip connection from input to output
        skip_out = self.skip(x[:, -1, :])
        
        # Dense layers
        fc1_out = self.relu(self.fc1(last_output))
        fc1_out = self.dropout(fc1_out)
        fc2_out = self.fc2(fc1_out)
        
        # Combine skip connection
        output = fc2_out + skip_out
        
        # Split output into prediction and uncertainty
        prediction, uncertainty = torch.chunk(output, 2, dim=1)
        uncertainty = torch.exp(uncertainty)  # Ensure positive uncertainty
        
        return torch.cat([prediction, uncertainty], dim=1), hidden
        
    def update(self, features: np.ndarray, target: np.ndarray):
        """
        Update model with new data point.
        
        Args:
            features: Input features of shape (sequence_length, input_size)
            target: Target value of shape (output_size,)
        """
        try:
            # Add to memory buffer
            self.memory.append((features, target))
            
            # Only update if we have enough samples
            if len(self.memory) < self.config['batch_size']:
                return
                
            # Sample mini-batch
            batch = self._sample_batch()
            
            # Convert to tensors
            x_batch = torch.FloatTensor(batch[0]).to(self.device)
            y_batch = torch.FloatTensor(batch[1]).to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            output, _ = self(x_batch)
            
            # Split predictions and uncertainties
            predictions, uncertainties = torch.chunk(output, 2, dim=1)
            
            # Compute loss
            loss = self.loss_fn(predictions, y_batch, uncertainties)
            
            # Backward pass
            loss.backward()
            
            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
            
            # Update weights
            self.optimizer.step()
            
            # Update statistics
            self.train_stats['losses'].append(loss.item())
            self.train_stats['predictions'].append(predictions.detach().cpu().numpy())
            self.train_stats['updates'] += 1
            self.train_stats['last_update'] = datetime.utcnow()
            
        except Exception as e:
            self.logger.error(f"Error updating model: {e}")
            
    def predict(
        self,
        features: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make prediction with uncertainty estimate.
        
        Args:
            features: Input features of shape (sequence_length, input_size)
            
        Returns:
            Tuple of (predictions, uncertainties)
        """
        try:
            self.eval()
            with torch.no_grad():
                # Convert to tensor
                x = torch.FloatTensor(features).unsqueeze(0).to(self.device)
                
                # Forward pass
                output, _ = self(x)
                
                # Split predictions and uncertainties
                predictions, uncertainties = torch.chunk(output, 2, dim=1)
                
                return (
                    predictions.cpu().numpy().squeeze(),
                    uncertainties.cpu().numpy().squeeze()
                )
                
        except Exception as e:
            self.logger.error(f"Error making prediction: {e}")
            return np.zeros(self.config['output_size']), np.ones(self.config['output_size'])
            
        finally:
            self.train()
            
    def _sample_batch(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Sample mini-batch from memory buffer.
        
        Returns:
            Tuple of (features_batch, targets_batch)
        """
        # Random sample
        indices = np.random.choice(
            len(self.memory),
            size=self.config['batch_size'],
            replace=False
        )
        
        # Split features and targets
        features = np.stack([self.memory[i][0] for i in indices])
        targets = np.stack([self.memory[i][1] for i in indices])
        
        return features, targets
        
    def get_training_stats(self) -> Dict[str, Any]:
        """
        Get training statistics.
        
        Returns:
            Dictionary of training statistics
        """
        return {
            'loss_mean': np.mean(self.train_stats['losses'][-100:]),
            'loss_std': np.std(self.train_stats['losses'][-100:]),
            'updates': self.train_stats['updates'],
            'last_update': self.train_stats['last_update'],
            'memory_size': len(self.memory),
            'prediction_std': np.std(self.train_stats['predictions'][-100:], axis=0)
        }