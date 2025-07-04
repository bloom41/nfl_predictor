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
  Grid,
  Chip,
  LinearProgress,
  Alert,
  SelectChangeEvent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import {
  ExpandMore,
  WbSunny,
  Air,
  Speed,
  TrendingUp,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { nflApi } from '../services/api';
import { Week, MatchupAnalysisResponse } from '../types/nfl';

interface MatchupAnalysisProps {
  defaultWeek?: Week;
  showControls?: boolean;
}

const MatchupAnalysis: React.FC<MatchupAnalysisProps> = ({
  defaultWeek = 1,
  showControls = true,
}) => {
  const [selectedWeek, setSelectedWeek] = useState<Week>(defaultWeek);

  // Get matchup analysis
  const { 
    data: matchups, 
    isLoading, 
    error 
  } = useQuery<MatchupAnalysisResponse>({
    queryKey: ['matchupAnalysis', selectedWeek],
    queryFn: () => nflApi.getMatchupAnalysis(selectedWeek),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });

  const handleWeekChange = (event: SelectChangeEvent<Week>) => {
    setSelectedWeek(event.target.value as Week);
  };

  const getWeatherImpactColor = (impact: string) => {
    switch (impact.toLowerCase()) {
      case 'minimal': return 'success';
      case 'moderate': return 'warning';
      case 'significant': return 'error';
      default: return 'default';
    }
  };

  const getPaceRatingColor = (rating: string) => {
    switch (rating.toLowerCase()) {
      case 'fast': return 'success';
      case 'average': return 'default';
      case 'slow': return 'warning';
      default: return 'default';
    }
  };

  const getScoringEnvironmentColor = (rating: string) => {
    switch (rating.toLowerCase()) {
      case 'high': return 'success';
      case 'moderate': return 'warning';
      case 'low': return 'error';
      default: return 'default';
    }
  };

  const formatTemperature = (temp: number) => `${temp}°F`;
  const formatWindSpeed = (speed: number) => `${speed} mph`;

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h6" component="div">
            Weekly Matchup Analysis
          </Typography>
          
          {showControls && (
            <FormControl size="small" sx={{ minWidth: 100 }}>
              <InputLabel>Week</InputLabel>
              <Select value={selectedWeek} label="Week" onChange={handleWeekChange}>
                {Array.from({ length: 18 }, (_, i) => i + 1).map(week => (
                  <MenuItem key={week} value={week as Week}>
                    Week {week}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to load matchup analysis. Please try again.
          </Alert>
        )}

        {isLoading ? (
          <LinearProgress />
        ) : matchups?.matchups?.length ? (
          <>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              {matchups.matchups.length} games analyzed for Week {selectedWeek}
            </Typography>

            <Box sx={{ mt: 2 }}>
              {matchups.matchups.map((matchup, index) => (
                <Accordion key={index}>
                  <AccordionSummary expandIcon={<ExpandMore />}>
                    <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600, flexGrow: 1 }}>
                        {matchup.away_team} @ {matchup.home_team}
                      </Typography>
                      
                      <Box sx={{ display: 'flex', gap: 1, mr: 2 }}>
                        <Chip
                          size="small"
                          label={matchup.analysis.scoring_environment.environment_rating}
                          color={getScoringEnvironmentColor(matchup.analysis.scoring_environment.environment_rating)}
                          variant="outlined"
                        />
                        <Chip
                          size="small"
                          label={matchup.analysis.weather_impact}
                          color={getWeatherImpactColor(matchup.analysis.weather_impact)}
                          variant="outlined"
                        />
                      </Box>
                      
                      <Typography variant="body2" color="text.secondary">
                        {matchup.game_info.kickoff_time}
                      </Typography>
                    </Box>
                  </AccordionSummary>
                  
                  <AccordionDetails>
                    <Grid container spacing={3}>
                      {/* Game Info */}
                      <Grid xs={12} md={6}>
                        <Typography variant="subtitle2" gutterBottom>
                          Game Information
                        </Typography>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2">Vegas Line:</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {matchup.home_team} {matchup.game_info.vegas_line > 0 ? '+' : ''}{matchup.game_info.vegas_line.toFixed(1)}
                            </Typography>
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2">Total Points:</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {matchup.analysis.scoring_environment.total_points_projection}
                            </Typography>
                          </Box>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Typography variant="body2">Expected Plays:</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {matchup.analysis.pace_analysis.expected_plays}
                            </Typography>
                          </Box>
                        </Box>
                      </Grid>

                      {/* Weather */}
                      <Grid xs={12} md={6}>
                        <Typography variant="subtitle2" gutterBottom>
                          Weather Conditions
                        </Typography>
                        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <WbSunny fontSize="small" color="action" />
                            <Typography variant="body2">
                              {formatTemperature(matchup.game_info.weather_conditions.temperature)}
                            </Typography>
                          </Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Air fontSize="small" color="action" />
                            <Typography variant="body2">
                              {formatWindSpeed(matchup.game_info.weather_conditions.wind_speed)} wind
                            </Typography>
                          </Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body2">
                              {matchup.game_info.weather_conditions.dome_game ? 'Dome Game' : 'Outdoor Game'}
                            </Typography>
                          </Box>
                          {matchup.game_info.weather_conditions.precipitation !== 'none' && (
                            <Typography variant="body2" color="warning.main">
                              Precipitation: {matchup.game_info.weather_conditions.precipitation}
                            </Typography>
                          )}
                        </Box>
                      </Grid>

                      {/* Analysis Tags */}
                      <Grid xs={12} md={6}>
                        <Typography variant="subtitle2" gutterBottom>
                          Game Analysis
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                          <Chip
                            size="small"
                            icon={<Speed />}
                            label={`${matchup.analysis.pace_analysis.pace_rating} pace`}
                            color={getPaceRatingColor(matchup.analysis.pace_analysis.pace_rating)}
                            variant="outlined"
                          />
                          <Chip
                            size="small"
                            icon={<TrendingUp />}
                            label={`${matchup.analysis.scoring_environment.environment_rating} scoring`}
                            color={getScoringEnvironmentColor(matchup.analysis.scoring_environment.environment_rating)}
                            variant="outlined"
                          />
                        </Box>
                      </Grid>

                      {/* Key Factors */}
                      <Grid xs={12} md={6}>
                        <Typography variant="subtitle2" gutterBottom>
                          Key Fantasy Factors
                        </Typography>
                        <List dense>
                          {matchup.analysis.key_factors.slice(0, 4).map((factor, factorIndex) => (
                            <ListItem key={factorIndex} sx={{ py: 0.5, px: 0 }}>
                              <ListItemText 
                                primary={factor}
                                primaryTypographyProps={{ variant: 'body2' }}
                              />
                            </ListItem>
                          ))}
                        </List>
                      </Grid>
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              ))}
            </Box>
          </>
        ) : (
          <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
            No matchup analysis available for Week {selectedWeek}.
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default MatchupAnalysis;