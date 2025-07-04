import React, { useState } from 'react';
import {
  Card,
  CardContent,
  Typography,
  Box,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  LinearProgress,
  Alert,
  SelectChangeEvent,
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { nflApi, apiUtils } from '../services/api';
import { Position, Week, ScoringFormat, MLProjectionsResponse } from '../types/nfl';

interface MLProjectionsProps {
  defaultPosition?: Position;
  defaultWeek?: Week;
  showControls?: boolean;
}

const MLProjections: React.FC<MLProjectionsProps> = ({
  defaultPosition = 'QB',
  defaultWeek = 1,
  showControls = true,
}) => {
  const [selectedPosition, setSelectedPosition] = useState<Position>(defaultPosition);
  const [selectedWeek, setSelectedWeek] = useState<Week>(defaultWeek);
  const [selectedScoring, setSelectedScoring] = useState<ScoringFormat>('half_ppr');

  // Get ML projections
  const { 
    data: projections, 
    isLoading, 
    error 
  } = useQuery<MLProjectionsResponse>({
    queryKey: ['mlProjections', selectedPosition, selectedWeek, selectedScoring],
    queryFn: () => nflApi.getMLProjections(selectedPosition, selectedWeek, selectedScoring, 10),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const handlePositionChange = (event: SelectChangeEvent<Position>) => {
    setSelectedPosition(event.target.value as Position);
  };

  const handleWeekChange = (event: SelectChangeEvent<Week>) => {
    setSelectedWeek(event.target.value as Week);
  };

  const handleScoringChange = (event: SelectChangeEvent<ScoringFormat>) => {
    setSelectedScoring(event.target.value as ScoringFormat);
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  const getInjuryStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'success';
      case 'questionable': return 'warning';
      case 'doubtful': return 'error';
      case 'out': return 'error';
      default: return 'default';
    }
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6" component="div">
            ML-Powered Projections
          </Typography>
          
          {showControls && (
            <Box sx={{ display: 'flex', gap: 2 }}>
              <FormControl size="small" sx={{ minWidth: 100 }}>
                <InputLabel>Position</InputLabel>
                <Select value={selectedPosition} label="Position" onChange={handlePositionChange}>
                  <MenuItem value="QB">QB</MenuItem>
                  <MenuItem value="RB">RB</MenuItem>
                  <MenuItem value="WR">WR</MenuItem>
                  <MenuItem value="TE">TE</MenuItem>
                </Select>
              </FormControl>
              
              <FormControl size="small" sx={{ minWidth: 100 }}>
                <InputLabel>Week</InputLabel>
                <Select value={selectedWeek} label="Week" onChange={handleWeekChange}>
                  {Array.from({ length: 18 }, (_, i) => i + 1).map(week => (
                    <MenuItem key={week} value={week as Week}>
                      {week}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Scoring</InputLabel>
                <Select value={selectedScoring} label="Scoring" onChange={handleScoringChange}>
                  <MenuItem value="standard">Standard</MenuItem>
                  <MenuItem value="half_ppr">Half PPR</MenuItem>
                  <MenuItem value="ppr">Full PPR</MenuItem>
                </Select>
              </FormControl>
            </Box>
          )}
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to load ML projections. Please try again.
          </Alert>
        )}

        {isLoading ? (
          <LinearProgress />
        ) : projections?.projections?.length ? (
          <>
            {/* Feature Importance */}
            <Box sx={{ mb: 3, p: 2, backgroundColor: 'grey.50', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Model Feature Importance
              </Typography>
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                {Object.entries(projections.metadata.feature_importance).map(([feature, importance]) => (
                  <Chip
                    key={feature}
                    label={`${feature.replace('_', ' ')}: ${Math.round(importance * 100)}%`}
                    size="small"
                    variant="outlined"
                  />
                ))}
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Model v{projections.projections[0]?.model_version} • Updated: {projections.metadata.model_updated_at}
              </Typography>
            </Box>

            {/* Projections Table */}
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Rank</TableCell>
                    <TableCell>Player</TableCell>
                    <TableCell>Team</TableCell>
                    <TableCell align="right">Projected Pts</TableCell>
                    <TableCell align="center">Confidence</TableCell>
                    <TableCell align="center">Health</TableCell>
                    <TableCell align="right">Recent Form</TableCell>
                    <TableCell align="right">Matchup</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {projections.projections.map((projection, index) => (
                    <TableRow key={projection.player_id} hover>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {index + 1}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {projection.player_name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {projection.team}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            fontWeight: 600,
                            color: apiUtils.getPositionColor(projection.position)
                          }}
                        >
                          {apiUtils.formatPoints(projection.predicted_points)}
                        </Typography>
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={`${Math.round(projection.confidence * 100)}%`}
                          size="small"
                          color={getConfidenceColor(projection.confidence)}
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Chip
                          label={projection.features.injury_status}
                          size="small"
                          color={getInjuryStatusColor(projection.features.injury_status)}
                          variant="filled"
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Typography 
                          variant="body2"
                          color={projection.features.recent_performance > 15 ? 'success.main' : 'text.secondary'}
                        >
                          {projection.features.recent_performance.toFixed(1)}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Typography 
                          variant="body2"
                          color={projection.features.matchup_difficulty < 0.5 ? 'success.main' : 'error.main'}
                        >
                          {projection.features.matchup_difficulty < 0.3 ? 'Easy' :
                           projection.features.matchup_difficulty < 0.7 ? 'Medium' : 'Hard'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        ) : (
          <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
            No ML projections available for the selected criteria.
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default MLProjections;