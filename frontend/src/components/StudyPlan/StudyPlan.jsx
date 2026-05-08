import React, { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
  Alert,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem
} from '@mui/material';
import {
  CheckCircleOutline,
  RadioButtonUnchecked,
  ExpandMore,
  Timer,
  TrendingUp,
  School,
  Assignment,
  Download,
  Schedule,
  Analytics,
  Fingerprint,
  Psychology,
} from '@mui/icons-material';

/** Small badge showing how consistently a topic appears across experiences */
const SpecificityBadge = ({ score }) => {
  if (score == null) return null;
  const pct = Math.round(score * 100);
  const [label, color] =
    score >= 0.7 ? ['Very consistent', 'secondary'] :
    score >= 0.4 ? ['Fairly consistent', 'info'] :
                   ['Occasional', 'default'];
  return (
    <Chip
      icon={<Fingerprint sx={{ fontSize: 14 }} />}
      label={`${label} ${pct}%`}
      size="small"
      color={color}
      variant="outlined"
      sx={{ fontSize: '0.68rem', height: 22 }}
    />
  );
};

/** Tiny indicator when sentence-transformer semantic confidence is available */
const SemanticBadge = ({ score }) => {
  if (score == null) return null;
  return (
    <Chip
      icon={<Psychology sx={{ fontSize: 14 }} />}
      label={`AI conf ${score}`}
      size="small"
      variant="outlined"
      sx={{ fontSize: '0.68rem', height: 22, color: 'text.secondary' }}
    />
  );
};

