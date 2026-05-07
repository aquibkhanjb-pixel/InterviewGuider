import React, { useState, useEffect } from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Box,
  CircularProgress,
  Alert,
  Typography,
  TextField,
  Button,
  Divider
} from '@mui/material';
import { Add } from '@mui/icons-material';
import { interviewAPI } from '../../services/api.js';

const CompanySelector = ({ selectedCompanies, onSelectionChange, maxSelection = 5 }) => {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [customInput, setCustomInput] = useState('');

  useEffect(() => {
    fetchCompanies();
  }, []);

  const fetchCompanies = async () => {
    try {
      setLoading(true);
      const response = await interviewAPI.getCompanies();
      const activeCompanies = response.data.companies.filter(company =>
        company.name !== 'Unknown' && company.name.trim() !== ''
      );
      setCompanies(activeCompanies);
    } catch (err) {
      setError('Failed to load companies');
      console.error('Error fetching companies:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCompanyToggle = (companyName) => {
    const isSelected = selectedCompanies.includes(companyName);
    if (isSelected) {
      onSelectionChange(selectedCompanies.filter(n => n !== companyName));
    } else if (selectedCompanies.length < maxSelection) {
      onSelectionChange([...selectedCompanies, companyName]);
    }
  };

  const handleRemoveCompany = (companyName) => {
    onSelectionChange(selectedCompanies.filter(n => n !== companyName));
  };

  const handleAddCustom = () => {
    const name = customInput.trim();
    if (!name) return;
    if (selectedCompanies.includes(name)) {
      setCustomInput('');
      return;
    }
    if (selectedCompanies.length >= maxSelection) return;
    onSelectionChange([...selectedCompanies, name]);
    setCustomInput('');
  };

  const handleCustomKeyDown = (e) => {
    if (e.key === 'Enter') handleAddCustom();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={2}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading companies...</Typography>
      </Box>
    );
  }

  if (error) {
    return <Alert severity="warning">{error}</Alert>;
  }

  return (
    <Box sx={{ width: '100%' }}>
      {/* Dropdown for known companies */}
      <FormControl fullWidth margin="normal">
        <InputLabel>Select from known companies</InputLabel>
        <Select
          multiple
          value={selectedCompanies}
          label="Select from known companies"
          renderValue={() => ''}
        >
          {companies.map((company) => (
            <MenuItem
              key={company.name}
              value={company.name}
              onClick={() => handleCompanyToggle(company.name)}
              disabled={selectedCompanies.length >= maxSelection && !selectedCompanies.includes(company.name)}
            >
              <Box display="flex" justifyContent="space-between" width="100%">
                <span>{company.display_name || company.name}</span>
                <small style={{ color: company.experience_count > 0 ? 'inherit' : '#999' }}>
                  {company.experience_count > 0
                    ? `${company.experience_count} experiences`
                    : 'No data — run analysis'}
                </small>
              </Box>
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Custom company input */}
      <Divider sx={{ my: 2 }}>
        <Typography variant="caption" color="textSecondary">OR add any company</Typography>
      </Divider>

      <Box display="flex" gap={1} alignItems="center">
        <TextField
          size="small"
          fullWidth
          label="Type company name (e.g. TCS, Capgemini, Infosys…)"
          value={customInput}
          onChange={(e) => setCustomInput(e.target.value)}
          onKeyDown={handleCustomKeyDown}
          disabled={selectedCompanies.length >= maxSelection}
        />
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleAddCustom}
          disabled={!customInput.trim() || selectedCompanies.length >= maxSelection}
          sx={{ whiteSpace: 'nowrap' }}
        >
          Add
        </Button>
      </Box>

      <Typography variant="caption" color="textSecondary" sx={{ mt: 0.5, display: 'block' }}>
        Any company name works — the scraper will search for it automatically.
      </Typography>

      {/* Selected chips */}
      {selectedCompanies.length > 0 && (
        <Box mt={2}>
          <Box display="flex" flexWrap="wrap" gap={1}>
            {selectedCompanies.map((company) => (
              <Chip
                key={company}
                label={company}
                onDelete={() => handleRemoveCompany(company)}
                color="primary"
                variant="outlined"
              />
            ))}
          </Box>
          <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
            {selectedCompanies.length}/{maxSelection} companies selected
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default CompanySelector;
