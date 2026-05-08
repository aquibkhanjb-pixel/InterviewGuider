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

/** Client-side company name validator — rejects obvious non-names. */
const validateCompanyName = (name) => {
  const s = name.trim();
  if (s.length < 2) return 'Name must be at least 2 characters.';
  if (!/[a-zA-Z]/.test(s)) return 'Name must contain at least one letter.';
  if (/^\d+$/.test(s)) return 'A company name cannot be only numbers.';
  if (/^[^a-zA-Z0-9]+$/.test(s)) return 'Please enter a valid company name.';
  return null; // valid
};

const CompanySelector = ({ selectedCompanies, onSelectionChange, maxSelection = 5 }) => {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [customInput, setCustomInput] = useState('');
  const [inputError, setInputError] = useState('');

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

    const validationError = validateCompanyName(name);
    if (validationError) {
      setInputError(validationError);
      return;
    }
    setInputError('');

    // Case-insensitive duplicate check against both already-selected and known companies
    const nameLower = name.toLowerCase();
    const alreadySelected = selectedCompanies.some(c => c.toLowerCase() === nameLower);
    if (alreadySelected) {
      setCustomInput('');
      return;
    }
    if (selectedCompanies.length >= maxSelection) return;

    // If the company already exists in our DB list, use the canonical DB name
    const existing = companies.find(c => c.name.toLowerCase() === nameLower);
    onSelectionChange([...selectedCompanies, existing ? existing.name : name]);
    setCustomInput('');
  };

  const handleCustomKeyDown = (e) => {
    if (e.key === 'Enter') handleAddCustom();
    else if (inputError) setInputError(''); // clear error on any new typing
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
          onChange={(e) => { setCustomInput(e.target.value); if (inputError) setInputError(''); }}
          onKeyDown={handleCustomKeyDown}
          disabled={selectedCompanies.length >= maxSelection}
          error={!!inputError}
          helperText={inputError || ''}
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

      {!inputError && (
        <Typography variant="caption" color="textSecondary" sx={{ mt: 0.5, display: 'block' }}>
          Any company name works. If no data is found after analysis, the company may not have public interview experiences yet.
        </Typography>
      )}

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
