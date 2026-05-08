import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Button,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  AppBar,
  Toolbar,
  Paper
} from '@mui/material';
import { Refresh, Analytics, Compare } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import CompanySelector from '../CompanySelector/CompanySelector.jsx';
import InsightsChart from '../InsightsChart/InsightsChart.jsx';
import StudyPlan from '../StudyPlan/StudyPlan.jsx';
import ExperiencesList from '../ExperiencesList/ExperiencesList.jsx';
import { interviewAPI } from '../../services/api.js';

const Dashboard = ({ onNotification }) => {
  // Persist company selection across page refreshes
  const [selectedCompanies, setSelectedCompanies] = useState(() => {
    try {
      const stored = localStorage.getItem('selectedCompanies');
      return stored ? JSON.parse(stored) : [];
    } catch { return []; }
  });
  const [insights, setInsights] = useState({});
  const [loading, setLoading] = useState(false);
  const [analysisLoading, setAnalysisLoading] = useState({});
  const [companiesData, setCompaniesData] = useState([]);
  const navigate = useNavigate();

  // Persist selection to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('selectedCompanies', JSON.stringify(selectedCompanies));
  }, [selectedCompanies]);

  // Fetch companies list once on mount so we know which have data
  useEffect(() => {
    interviewAPI.getCompanies()
      .then(res => setCompaniesData(res.data.companies || []))
      .catch(() => {});
  }, []);

  // Auto-load insights when companies are selected — on mount this reloads persisted selections.
  // An empty selection naturally returns early (no API call on a blank slate).
  useEffect(() => {
    if (selectedCompanies.length === 0) return;
    loadInsights(selectedCompanies);
  }, [selectedCompanies]);

  // Remove insights for companies that have been deselected
  useEffect(() => {
    setInsights(prev => {
      const active = new Set(selectedCompanies);
      const pruned = Object.fromEntries(
        Object.entries(prev).filter(([key]) => active.has(key))
      );
      return Object.keys(pruned).length === Object.keys(prev).length ? prev : pruned;
    });
  }, [selectedCompanies]);

  const loadInsights = async (companiesToLoad = selectedCompanies) => {
    setLoading(true);
    try {
      // Re-fetch companies list so we have fresh experience counts
      // Map: lowercase name → { canonicalName, hasData } for case-insensitive lookup
      let companyMap = new Map(); // 'tcs' → 'TCS' (canonical name from DB)
      let hasDataSet = new Set(); // lowercase names that have experiences
      try {
        const res = await interviewAPI.getCompanies();
        const list = res.data.companies || [];
        setCompaniesData(list);
        list.forEach(c => {
          companyMap.set(c.name.toLowerCase(), c.name);
          if (c.experience_count > 0) hasDataSet.add(c.name.toLowerCase());
        });
      } catch (_) { /* non-fatal — fall through and call insights anyway */ }

      // Collect results for just the requested companies (functional update preserves the rest)
      const fetched = {};
      for (const company of companiesToLoad) {
        const lc = company.toLowerCase();
        // Resolve to the canonical DB name (handles TCS vs tcs vs Tcs)
        const canonicalName = companyMap.get(lc) || company;

        // Skip the ML call for companies with no experiences OR not in DB at all.
        // companyMap.has(lc): company is known to the DB
        // hasDataSet.has(lc): company has at least one scraped experience
        if (companyMap.size > 0 && (!companyMap.has(lc) || !hasDataSet.has(lc))) {
          fetched[company] = { status: 'no_data', company };
          continue;
        }
        try {
          const response = await interviewAPI.getCompanyInsights(canonicalName);
          fetched[company] = response.data;
        } catch (error) {
          console.error(`Error loading insights for ${company}:`, error);
          onNotification(`Failed to load insights for ${company}. Try running analysis first.`, 'warning');
        }
      }

      setInsights(prev => ({ ...prev, ...fetched }));
    } finally {
      setLoading(false);
    }
  };

  const triggerAnalysis = async (company) => {
    setAnalysisLoading(prev => ({ ...prev, [company]: true }));
    onNotification(`Scraping started for ${company}. This may take 1–2 minutes…`, 'info');

    try {
      // Start the background job
      const startRes = await interviewAPI.triggerAnalysis(company, {
        max_experiences: 20,
        force_refresh: false
      });

      const jobId = startRes.data.job_id;
      if (!jobId) throw new Error('No job ID returned from server');

      // Poll every 6 seconds until done or failed
      await new Promise((resolve, reject) => {
        const maxWaitMs = 5 * 60 * 1000; // 5 minutes
        const startedAt = Date.now();
        const interval = setInterval(async () => {
          if (Date.now() - startedAt > maxWaitMs) {
            clearInterval(interval);
            reject(new Error('Analysis timed out after 5 minutes'));
            return;
          }
          try {
            const poll = await interviewAPI.getJobStatus(jobId);
            const { status, result, error } = poll.data;

            if (status === 'completed') {
              clearInterval(interval);
              const total = result?.data_collection?.total_experiences || 0;
              const scraped = result?.data_collection?.newly_scraped || 0;
              if (total === 0) {
                onNotification(
                  `No interview experiences found for ${company}. The company may not have public data on supported platforms yet.`,
                  'warning'
                );
              } else {
                onNotification(
                  `Analysis done for ${company}! ${scraped} new experiences scraped (${total} total).`,
                  'success'
                );
              }
              // Use the same key as in selectedCompanies so insights[company] is found on render.
              // loadInsights() resolves the canonical DB name internally via companyMap.
              setTimeout(() => loadInsights([company]), 800);
              resolve();
            } else if (status === 'failed') {
              clearInterval(interval);
              reject(new Error(error || 'Pipeline failed'));
            }
            // status === 'running' or 'queued' → keep polling
          } catch (pollErr) {
            // 404 can happen transiently; keep polling unless it's a hard failure
            const is404 = pollErr?.response?.status === 404;
            if (!is404) {
              clearInterval(interval);
              reject(pollErr);
            }
          }
        }, 6000);
      });

    } catch (error) {
      console.error(`Analysis error for ${company}:`, error);
      onNotification(`Analysis failed for ${company}: ${error.message}`, 'error');
    } finally {
      setAnalysisLoading(prev => ({ ...prev, [company]: false }));
    }
  };

  const getInsightsSummary = (companyInsights) => {
    if (!companyInsights.insights) return null;
    
    const topicEntries = Object.entries(companyInsights.insights);
    const topTopics = topicEntries.slice(0, 3).map(([key, data]) => data.topic_name);
    const highPriority = topicEntries.filter(([_, data]) => data.priority_level?.toUpperCase() === 'HIGH').length;
    const sampleSize = companyInsights.analysis_metadata?.sample_size || 0;
    
    return { topTopics, highPriority, sampleSize };
  };

  return (
    <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Navigation Bar */}
      <AppBar position="static" elevation={1} sx={{ bgcolor: 'primary.main' }}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Interview Intelligence System
          </Typography>
          <Button 
            color="inherit" 
            onClick={() => navigate('/compare')}
            startIcon={<Compare />}
          >
            Compare Companies
          </Button>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth="xl" sx={{ py: 4 }}>
        {/* Header Section */}
        <Paper elevation={0} sx={{ p: 3, mb: 4, bgcolor: 'transparent' }}>
          <Typography variant="h4" component="h1" gutterBottom align="center">
            Interview Intelligence Dashboard
          </Typography>
          <Typography variant="subtitle1" color="textSecondary" align="center">
            Data-driven interview preparation insights powered by AI analysis
          </Typography>
        </Paper>

        {/* Company Selection */}
        <Card sx={{ mb: 4 }} elevation={2}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Select Companies to Analyze
            </Typography>
            <CompanySelector
              selectedCompanies={selectedCompanies}
              onSelectionChange={setSelectedCompanies}
              maxSelection={3}
            />
          </CardContent>
        </Card>

        {loading && (
          <Box display="flex" justifyContent="center" alignItems="center" my={6}>
            <CircularProgress size={40} />
            <Typography variant="h6" sx={{ ml: 2 }}>
              Loading insights...
            </Typography>
          </Box>
        )}

        {/* Company Insights Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          {selectedCompanies.map((company) => {
            const companyInsights = insights[company];
            const summary = companyInsights ? getInsightsSummary(companyInsights) : null;
            
            return (
              <Grid item xs={12} sm={6} md={4} key={company}>
                <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }} elevation={2}>
                  <CardContent sx={{ flexGrow: 1, p: 3 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                      <Typography variant="h6">{company}</Typography>
                      {summary && (
                        <Chip 
                          label={`${summary.sampleSize} experiences`} 
                          size="small" 
                          color="primary"
                        />
                      )}
                    </Box>
                    
                    {summary ? (
                      <Box>
                        <Typography variant="body2" color="textSecondary" gutterBottom>
                          High Priority Topics: {summary.highPriority}
                        </Typography>

                        <Typography variant="body2" gutterBottom sx={{ mt: 2 }}>
                          Top Focus Areas:
                        </Typography>
                        <Box>
                          {summary.topTopics.map((topic, index) => (
                            <Chip
                              key={index}
                              label={topic}
                              size="small"
                              variant="outlined"
                              sx={{ mr: 1, mb: 1 }}
                            />
                          ))}
                        </Box>
                      </Box>
                    ) : (
                      <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
                        No data yet. Click <strong>Run Analysis</strong> to collect interview experiences.
                      </Typography>
                    )}
                  </CardContent>
                  
                  <CardActions sx={{ p: 2, pt: 0 }}>
                    <Button
                      size="small"
                      fullWidth
                      variant="contained"
                      startIcon={analysisLoading[company] ? <CircularProgress size={16} /> : <Analytics />}
                      onClick={() => triggerAnalysis(company)}
                      disabled={analysisLoading[company]}
                    >
                      {analysisLoading[company] ? 'Analyzing...' : (summary ? 'Update Data' : 'Run Analysis')}
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            );
          })}
        </Grid>

        {/* Detailed Insights — only for companies with real live data */}
        {Object.keys(insights).length > 0 && (
          <Grid container spacing={4}>
            {Object.entries(insights).map(([company, companyInsights]) => {
              if (companyInsights?.status !== 'live_data') return null;
              return (
              <Grid item xs={12} key={company}>
                <Card elevation={2}>
                  <CardContent sx={{ p: 4 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
                      <Typography variant="h5">{company} Detailed Analysis</Typography>
                      <Button
                        variant="outlined"
                        startIcon={<Refresh />}
                        onClick={loadInsights}
                        disabled={loading}
                      >
                        Refresh Data
                      </Button>
                    </Box>
                    
                    <Box mb={4}>
                      <InsightsChart 
                        insights={companyInsights}
                        title={`${company} Topic Analysis`}
                      />
                    </Box>
                    
                    <StudyPlan insights={companyInsights} company={company} />

                    {/* Interview Experiences Section */}
                    <Box mt={4}>
                      <ExperiencesList company={company} onNotification={onNotification} />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
              );
            })}
          </Grid>
        )}
      </Container>
    </Box>
  );
};

export default Dashboard;