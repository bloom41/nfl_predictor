import React, { useState } from 'react';
import {
  Container,
  Typography,
  Box,
  Tabs,
  Tab,
  Paper,
} from '@mui/material';
import {
  Psychology,
  LocalHospital,
  TrendingUp,
  Sports,
} from '@mui/icons-material';
import MLProjections from '../components/MLProjections';
import MatchupAnalysis from '../components/MatchupAnalysis';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`analysis-tabpanel-${index}`}
      aria-labelledby={`analysis-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ py: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `analysis-tab-${index}`,
    'aria-controls': `analysis-tabpanel-${index}`,
  };
}

const Analysis: React.FC = () => {
  const [value, setValue] = useState(0);

  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    setValue(newValue);
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ mb: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
          Advanced NFL Analysis
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          Machine learning predictions, matchup insights, and advanced analytics
        </Typography>
      </Box>

      <Paper sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={value} onChange={handleChange} aria-label="analysis tabs">
            <Tab 
              icon={<Psychology />} 
              label="ML Projections" 
              iconPosition="start"
              {...a11yProps(0)} 
            />
            <Tab 
              icon={<Sports />} 
              label="Matchup Analysis" 
              iconPosition="start"
              {...a11yProps(1)} 
            />
            <Tab 
              icon={<LocalHospital />} 
              label="Injury Analysis" 
              iconPosition="start"
              {...a11yProps(2)} 
            />
            <Tab 
              icon={<TrendingUp />} 
              label="Boom/Bust Analysis" 
              iconPosition="start"
              {...a11yProps(3)} 
            />
          </Tabs>
        </Box>

        <TabPanel value={value} index={0}>
          <MLProjections />
        </TabPanel>
        
        <TabPanel value={value} index={1}>
          <MatchupAnalysis />
        </TabPanel>
        
        <TabPanel value={value} index={2}>
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <LocalHospital sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Injury Analysis
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Real-time injury monitoring and impact assessment coming soon.
            </Typography>
          </Box>
        </TabPanel>
        
        <TabPanel value={value} index={3}>
          <Box sx={{ textAlign: 'center', py: 8 }}>
            <TrendingUp sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" gutterBottom>
              Boom/Bust Analysis
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Volatility modeling and risk assessment for player projections.
            </Typography>
          </Box>
        </TabPanel>
      </Paper>
    </Container>
  );
};

export default Analysis;