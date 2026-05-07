import React, { useState } from 'react';
import { Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Box, Typography, Paper, Grid, ToggleButton, ToggleButtonGroup, Chip } from '@mui/material';
import { TrendingUp, Fingerprint } from '@mui/icons-material';

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend);

const priorityColor = (level, alpha = 0.8) => {
  switch ((level || '').toUpperCase()) {
    case 'HIGH':   return `rgba(255, 99, 132, ${alpha})`;
    case 'MEDIUM': return `rgba(54, 162, 235, ${alpha})`;
    default:       return `rgba(255, 206, 86, ${alpha})`;
  }
};

const discColor = (score, alpha = 0.8) => {
  if (score >= 0.7) return `rgba(156, 39, 176, ${alpha})`;   // purple — highly specific
  if (score >= 0.4) return `rgba(33, 150, 243, ${alpha})`;   // blue — moderately specific
  return `rgba(158, 158, 158, ${alpha})`;                     // grey — generic
};

const InsightsChart = ({ insights, title = 'Topic Analysis' }) => {
  const [chartMode, setChartMode] = useState('frequency');

  if (!insights || !insights.insights) {
    return (
      <Paper sx={{ p: 2, textAlign: 'center' }}>
        <Typography variant="body1" color="textSecondary">
          No insights data available
        </Typography>
      </Paper>
    );
  }

  const topicEntries = Object.entries(insights.insights).slice(0, 10);
  const labels = topicEntries.map(([, d]) => d.topic_name);
  const hasMlFields = topicEntries.some(([, d]) => d.discriminative_score != null);

  // ── Frequency chart data ────────────────────────────────────────────────────
  const frequencyData = {
    labels,
    datasets: [{
      label: 'Mention Frequency (%)',
      data: topicEntries.map(([, d]) => d.weighted_frequency),
      backgroundColor: topicEntries.map(([, d]) => priorityColor(d.priority_level)),
      borderColor:     topicEntries.map(([, d]) => priorityColor(d.priority_level, 1)),
      borderWidth: 1,
    }],
  };

  const freqOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' },
      tooltip: {
        callbacks: {
          afterLabel: (ctx) => {
            const d = topicEntries[ctx.dataIndex]?.[1];
            if (!d) return '';
            const lines = [`Priority: ${d.priority_level}`, `Confidence: ${d.confidence_score}`];
            if (d.discriminative_score != null)
              lines.push(`Company-specific: ${Math.round(d.discriminative_score * 100)}%`);
            if (d.semantic_confidence != null)
              lines.push(`Semantic confidence: ${d.semantic_confidence}`);
            return lines;
          },
        },
      },
    },
    scales: { y: { beginAtZero: true } },
  };

  // ── Discriminative score chart data ─────────────────────────────────────────
  const discData = {
    labels,
    datasets: [{
      label: 'Company-Specificity Score (%)',
      data: topicEntries.map(([, d]) => Math.round((d.discriminative_score ?? 0) * 100)),
      backgroundColor: topicEntries.map(([, d]) => discColor(d.discriminative_score ?? 0)),
      borderColor:     topicEntries.map(([, d]) => discColor(d.discriminative_score ?? 0, 1)),
      borderWidth: 1,
    }],
  };

  const discOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'top' },
      tooltip: {
        callbacks: {
          afterLabel: (ctx) => {
            const d = topicEntries[ctx.dataIndex]?.[1];
            if (!d) return '';
            const lines = [
              `Frequency: ${d.weighted_frequency}%`,
              `IDF: ${d.idf ?? 'N/A'}`,
              `TF-IDF score: ${d.tfidf_score ?? 'N/A'}`,
            ];
            if (d.semantic_confidence != null)
              lines.push(`Semantic confidence: ${d.semantic_confidence}`);
            return lines;
          },
        },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        title: { display: true, text: 'Specificity (%)' },
      },
    },
  };

  // ── Category doughnut ───────────────────────────────────────────────────────
  const categories = {};
  Object.values(insights.insights).forEach(t => {
    const c = t.category || 'other';
    categories[c] = (categories[c] || 0) + 1;
  });

  const distributionData = {
    labels: Object.keys(categories),
    datasets: [{
      data: Object.values(categories),
      backgroundColor: [
        'rgba(255, 99, 132, 0.8)',
        'rgba(54, 162, 235, 0.8)',
        'rgba(255, 206, 86, 0.8)',
        'rgba(75, 192, 192, 0.8)',
        'rgba(153, 102, 255, 0.8)',
      ],
      borderWidth: 1,
    }],
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: 'right' } },
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} flexWrap="wrap" gap={1}>
        <Typography variant="h6">{title}</Typography>

        {hasMlFields && (
          <Box display="flex" alignItems="center" gap={1}>
            <Chip label="ML-Scored" size="small" color="secondary" variant="outlined" />
            <ToggleButtonGroup
              value={chartMode}
              exclusive
              onChange={(_, v) => v && setChartMode(v)}
              size="small"
            >
              <ToggleButton value="frequency">
                <TrendingUp sx={{ mr: 0.5, fontSize: 16 }} />
                Frequency
              </ToggleButton>
              <ToggleButton value="discriminative">
                <Fingerprint sx={{ mr: 0.5, fontSize: 16 }} />
                Company-Specific
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>
        )}
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 2, height: 400 }}>
            {chartMode === 'frequency' ? (
              <>
                <Typography variant="subtitle1" gutterBottom>
                  Topic Frequency — how often each topic appears across interviews
                </Typography>
                <Box sx={{ height: 320 }}>
                  <Bar data={frequencyData} options={freqOptions} />
                </Box>
              </>
            ) : (
              <>
                <Typography variant="subtitle1" gutterBottom>
                  Company-Specificity — TF-IDF score showing topics unique to this company
                </Typography>
                <Box sx={{ height: 10, display: 'flex', gap: 2, mb: 1, flexWrap: 'wrap' }}>
                  {[
                    { color: 'rgba(156,39,176,0.8)', label: '≥70% — highly specific' },
                    { color: 'rgba(33,150,243,0.8)', label: '40–70% — moderately specific' },
                    { color: 'rgba(158,158,158,0.8)', label: '<40% — generic topic' },
                  ].map(({ color, label }) => (
                    <Box key={label} display="flex" alignItems="center" gap={0.5} mt={0}>
                      <Box sx={{ width: 12, height: 12, borderRadius: '2px', bgcolor: color, flexShrink: 0 }} />
                      <Typography variant="caption">{label}</Typography>
                    </Box>
                  ))}
                </Box>
                <Box sx={{ height: 310 }}>
                  <Bar data={discData} options={discOptions} />
                </Box>
              </>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 2, height: 400 }}>
            <Typography variant="subtitle1" gutterBottom>
              Category Distribution
            </Typography>
            <Box sx={{ height: 320 }}>
              <Doughnut data={distributionData} options={doughnutOptions} />
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Legend row for frequency chart */}
      {chartMode === 'frequency' && (
        <Box display="flex" gap={2} mt={1} flexWrap="wrap">
          {[
            { color: priorityColor('HIGH'),   label: 'HIGH priority' },
            { color: priorityColor('MEDIUM'), label: 'MEDIUM priority' },
            { color: priorityColor('LOW'),    label: 'LOW priority' },
          ].map(({ color, label }) => (
            <Box key={label} display="flex" alignItems="center" gap={0.5}>
              <Box sx={{ width: 12, height: 12, borderRadius: '2px', bgcolor: color, flexShrink: 0 }} />
              <Typography variant="caption">{label}</Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};

export default InsightsChart;
