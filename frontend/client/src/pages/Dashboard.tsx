import React, { useState } from 'react';
import {
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Box,
  Button,
  Chip,
  LinearProgress,
  Alert,
  useTheme,
  alpha,
  CardActions,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  SelectChangeEvent,
} from '@mui/material';
import {
  TrendingUp,
  Speed,
  Assessment,
  Refresh,
  EmojiEvents,
  Person,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { nflApi, apiUtils } from '../services/api';
import { ScoringFormat, Week, Position } from '../types/nfl';

const Dashboard: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const [selectedWeek, setSelectedWeek] = useState<Week>(1);
  const [selectedScoring, setSelectedScoring] = useState<ScoringFormat>('half_ppr');

  // Get system status
  const { data: systemStatus, error: statusError } = useQuery({
    queryKey: ['systemStatus'],
    queryFn: () => nflApi.healthCheck(),
    refetchInterval: 30000,
  });

  // Get API features
  const { data: apiFeatures } = useQuery({
    queryKey: ['apiFeatures'],
    queryFn: () => nflApi.getFeatures(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  // Get overview rankings for all positions
  const { data: overviewRankings, isLoading: rankingsLoading, error: rankingsError, refetch } = useQuery({
    queryKey: ['overviewRankings', selectedWeek, selectedScoring],
    queryFn: () => nflApi.getAllPositionRankings(selectedWeek, selectedScoring, 5),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const handleWeekChange = (event: SelectChangeEvent<Week>) => {
    setSelectedWeek(event.target.value as Week);
  };

  const handleScoringChange = (event: SelectChangeEvent<ScoringFormat>) => {
    setSelectedScoring(event.target.value as ScoringFormat);
  };

  const getEliteFeaturesCount = () => {
    if (!apiFeatures?.capabilities) return 0;
    return Object.values(apiFeatures.capabilities).filter((cap: any) => cap.enabled).length;
  };

  const getPositionRankings = (position: string) => {
    return overviewRankings?.rankings?.[position.toLowerCase()] || [];
  };

  const StatusCard: React.FC<{ title: string; status: string; color: string; icon: React.ReactNode }> = ({
    title,
    status,
    color,
    icon,
  }) => (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Box sx={{ color, mr: 1 }}>{icon}</Box>
          <Typography variant="h6" component="div">
            {title}
          </Typography>
        </Box>
        <Typography variant="h4" sx={{ color, fontWeight: 700 }}>
          {status}
        </Typography>
      </CardContent>
    </Card>
  );

  const PositionCard: React.FC<{ position: Position }> = ({ position }) => {
    const rankings = getPositionRankings(position);
    const positionColor = apiUtils.getPositionColor(position);

    return (
      <Card sx={{ height: '100%' }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6" component="div">
              Top {position}s
            </Typography>
            <Chip 
              label={position} 
              sx={{ 
                backgroundColor: alpha(positionColor, 0.2),
                color: positionColor,
                fontWeight: 600,
              }}
            />
          </Box>
          
          {rankingsLoading ? (
            <LinearProgress />
          ) : rankings.length > 0 ? (
            <Box>
              {rankings.slice(0, 3).map((ranking, index) => (
                <Box
                  key={ranking.player.id}
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    py: 1,
                    borderBottom: index < 2 ? `1px solid ${alpha(theme.palette.divider, 0.1)}` : 'none',
                    cursor: 'pointer',
                    '&:hover': {
                      backgroundColor: alpha(positionColor, 0.05),
                    },
                  }}
                  onClick={() => navigate(`/player/${ranking.player.id}`)}
                >
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      {index + 1}. {ranking.player.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {ranking.player.team}
                    </Typography>
                  </Box>
                  <Box sx={{ textAlign: 'right' }}>
                    <Typography variant="subtitle2" sx={{ color: positionColor, fontWeight: 600 }}>
                      {apiUtils.formatPoints(ranking.predictedPoints)}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {Math.round(ranking.confidence * 100)}% conf
                    </Typography>
                  </Box>
                </Box>
              ))}
            </Box>
          ) : (
            <Typography color="text.secondary">No data available</Typography>
          )}
        </CardContent>
        <CardActions>
          <Button 
            size="small" 
            onClick={() => navigate(`/rankings/${position.toLowerCase()}`)}
            sx={{ color: positionColor }}
          >
            View All {position}s
          </Button>
        </CardActions>
      </Card>
    );
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
          NFL Elite Assistant Dashboard
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" gutterBottom>
          Advanced AI-powered fantasy football predictions with real-time data
        </Typography>
        
        {/* Controls */}
        <Box sx={{ display: 'flex', gap: 2, mt: 3, mb: 3 }}>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Week</InputLabel>
            <Select value={selectedWeek} label="Week" onChange={handleWeekChange}>
              {Array.from({ length: 18 }, (_, i) => i + 1).map(week => (
                <MenuItem key={week} value={week as Week}>
                  Week {week}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel>Scoring</InputLabel>
            <Select value={selectedScoring} label="Scoring" onChange={handleScoringChange}>
              <MenuItem value="standard">Standard</MenuItem>
              <MenuItem value="half_ppr">Half PPR</MenuItem>
              <MenuItem value="ppr">Full PPR</MenuItem>
            </Select>
          </FormControl>

          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={() => refetch()}
            disabled={rankingsLoading}
          >
            Refresh Data
          </Button>
        </Box>
      </Box>

      {/* Error Display */}
      {(statusError || rankingsError) && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {statusError && 'Failed to load system status. '}
          {rankingsError && 'Failed to load rankings data. '}
          Please check your connection and try again.
        </Alert>
      )}

      {/* System Status Overview */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mb: 4 }}>
        <Box sx={{ flex: '1 1 250px', minWidth: '250px' }}>
          <StatusCard
            title="System Status"
            status={systemStatus?.status || 'Unknown'}
            color={
              systemStatus?.status === 'healthy'
                ? theme.palette.success.main
                : systemStatus?.status === 'degraded'
                ? theme.palette.warning.main
                : theme.palette.error.main
            }
            icon={<Speed />}
          />
        </Box>
        
        <Box sx={{ flex: '1 1 250px', minWidth: '250px' }}>
          <StatusCard
            title="Analysis Features"
            status={`${getEliteFeaturesCount()}/7 Active`}
            color={theme.palette.secondary.main}
            icon={<TrendingUp />}
          />
        </Box>
        
        <Box sx={{ flex: '1 1 250px', minWidth: '250px' }}>
          <StatusCard
            title="API Version"
            status={(systemStatus as any)?.version || 'Unknown'}
            color={theme.palette.primary.main}
            icon={<Person />}
          />
        </Box>
        
        <Box sx={{ flex: '1 1 250px', minWidth: '250px' }}>
          <StatusCard
            title="ML Models"
            status={(systemStatus as any)?.mlService?.available ? 'Active' : 'Inactive'}
            color={(systemStatus as any)?.mlService?.available ? theme.palette.success.main : theme.palette.error.main}
            icon={<Assessment />}
          />
        </Box>
      </Box>

      {/* Position Rankings Overview */}
      <Typography variant="h5" component="h2" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
        Week {selectedWeek} Top Players ({apiUtils.getScoringDisplayName(selectedScoring)})
      </Typography>
      
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mb: 4 }}>
        {(['QB', 'RB', 'WR', 'TE'] as Position[]).map(position => (
          <Box key={position} sx={{ flex: '1 1 280px', minWidth: '280px' }}>
            <PositionCard position={position} />
          </Box>
        ))}
      </Box>

      {/* Quick Actions */}
      <Card>
        <CardContent>
          <Typography variant="h6" component="div" gutterBottom>
            Quick Actions
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Button
              variant="contained"
              startIcon={<EmojiEvents />}
              onClick={() => navigate('/rankings')}
            >
              View All Rankings
            </Button>
            <Button
              variant="outlined"
              startIcon={<Person />}
              onClick={() => navigate('/player/search')}
            >
              Search Players
            </Button>
            <Button
              variant="outlined"
              startIcon={<Assessment />}
              onClick={() => navigate('/status')}
            >
              System Details
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Container>
  );
};

export default Dashboard;