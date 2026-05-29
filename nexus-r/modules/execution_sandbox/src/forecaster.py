import math
import random
from typing import Dict, Any, List, Optional

class TimesFMForecaster:
    """
    Forecasting Engine for NEXUS-R.
    Integrates Google's TimesFM (Time Series Foundation Model) for zero-shot forecasting,
    with a premium, high-fidelity statistical zero-shot fallback that models trends,
    seasonality, volatility, and quantile prediction intervals.
    """
    def __init__(self):
        self.has_timesfm = False
        try:
            # Attempt to import timesfm if available
            import timesfm
            self.has_timesfm = True
        except ImportError:
            pass

    def forecast(self, history: List[float], horizon: int = 5) -> Dict[str, Any]:
        """
        Perform zero-shot time-series forecasting.
        
        Args:
            history: List of floats representing the historical sequence.
            horizon: Number of future points to predict.
            
        Returns:
            Dict containing:
                "success": bool
                "history": List[float]
                "forecast": List[float] (50th percentile / mean)
                "lower_bound": List[float] (10th percentile prediction interval)
                "upper_bound": List[float] (90th percentile prediction interval)
                "metrics": Dict of statistical insights
                "ascii_chart": str
        """
        if not history:
            return {"success": False, "error": "History sequence is empty."}
            
        if len(history) < 3:
            return {"success": False, "error": "At least 3 historical points are required for time-series forecasting."}

        # If TimesFM is installed on the host system, we use it!
        if self.has_timesfm:
            try:
                return self._run_timesfm(history, horizon)
            except Exception as e:
                # Fallback on any failure of local GPU/weights
                return self._run_fallback(history, horizon, fallback_reason=str(e))
        else:
            return self._run_fallback(history, horizon)

    def _run_timesfm(self, history: List[float], horizon: int) -> Dict[str, Any]:
        """Runs the official TimesFM foundation model (if library is present)."""
        import numpy as np
        import timesfm
        
        # Load the pre-trained model (cached locally in the environment)
        tfm = timesfm.TimesFm(
            context_len=min(len(history), 32),
            horizon=horizon,
            input_patch_len=32,
            output_patch_len=128,
            num_layers=20,
            model_dim=1280,
            backend="cpu",  # Fallback to CPU to avoid CUDA dependency issues
        )
        # Note: Model loading would typically be done once in __init__, 
        # but is done here lazy-load style to keep memory footprint light.
        tfm.load_from_checkpoint(repo_id="google/timesfm-1.0-200m")
        
        # Format input as a batch of size 1
        inputs = [np.array(history)]
        freq = [0] # 0 for high-frequency or unspecified
        
        forecast_input = tfm.forecast(inputs, freq=freq)
        # forecast_input returns a tuple of (mean_forecast, quantiles_forecast)
        mean_fc = forecast_input[0][0].tolist()
        quantiles = forecast_input[1][0] # shape (horizon, num_quantiles)
        
        # Extract 10th percentile (quantile index 1 or 2 depending on config) and 90th percentile
        # Standard quantiles: [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        lower_fc = quantiles[:, 1].tolist()  # 10%
        upper_fc = quantiles[:, 7].tolist()  # 90%
        
        metrics = self._calculate_metrics(history, mean_fc)
        ascii_chart = self._generate_ascii_chart(history, mean_fc, lower_fc, upper_fc)
        
        return {
            "success": True,
            "engine": "Google TimesFM (Zero-Shot Foundation Model)",
            "history": history,
            "forecast": mean_fc,
            "lower_bound": lower_fc,
            "upper_bound": upper_fc,
            "metrics": metrics,
            "ascii_chart": ascii_chart
        }

    def _run_fallback(self, history: List[float], horizon: int, fallback_reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Calculates high-fidelity zero-shot predictions using state-of-the-art
        statistical forecasting models (Holt-Winters, Trend-Regression & Volatility quantiles).
        """
        n = len(history)
        
        # 1. Trend Analysis (Least Squares Regression)
        x = list(range(n))
        mean_x = sum(x) / n
        mean_y = sum(history) / n
        
        num = sum((x[i] - mean_x) * (history[i] - mean_y) for i in range(n))
        den = sum((x[i] - mean_x) ** 2 for i in range(n))
        
        slope = num / den if den != 0 else 0.0
        intercept = mean_y - slope * mean_x
        
        # Calculate quadratic trend component for accelerating datasets
        # e.g., if history grows exponentially or quadratically
        quad_num = sum((x[i]**2) * history[i] for i in range(n))
        quad_den = sum(x[i]**4 for i in range(n))
        quad_coefficient = quad_num / quad_den if quad_den != 0 else 0.0
        
        # 2. Seasonality Detection
        # Check cycle lengths of 3, 4, or 12 points
        season_period = 1
        best_autocorr = 0.0
        for period in [3, 4, 12]:
            if n >= period * 2:
                # Calculate simple auto-correlation at lag 'period'
                diffs_t = [history[i] - mean_y for i in range(n - period)]
                diffs_lag = [history[i + period] - mean_y for i in range(n - period)]
                cov = sum(diffs_t[i] * diffs_lag[i] for i in range(len(diffs_t)))
                var = sum((history[i] - mean_y)**2 for i in range(n))
                autocorr = cov / var if var != 0 else 0.0
                if autocorr > best_autocorr and autocorr > 0.3:
                    best_autocorr = autocorr
                    season_period = period
                    
        # 3. Triple Exponential Smoothing (Holt-Winters Core)
        # Initialize level, trend, and seasonal indices
        level = history[0]
        trend = history[1] - history[0]
        seasonals = [0.0] * season_period
        
        if season_period > 1:
            for i in range(season_period):
                seasonals[i] = history[i] - (intercept + slope * i)
                
        # Smoothing factors
        alpha = 0.4
        beta = 0.2
        gamma = 0.3
        
        # Perform smoothing updates over history
        residuals = []
        for i in range(n):
            val = history[i]
            last_level = level
            
            if season_period > 1:
                idx = i % season_period
                level = alpha * (val - seasonals[idx]) + (1 - alpha) * (level + trend)
                seasonals[idx] = gamma * (val - level) + (1 - gamma) * seasonals[idx]
            else:
                level = alpha * val + (1 - alpha) * (level + trend)
                
            trend = beta * (level - last_level) + (1 - beta) * trend
            fitted = last_level + trend + (seasonals[i % season_period] if season_period > 1 else 0.0)
            residuals.append(val - fitted)
            
        # 4. Generate Future Forecasts
        mean_fc = []
        lower_fc = []
        upper_fc = []
        
        # Calculate standard deviation of historical residuals to build confidence bounds
        variance = sum(r**2 for r in residuals) / max(n - 2, 1)
        std_err = math.sqrt(variance) if variance > 0 else (mean_y * 0.05) # fallback standard error
        
        # Adjust for small datasets
        if std_err == 0:
            std_err = 1.0
            
        for m in range(1, horizon + 1):
            # Calculate base prediction
            if season_period > 1:
                idx = (n + m - 1) % season_period
                pred = level + m * trend + seasonals[idx]
            else:
                # Weighted mixture of linear trend and simple level
                pred = level + m * trend
                
            # If the data shows exponential growth, smoothly incorporate quadratic trend
            is_growing_fast = n >= 4 and history[-1] > history[-2] > history[-3]
            if is_growing_fast and slope > 0:
                pred = 0.7 * pred + 0.3 * (intercept + slope * (n + m - 1) + 0.1 * quad_coefficient * (n + m - 1)**2)
                
            # Apply logical floor for non-negative series (if all history is >= 0)
            if all(h >= 0 for h in history):
                pred = max(0.0, pred)
                
            # Compute confidence bounds expanding with horizon (standard time-series root-t error propagation)
            step_std_err = std_err * math.sqrt(m)
            # 1.28 standard deviations corresponds to ~10% and 90% quantiles
            lower = pred - 1.28 * step_std_err
            upper = pred + 1.28 * step_std_err
            
            if all(h >= 0 for h in history):
                lower = max(0.0, lower)
                upper = max(0.0, upper)
                
            mean_fc.append(round(pred, 4))
            lower_fc.append(round(lower, 4))
            upper_fc.append(round(upper, 4))
            
        metrics = self._calculate_metrics(history, mean_fc)
        if fallback_reason:
            metrics["timesfm_status"] = f"Statistical Emulation (Holt-Winters): {fallback_reason}"
        else:
            metrics["timesfm_status"] = "Statistical Emulation (Holt-Winters)"
            
        ascii_chart = self._generate_ascii_chart(history, mean_fc, lower_fc, upper_fc)
        
        return {
            "success": True,
            "engine": "Statistical Emulation (Holt-Winters)",
            "history": history,
            "forecast": mean_fc,
            "lower_bound": lower_fc,
            "upper_bound": upper_fc,
            "metrics": metrics,
            "ascii_chart": ascii_chart
        }

    def _calculate_metrics(self, history: List[float], forecast: List[float]) -> Dict[str, Any]:
        """Calculates rich statistical characteristics of the sequence."""
        n = len(history)
        avg_hist = sum(history) / n
        avg_fc = sum(forecast) / len(forecast)
        
        # Volatility (standard deviation of history)
        var = sum((h - avg_hist)**2 for h in history) / n
        volatility = math.sqrt(var)
        
        # Growth Rate (from last history point to last forecast point)
        start_val = history[-1]
        end_val = forecast[-1]
        if start_val != 0:
            growth_rate = ((end_val - start_val) / abs(start_val)) * 100
        else:
            growth_rate = 0.0
            
        # Volatility percentage
        vol_pct = (volatility / avg_hist * 100) if avg_hist != 0 else 0.0
        
        # Trend classification
        recent_trend = "STABLE"
        if n >= 2:
            change = history[-1] - history[0]
            change_pct = (change / abs(history[0])) if history[0] != 0 else change
            if change_pct > 0.05:
                recent_trend = "UPWARD"
            elif change_pct < -0.05:
                recent_trend = "DOWNWARD"
                
        return {
            "historical_average": round(avg_hist, 4),
            "forecast_average": round(avg_fc, 4),
            "historical_volatility": round(volatility, 4),
            "volatility_percentage": f"{round(vol_pct, 2)}%",
            "projected_growth_rate": f"{round(growth_rate, 2)}%",
            "trend_direction": recent_trend
        }

    def _generate_ascii_chart(self, history: List[float], forecast: List[float], 
                              lower: List[float], upper: List[float]) -> str:
        """Generates a highly-curated, beautiful ASCII chart representing history and predictions."""
        full_series = history + forecast
        full_upper = history + upper
        full_lower = history + lower
        
        # Find min/max boundaries for plotting
        max_val = max(full_upper)
        min_val = min(full_lower)
        val_range = max_val - min_val
        if val_range == 0:
            val_range = 1.0
            
        # Chart Dimensions
        height = 10
        width = len(full_series)
        
        # Render plot grid
        grid = [[" " for _ in range(width)] for _ in range(height)]
        
        def val_to_row(v: float) -> int:
            row = int(((v - min_val) / val_range) * (height - 1))
            # Clip between 0 and height-1, invert because row 0 is top
            return (height - 1) - max(0, min(row, height - 1))
            
        # 1. Plot History points as 'o'
        for i in range(len(history)):
            row = val_to_row(history[i])
            grid[row][i] = "o"
            
        # 2. Plot Quantile Upper/Lower limits as '.'
        for i in range(len(history), width):
            idx = i - len(history)
            row_l = val_to_row(lower[idx])
            row_u = val_to_row(upper[idx])
            
            # Fill the interval with subtle dots/bars
            for r in range(min(row_l, row_u), max(row_l, row_u) + 1):
                grid[r][i] = "░"
                
        # 3. Plot Mean Forecast points as 'x' over the intervals
        for i in range(len(history), width):
            idx = i - len(history)
            row = val_to_row(forecast[idx])
            grid[row][i] = "█"
            
        # Build string output
        lines = []
        # Top border
        lines.append("  " + "┌" + "─" * (width + 2) + "┐")
        
        for r in range(height):
            # Y-axis label (min, mid, max values)
            if r == 0:
                y_val = f"{max_val:7.2f} ┤"
            elif r == height // 2:
                y_val = f"{(min_val + val_range/2):7.2f} ┤"
            elif r == height - 1:
                y_val = f"{min_val:7.2f} ┤"
            else:
                y_val = "        │"
                
            row_str = "".join(grid[r])
            lines.append(f"{y_val}  {row_str}  │")
            
        # Bottom border
        lines.append("  " + "└" + "─" * (width + 2) + "┘")
        
        # X-axis label
        history_labels = "History (o)"
        forecast_labels = "Forecast (█/░)"
        padding = " " * max(1, width - len(history_labels) - len(forecast_labels) - 4)
        lines.append("         " + f"  {history_labels}{padding}{forecast_labels}  ")
        
        return "\n".join(lines)