const StudyPlan = ({ insights, company }) => {
  const [completedTopics, setCompletedTopics] = useState(new Set());
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [practiceDialogOpen, setPracticeDialogOpen] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({
    duration: '4',
    hoursPerDay: '2',
    startDate: new Date().toISOString().split('T')[0]
  });

  if (!insights || !insights.insights) {
    return (
      <Alert severity="info">
        No study plan available. Run analysis to generate personalized recommendations.
      </Alert>
    );
  }

  const { insights: topicInsights, analysis_metadata } = insights;
  const topicEntries = Object.entries(topicInsights);
  
  // Separate topics by priority
  const highPriorityTopics = topicEntries.filter(([_, data]) => 
    data.priority_level?.toUpperCase() === 'HIGH'
  );
  const mediumPriorityTopics = topicEntries.filter(([_, data]) => 
    data.priority_level?.toUpperCase() === 'MEDIUM'
  );
  const lowPriorityTopics = topicEntries.filter(([_, data]) => 
    data.priority_level?.toUpperCase() === 'LOW'
  );

  const toggleTopicCompletion = (topicKey) => {
    const newCompleted = new Set(completedTopics);
    if (newCompleted.has(topicKey)) {
      newCompleted.delete(topicKey);
    } else {
      newCompleted.add(topicKey);
    }
    setCompletedTopics(newCompleted);
    
    // Save to localStorage for persistence
    localStorage.setItem(`studyProgress_${company}`, JSON.stringify(Array.from(newCompleted)));
  };

  const calculateProgress = () => {
    const totalTopics = topicEntries.length;
    const completedCount = completedTopics.size;
    return totalTopics > 0 ? (completedCount / totalTopics) * 100 : 0;
  };

  // Load saved progress on component mount
  React.useEffect(() => {
    const saved = localStorage.getItem(`studyProgress_${company}`);
    if (saved) {
      setCompletedTopics(new Set(JSON.parse(saved)));
    }
  }, [company]);

  // Export study plan functionality
  const exportStudyPlan = () => {
    const studyPlanData = {
      company,
      analysisDate: new Date().toISOString(),
      totalTopics: topicEntries.length,
      completedTopics: Array.from(completedTopics),
      progress: calculateProgress(),
      highPriority: highPriorityTopics.map(([key, data]) => ({
        topic: data.topic_name,
        frequency: data.weighted_frequency,
        completed: completedTopics.has(key)
      })),
      mediumPriority: mediumPriorityTopics.map(([key, data]) => ({
        topic: data.topic_name,
        frequency: data.weighted_frequency,
        completed: completedTopics.has(key)
      })),
      lowPriority: lowPriorityTopics.map(([key, data]) => ({
        topic: data.topic_name,
        frequency: data.weighted_frequency,
        completed: completedTopics.has(key)
      }))
    };

    const blob = new Blob([JSON.stringify(studyPlanData, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${company}_Study_Plan_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Generate practice set functionality
  const generatePracticeSet = () => {
    setPracticeDialogOpen(true);
  };

  // Schedule study time functionality
  const scheduleStudyTime = () => {
    setScheduleDialogOpen(true);
  };

  // Track progress functionality (opens analytics view)
  const trackProgress = () => {
    const progressData = {
      totalTopics: topicEntries.length,
      completed: completedTopics.size,
      percentage: calculateProgress(),
      highPriorityCompleted: highPriorityTopics.filter(([key]) => completedTopics.has(key)).length,
      mediumPriorityCompleted: mediumPriorityTopics.filter(([key]) => completedTopics.has(key)).length,
      lowPriorityCompleted: lowPriorityTopics.filter(([key]) => completedTopics.has(key)).length
    };
    
    alert(`Progress Tracking for ${company}:
    
Total Progress: ${progressData.percentage.toFixed(1)}%
Completed Topics: ${progressData.completed}/${progressData.totalTopics}

High Priority: ${progressData.highPriorityCompleted}/${highPriorityTopics.length}
Medium Priority: ${progressData.mediumPriorityCompleted}/${mediumPriorityTopics.length}
Low Priority: ${progressData.lowPriorityCompleted}/${lowPriorityTopics.length}`);
  };

  const handleScheduleSubmit = () => {
    const schedule = {
      company,
      duration: scheduleForm.duration,
      hoursPerDay: scheduleForm.hoursPerDay,
      startDate: scheduleForm.startDate,
      topics: topicEntries.length
    };
    
    alert(`Study Schedule Created for ${company}:
    
Duration: ${schedule.duration} weeks
Daily Study: ${schedule.hoursPerDay} hours
Start Date: ${schedule.startDate}
Total Topics: ${schedule.topics}

Schedule has been saved locally!`);
    
    localStorage.setItem(`studySchedule_${company}`, JSON.stringify(schedule));
    setScheduleDialogOpen(false);
  };

  const renderTopicSection = (topics, title, color) => {
    if (topics.length === 0) return null;

    return (
      <Accordion key={title} defaultExpanded={title === 'High Priority Topics'} sx={{ mb: 2 }}>
        <AccordionSummary expandIcon={<ExpandMore />} sx={{ bgcolor: `${color}.50` }}>
          <Box display="flex" alignItems="center" width="100%">
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              {title} ({topics.length})
            </Typography>
            <Chip 
              label={`${topics.filter(([key]) => completedTopics.has(key)).length}/${topics.length} completed`}
              color={color}
              size="small"
            />
          </Box>
        </AccordionSummary>
        
        <AccordionDetails>
          <List>
            {topics.map(([topicKey, topicData]) => (
              <ListItem
                key={topicKey}
                button
                onClick={() => toggleTopicCompletion(topicKey)}
                sx={{
                  border: '1px solid #e0e0e0',
                  borderRadius: 2,
                  mb: 1,
                  backgroundColor: completedTopics.has(topicKey) ? '#f0f8f0' : 'white',
                  '&:hover': {
                    backgroundColor: completedTopics.has(topicKey) ? '#e8f5e8' : '#f5f5f5'
                  }
                }}
              >
                <ListItemIcon>
                  {completedTopics.has(topicKey) ? (
                    <CheckCircleOutline color="success" />
                  ) : (
                    <RadioButtonUnchecked />
                  )}
                </ListItemIcon>
                
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={0.5}>
                      <Typography variant="subtitle1" fontWeight="medium">
                        {topicData.topic_name}
                      </Typography>
                      <Box display="flex" gap={1} flexWrap="wrap" alignItems="center">
                        <Chip
                          label={`${topicData.weighted_frequency}%`}
                          size="small"
                          color={color}
                          title="Mention frequency across interviews"
                        />
                        <Chip
                          label={topicData.category}
                          size="small"
                          variant="outlined"
                        />
                        <SpecificityBadge score={topicData.discriminative_score} />
                        <SemanticBadge score={topicData.semantic_confidence} />
                      </Box>
                    </Box>
                  }
                  secondary={
                    <Box mt={1}>
                      <Typography variant="body2" color="textSecondary" gutterBottom>
                        Confidence: {topicData.confidence_score} | Priority: {topicData.priority_level}
                        {topicData.mentions_count != null && ` | In ${topicData.mentions_count} interview(s)`}
                      </Typography>

                      {/* Practice Problems */}
                      <Box mt={1}>
                        <Typography variant="caption" display="block" gutterBottom>
                          Recommended Practice:
                        </Typography>
                        {topicData.topic_name.toLowerCase().includes('array') && (
                          <Box display="flex" flexWrap="wrap" gap={0.5}>
                            {['Two Sum', 'Best Time to Buy Stock', 'Maximum Subarray'].map((problem, idx) => (
                              <Chip key={idx} label={problem} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                            ))}
                          </Box>
                        )}
                        {topicData.topic_name.toLowerCase().includes('dynamic') && (
                          <Box display="flex" flexWrap="wrap" gap={0.5}>
                            {['Climbing Stairs', 'House Robber', 'Coin Change'].map((problem, idx) => (
                              <Chip key={idx} label={problem} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                            ))}
                          </Box>
                        )}
                        {topicData.topic_name.toLowerCase().includes('tree') && (
                          <Box display="flex" flexWrap="wrap" gap={0.5}>
                            {['Binary Tree Traversal', 'Maximum Depth', 'Validate BST'].map((problem, idx) => (
                              <Chip key={idx} label={problem} size="small" variant="outlined" sx={{ fontSize: '0.7rem' }} />
                            ))}
                          </Box>
                        )}
                      </Box>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        </AccordionDetails>
      </Accordion>
    );
  };

  return (
    <Box sx={{ width: '100%', maxWidth: '100%' }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3} flexWrap="wrap" gap={2}>
        <Typography variant="h5">
          Personalized Study Plan for {company}
        </Typography>
        <Button 
          variant="outlined" 
          size="small" 
          startIcon={<Download />}
          onClick={exportStudyPlan}
        >
          Export Plan
        </Button>
      </Box>

      {/* Progress Overview - Responsive Grid */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Assignment color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Progress Overview</Typography>
              </Box>
              
              <Box mb={2}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">Study Progress</Typography>
                  <Typography variant="body2" fontWeight="bold">
                    {Math.round(calculateProgress())}%
                  </Typography>
                </Box>
                <LinearProgress 
                  variant="determinate" 
                  value={calculateProgress()}
                  sx={{ height: 10, borderRadius: 5 }}
                />
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={4}>
                  <Typography variant="h4" color="error">{highPriorityTopics.length}</Typography>
                  <Typography variant="caption" color="textSecondary">High Priority</Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="h4" color="warning.main">{mediumPriorityTopics.length}</Typography>
                  <Typography variant="caption" color="textSecondary">Medium Priority</Typography>
                </Grid>
                <Grid item xs={4}>
                  <Typography variant="h4" color="success.main">{lowPriorityTopics.length}</Typography>
                  <Typography variant="caption" color="textSecondary">Low Priority</Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Timer color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Recommended Timeline</Typography>
              </Box>
              
              <Typography variant="body2" gutterBottom>
                Based on {analysis_metadata?.sample_size || 0} interview experiences
              </Typography>
              
              <Box mt={2}>
                <Typography variant="body2" color="error" gutterBottom>
                  Week 1-2: Focus on High Priority Topics ({highPriorityTopics.length} topics)
                </Typography>
                <Typography variant="body2" color="warning.main" gutterBottom>
                  Week 3: Cover Medium Priority Topics ({mediumPriorityTopics.length} topics)
                </Typography>
                <Typography variant="body2" color="success.main" gutterBottom>
                  Week 4: Review Low Priority & Mock Interviews ({lowPriorityTopics.length} topics)
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Study Plan Sections */}
      <Box sx={{ mb: 3 }}>
        {renderTopicSection(highPriorityTopics, 'High Priority Topics', 'error')}
        {renderTopicSection(mediumPriorityTopics, 'Medium Priority Topics', 'warning')}
        {renderTopicSection(lowPriorityTopics, 'Low Priority Topics', 'success')}
      </Box>

      {/* Functional Action Buttons */}
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Study Tools & Actions
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <Button 
                variant="outlined" 
                fullWidth
                startIcon={<School />}
                onClick={generatePracticeSet}
              >
                Generate Practice Set
              </Button>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Button 
                variant="outlined" 
                fullWidth
                startIcon={<Schedule />}
                onClick={scheduleStudyTime}
              >
                Schedule Study Time
              </Button>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Button 
                variant="outlined" 
                fullWidth
                startIcon={<Analytics />}
                onClick={trackProgress}
              >
                Track Progress
              </Button>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Button 
                variant="outlined" 
                fullWidth
                startIcon={<Download />}
                onClick={exportStudyPlan}
              >
                Export Data
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Schedule Study Time Dialog */}
      <Dialog open={scheduleDialogOpen} onClose={() => setScheduleDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Schedule Your Study Plan</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Study Duration"
                value={scheduleForm.duration}
                onChange={(e) => setScheduleForm({...scheduleForm, duration: e.target.value})}
                fullWidth
              >
                <MenuItem value="2">2 weeks</MenuItem>
                <MenuItem value="4">4 weeks</MenuItem>
                <MenuItem value="6">6 weeks</MenuItem>
                <MenuItem value="8">8 weeks</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                select
                label="Hours per Day"
                value={scheduleForm.hoursPerDay}
                onChange={(e) => setScheduleForm({...scheduleForm, hoursPerDay: e.target.value})}
                fullWidth
              >
                <MenuItem value="1">1 hour</MenuItem>
                <MenuItem value="2">2 hours</MenuItem>
                <MenuItem value="3">3 hours</MenuItem>
                <MenuItem value="4">4 hours</MenuItem>
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Start Date"
                type="date"
                value={scheduleForm.startDate}
                onChange={(e) => setScheduleForm({...scheduleForm, startDate: e.target.value})}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setScheduleDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleScheduleSubmit} variant="contained">Create Schedule</Button>
        </DialogActions>
      </Dialog>

      {/* Practice Set Dialog */}
      <Dialog open={practiceDialogOpen} onClose={() => setPracticeDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Generated Practice Set for {company}</DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Based on your high priority topics, here's a customized practice set:
          </Typography>
          
          {highPriorityTopics.slice(0, 3).map(([key, data], index) => (
            <Card key={key} sx={{ mb: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {index + 1}. {data.topic_name}
                </Typography>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  Frequency: {data.weighted_frequency}% | Priority: {data.priority_level}
                </Typography>
                <Box display="flex" flexWrap="wrap" gap={1} mt={1}>
                  {data.topic_name.toLowerCase().includes('array') && 
                    ['Two Sum', 'Best Time to Buy Stock', 'Maximum Subarray'].map((problem) => (
                      <Chip key={problem} label={problem} size="small" color="primary" />
                    ))
                  }
                  {data.topic_name.toLowerCase().includes('dynamic') && 
                    ['Climbing Stairs', 'House Robber', 'Coin Change'].map((problem) => (
                      <Chip key={problem} label={problem} size="small" color="primary" />
                    ))
                  }
                  {data.topic_name.toLowerCase().includes('tree') && 
                    ['Binary Tree Traversal', 'Maximum Depth', 'Validate BST'].map((problem) => (
                      <Chip key={problem} label={problem} size="small" color="primary" />
                    ))
                  }
                </Box>
              </CardContent>
            </Card>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPracticeDialogOpen(false)}>Close</Button>
          <Button
            variant="contained"
            onClick={() => window.open('https://leetcode.com/problemset/', '_blank')}
          >
            Open LeetCode
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default StudyPlan;