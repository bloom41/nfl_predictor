import React from 'react';
import {
  Container,
  Typography,
  Box,
  Card,
  CardContent,
  Grid,
  Chip,
  LinearProgress,
  Alert,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { nflApi } from '../services/api';

const SystemStatus: React.FC = () => {
  const { data: systemStatus, isLoading, error } = useQuery({
    queryKey: ['systemStatus'],
    queryFn: () => nflApi.getSystemStatus(),
    refetchInterval: 10000, // Refetch every 10 seconds
  });

  const getStatusColor = (status: string | boolean) => {
    switch (status) {
      case 'operational':
      case 'active':
      case true:
        return 'success';
      case 'degraded':
        return 'warning';
      case 'down':
      case false:
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
          System Status
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Real-time monitoring of NFL Assistant services and components
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load system status. Please check your connection and try again.
        </Alert>
      )}

      {isLoading && <LinearProgress sx={{ mb: 3 }} />}

      {systemStatus && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* Overall Status */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Overall System Status
              </Typography>
              <Chip
                label={systemStatus.status}
                color={getStatusColor(systemStatus.status)}
                size="medium"
                sx={{ fontWeight: 600 }}
              />
            </CardContent>
          </Card>

          {/* Services Status */}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            {/* Express Server Status */}
            <Box sx={{ flex: '1 1 400px', minWidth: '400px' }}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Express API Server
                  </Typography>
                  <Box sx={{ mb: 2 }}>
                    <Chip
                      label={systemStatus.services.express.status}
                      color={getStatusColor(systemStatus.services.express.status)}
                      sx={{ mr: 1 }}
                    />
                    <Typography variant="body2" color="text.secondary">
                      Version: {systemStatus.services.express.version}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Uptime: {Math.round(systemStatus.services.express.uptime)} seconds
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Box>

            {/* Django Backend Status */}
            <Box sx={{ flex: '1 1 400px', minWidth: '400px' }}>
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Django Backend
                  </Typography>
                  <Box sx={{ mb: 2 }}>
                    <Chip
                      label={systemStatus.services.django.status}
                      color={getStatusColor(systemStatus.services.django.status)}
                      sx={{ mr: 1, mb: 1 }}
                    />
                    <Chip
                      label={`DB: ${systemStatus.services.django.database_status}`}
                      color={getStatusColor(systemStatus.services.django.database_status)}
                      sx={{ mb: 1 }}
                    />
                    <Typography variant="body2" color="text.secondary">
                      Players: {systemStatus.services.django.player_count?.toLocaleString()}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Last Update: {systemStatus.services.django.last_update}
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Box>
          </Box>

          {/* Elite Features Status */}
          {systemStatus.services.django.elite_features && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Elite Features Status
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {Object.entries(systemStatus.services.django.elite_features).map(([feature, status]) => (
                    <Chip
                      key={feature}
                      label={feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      color={getStatusColor(status as string | boolean)}
                      variant="outlined"
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          )}

          {/* Performance Metrics */}
          {systemStatus.performance_metrics && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Performance Metrics
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                  <Box sx={{ flex: '1 1 150px', minWidth: '150px' }}>
                    <Typography variant="subtitle2">Response Time</Typography>
                    <Typography variant="h6" color="primary">
                      {systemStatus.performance_metrics.response_time}ms
                    </Typography>
                  </Box>
                  <Box sx={{ flex: '1 1 150px', minWidth: '150px' }}>
                    <Typography variant="subtitle2">Error Rate</Typography>
                    <Typography variant="h6" color={systemStatus.performance_metrics.error_rate > 0.05 ? 'error' : 'success'}>
                      {(systemStatus.performance_metrics.error_rate * 100).toFixed(2)}%
                    </Typography>
                  </Box>
                  <Box sx={{ flex: '1 1 150px', minWidth: '150px' }}>
                    <Typography variant="subtitle2">Throughput</Typography>
                    <Typography variant="h6" color="info">
                      {systemStatus.performance_metrics.throughput} req/min
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          )}
        </Box>
      )}
    </Container>
  );
};

export default SystemStatus;