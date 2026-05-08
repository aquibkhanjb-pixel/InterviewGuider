import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import logging

class ExponentialDecayCalculator:
    """
    Advanced exponential decay calculator for time-based weighting.
    Implements multiple decay models and trend analysis.
    """
    
    def __init__(self, decay_lambda: float = 0.08):
        self.decay_lambda = decay_lambda
        self.logger = logging.getLogger(__name__)
    
    def calculate_weight(self, experience_date: datetime) -> float:
        """
        Calculate exponential decay weight: w = e^(-λt)

        Args:
            experience_date: When the experience was published

        Returns:
            Weight between 0.01 and 1.0
        """
        if isinstance(experience_date, str):
            experience_date = datetime.fromisoformat(experience_date.replace('Z', '+00:00'))

        # Strip tzinfo to avoid naive/aware comparison errors (psycopg3 returns tz-aware)
        if hasattr(experience_date, 'tzinfo') and experience_date.tzinfo is not None:
            experience_date = experience_date.replace(tzinfo=None)

        now = datetime.utcnow()
        age_months = (now - experience_date).days / 30.44  # Average days per month
        
        # Exponential decay formula
        weight = math.exp(-self.decay_lambda * age_months)
        
        # Ensure minimum weight
        return max(weight, 0.01)
    
    def calculate_batch_weights(self, experience_dates: List[datetime]) -> List[float]:
        """Calculate weights for multiple experiences efficiently."""
        return [self.calculate_weight(date) for date in experience_dates]
    
    def calculate_weighted_average(self, values: List[float], 
                                 experience_dates: List[datetime]) -> float:
        """Calculate weighted average using exponential decay."""
        if len(values) != len(experience_dates):
            raise ValueError("Values and dates lists must have same length")
        
        weights = self.calculate_batch_weights(experience_dates)
        
        weighted_sum = sum(val * weight for val, weight in zip(values, weights))
        total_weight = sum(weights)
        
        return weighted_sum / total_weight if total_weight > 0 else 0
    
    def analyze_temporal_trends(self, data_points: List[Dict]) -> Dict:
        """
        Analyze trends over time using exponential decay weighting.
        
        Args:
            data_points: List of {'value': float, 'date': datetime} dicts
            
        Returns:
            Trend analysis results
        """
        if len(data_points) < 3:
            return {
                'trend_direction': 'insufficient_data',
                'trend_strength': 0.0,
                'confidence': 0.0
            }
        
        # Sort by date
        sorted_data = sorted(data_points, key=lambda x: x['date'])
        
        # Split into time periods
        total_span = sorted_data[-1]['date'] - sorted_data[0]['date']
        mid_point = sorted_data[0]['date'] + total_span / 2
        
        recent_data = [d for d in sorted_data if d['date'] >= mid_point]
        older_data = [d for d in sorted_data if d['date'] < mid_point]
        
        if not recent_data or not older_data:
            return {
                'trend_direction': 'insufficient_data',
                'trend_strength': 0.0,
                'confidence': 0.0
            }
        
        # Calculate weighted averages for each period
        recent_values = [d['value'] for d in recent_data]
        recent_dates = [d['date'] for d in recent_data]
        recent_avg = self.calculate_weighted_average(recent_values, recent_dates)
        
        older_values = [d['value'] for d in older_data]
        older_dates = [d['date'] for d in older_data]
        older_avg = self.calculate_weighted_average(older_values, older_dates)
        
        # Calculate trend
        if older_avg == 0:
            trend_strength = 0.0
        else:
            trend_strength = (recent_avg - older_avg) / older_avg
        
        # Determine direction
        if abs(trend_strength) < 0.1:
            trend_direction = 'stable'
        elif trend_strength > 0:
            trend_direction = 'increasing'
        else:
            trend_direction = 'decreasing'
        
        # Calculate confidence based on sample sizes and consistency
        confidence = self._calculate_trend_confidence(recent_data, older_data, trend_strength)
        
        return {
            'trend_direction': trend_direction,
            'trend_strength': abs(trend_strength),
            'confidence': confidence,
            'recent_average': recent_avg,
            'older_average': older_avg,
            'sample_sizes': {
                'recent': len(recent_data),
                'older': len(older_data)
            }
        }
    
    def _calculate_trend_confidence(self, recent_data: List[Dict], 
                                  older_data: List[Dict], 
                                  trend_strength: float) -> float:
        """Calculate confidence in trend analysis."""
        # Base confidence on sample sizes
        min_sample_size = min(len(recent_data), len(older_data))
        size_confidence = min(min_sample_size / 5.0, 1.0)  # Max confidence at 5+ samples
        
        # Adjust for trend strength
        strength_confidence = min(abs(trend_strength) * 2, 1.0)
        
        # Calculate variance within periods
        recent_values = [d['value'] for d in recent_data]
        older_values = [d['value'] for d in older_data]
        
        recent_variance = self._calculate_variance(recent_values)
        older_variance = self._calculate_variance(older_values)
        
        # Lower variance = higher confidence
        avg_variance = (recent_variance + older_variance) / 2
        variance_confidence = 1 / (1 + avg_variance) if avg_variance > 0 else 1.0
        
        # Combine factors
        overall_confidence = (size_confidence + strength_confidence + variance_confidence) / 3
        
        return round(overall_confidence, 2)
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calculate variance of a list of values."""
        if len(values) <= 1:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        return variance
    
    def get_decay_visualization_data(self, months_range: int = 60) -> List[Dict]:
        """Generate data for visualizing decay function."""
        data = []
        
        for month in range(0, months_range + 1):
            fake_date = datetime.utcnow() - timedelta(days=month * 30.44)
            weight = self.calculate_weight(fake_date)
            
            data.append({
                'months_ago': month,
                'weight': weight,
                'weight_percentage': weight * 100
            })
        
        return data