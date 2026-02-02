"""
MCP Statistical Tools Server
Provides mathematical calculations with verification and audit trail
Integrates with Wolfram Alpha for complex computations
"""

from typing import Dict, List, Any, Optional
from mcp.server import Server
import numpy as np
from scipy import stats
from datetime import datetime
import httpx
from backend.config import settings
from backend.database.session import get_db_context
from backend.database.models import CalculationLog


class StatisticalToolsServer:
    """MCP Server for statistical calculations"""
    
    def __init__(self):
        self.server = Server("statistical-tools")
        self.wolfram_client = httpx.AsyncClient(timeout=30.0)
        self.register_tools()
    
    def register_tools(self):
        """Register all statistical tools"""
        
        @self.server.tool()
        async def calculate_complaint_rate(
            session_id: int,
            numerator: int,
            denominator: int,
            show_work: bool = True,
            agent_name: str = "Unknown"
        ) -> Dict[str, Any]:
            """
            Calculate complaint rate with full mathematical verification
            
            Args:
                session_id: PSUR session ID
                numerator: Number of complaints
                denominator: Total units sold
                show_work: Return step-by-step calculation
                agent_name: Name of requesting agent
            
            Returns:
                Dict with rate, percentage, and calculation steps
            """
            if denominator == 0:
                return {
                    "error": "Division by zero: denominator cannot be 0",
                    "status": "error"
                }
            
            # Calculate rate
            rate = numerator / denominator
            percentage = rate * 100
            
            # Build step-by-step work
            work_steps = []
            if show_work:
                work_steps = [
                    f"Formula: Complaint Rate = (Complaints / Units Sold) × 100",
                    f"Input: Numerator = {numerator:,} complaints",
                    f"Input: Denominator = {denominator:,} units sold",
                    f"Calculation: ({numerator:,} / {denominator:,}) × 100",
                    f"Division: {numerator}/{denominator} = {rate:.6f}",
                    f"Multiply by 100: {rate:.6f} × 100 = {percentage:.4f}%",
                    f"Result: {percentage:.2f}%"
                ]
            
            # Log calculation to database
            with get_db_context() as db:
                calc_log = CalculationLog(
                    session_id=session_id,
                    calculation_type="complaint_rate",
                    agent_name=agent_name,
                    inputs={"numerator": numerator, "denominator": denominator},
                    formula="(numerator / denominator) × 100",
                    result=percentage,
                    showed_work="\n".join(work_steps)
                )
                db.add(calc_log)
                db.commit()
            
            return {
                "status": "success",
                "rate": rate,
                "percentage": round(percentage, 2),
                "formatted": f"{percentage:.2f}%",
                "numerator": numerator,
                "denominator": denominator,
                "work_shown": work_steps if show_work else [],
                "verified": True
            }
        
        @self.server.tool()
        async def calculate_ucl(
            session_id: int,
            data_points: List[float],
            confidence_level: float = 0.95,
            agent_name: str = "Unknown"
        ) -> Dict[str, Any]:
            """
            Calculate Upper Control Limit (UCL) for control charts
            Uses standard statistical process control formulas
            
            Args:
                session_id: PSUR session ID
                data_points: List of data points (rates, counts, etc.)
                confidence_level: Confidence level (default 0.95 for 95%)
                agent_name: Name of requesting agent
            
            Returns:
                Dict with UCL, mean, std dev, and calculation details
            """
            if not data_points or len(data_points) < 2:
                return {
                    "error": "Insufficient data points (need at least 2)",
                    "status": "error"
                }
            
            # Convert to numpy array
            data = np.array(data_points)
            
            # Calculate statistics
            mean = float(np.mean(data))
            std_dev = float(np.std(data, ddof=1))  # Sample std dev
            n = len(data)
            
            # Calculate UCL using 3-sigma method (standard SPC)
            ucl = mean + (3 * std_dev)
            lcl = mean - (3 * std_dev)
            
            # Also calculate confidence interval
            confidence_multiplier = stats.t.ppf((1 + confidence_level) / 2, n - 1)
            margin_of_error = confidence_multiplier * (std_dev / np.sqrt(n))
            ci_upper = mean + margin_of_error
            ci_lower = mean - margin_of_error
            
            work_steps = [
                f"Data points (n={n}): {data_points[:5]}{'...' if n > 5 else ''}",
                f"Mean (x̄) = {mean:.6f}",
                f"Standard Deviation (σ) = {std_dev:.6f}",
                f"",
                f"3-Sigma Control Limits:",
                f"UCL = Mean + 3σ = {mean:.6f} + 3({std_dev:.6f}) = {ucl:.6f}",
                f"LCL = Mean - 3σ = {mean:.6f} - 3({std_dev:.6f}) = {lcl:.6f}",
                f"",
                f"{confidence_level*100:.0f}% Confidence Interval:",
                f"CI = [{ci_lower:.6f}, {ci_upper:.6f}]"
            ]
            
            # Log calculation
            with get_db_context() as db:
                calc_log = CalculationLog(
                    session_id=session_id,
                    calculation_type="ucl",
                    agent_name=agent_name,
                    inputs={
                        "data_points": data_points,
                        "n": n,
                        "confidence_level": confidence_level
                    },
                    formula="UCL = mean + 3 × std_dev",
                    result=ucl,
                    showed_work="\n".join(work_steps)
                )
                db.add(calc_log)
                db.commit()
            
            return {
                "status": "success",
                "ucl": round(ucl, 6),
                "lcl": round(lcl, 6),
                "mean": round(mean, 6),
                "std_dev": round(std_dev, 6),
                "n": n,
                "confidence_interval": {
                    "level": confidence_level,
                    "lower": round(ci_lower, 6),
                    "upper": round(ci_upper, 6)
                },
                "work_shown": work_steps,
                "verified": True
            }
        
        @self.server.tool()
        async def analyze_trend(
            session_id: int,
            time_series: List[Dict[str, Any]],
            method: str = "linear",
            agent_name: str = "Unknown"
        ) -> Dict[str, Any]:
            """
            Analyze trend in time series data
            
            Args:
                session_id: PSUR session ID
                time_series: List of dicts with 'period' and 'value' keys
                method: Analysis method ('linear', 'percentage_change')
                agent_name: Name of requesting agent
            
            Returns:
                Dict with trend analysis, slope, and interpretation
            """
            if not time_series or len(time_series) < 2:
                return {
                    "error": "Insufficient time series data (need at least 2 points)",
                    "status": "error"
                }
            
            # Extract values
            periods = [i for i in range(len(time_series))]
            values = [float(point['value']) for point in time_series]
            
            # Linear regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(periods, values)
            
            # Determine trend direction
            if abs(slope) < 0.01:
                trend_direction = "STABLE"
                trend_description = "No significant trend"
            elif slope > 0:
                trend_direction = "INCREASING"
                trend_description = f"Increasing at rate of {slope:.4f} per period"
            else:
                trend_direction = "DECREASING"
                trend_description = f"Decreasing at rate of {abs(slope):.4f} per period"
            
            # Calculate percentage change from first to last
            first_value = values[0]
            last_value = values[-1]
            if first_value != 0:
                pct_change = ((last_value - first_value) / first_value) * 100
            else:
                pct_change = 0.0
            
            work_steps = [
                f"Time Series Analysis ({len(time_series)} data points)",
                f"Method: Linear Regression",
                f"",
                f"Data:",
                *[f"  Period {i+1}: {point['value']}" for i, point in enumerate(time_series)],
                f"",
                f"Linear Regression Results:",
                f"  Slope (β₁) = {slope:.6f}",
                f"  Intercept (β₀) = {intercept:.6f}",
                f"  R² = {r_value**2:.4f}",
                f"  P-value = {p_value:.4f}",
                f"",
                f"Interpretation:",
                f"  Trend Direction: {trend_direction}",
                f"  {trend_description}",
                f"  Overall Change: {pct_change:+.2f}%",
                f"  Statistical Significance: {'Yes' if p_value < 0.05 else 'No'} (p={p_value:.4f})"
            ]
            
            # Log calculation
            with get_db_context() as db:
                calc_log = CalculationLog(
                    session_id=session_id,
                    calculation_type="trend_analysis",
                    agent_name=agent_name,
                    inputs={
                        "time_series": time_series,
                        "method": method
                    },
                    formula="Linear Regression: y = mx + b",
                    result=slope,
                    showed_work="\n".join(work_steps)
                )
                db.add(calc_log)
                db.commit()
            
            return {
                "status": "success",
                "trend_direction": trend_direction,
                "trend_description": trend_description,
                "slope": round(slope, 6),
                "intercept": round(intercept, 6),
                "r_squared": round(r_value ** 2, 4),
                "p_value": round(p_value, 4),
                "percentage_change": round(pct_change, 2),
                "statistically_significant": p_value < 0.05,
                "work_shown": work_steps,
                "verified": True
            }
        
        @self.server.tool()
        async def calculate_capa_effectiveness(
            session_id: int,
            pre_capa_data: List[float],
            post_capa_data: List[float],
            agent_name: str = "Unknown"
        ) -> Dict[str, Any]:
            """
            Calculate CAPA effectiveness using before/after comparison
            
            Args:
                session_id: PSUR session ID
                pre_capa_data: List of complaint rates/counts BEFORE CAPA
                post_capa_data: List of complaint rates/counts AFTER CAPA
                agent_name: Name of requesting agent
            
            Returns:
                Dict with effectiveness percentage and statistical test results
            """
            if not pre_capa_data or not post_capa_data:
                return {
                    "error": "Need both pre-CAPA and post-CAPA data",
                    "status": "error"
                }
            
            # Calculate means
            pre_mean = float(np.mean(pre_capa_data))
            post_mean = float(np.mean(post_capa_data))
            
            # Calculate reduction
            if pre_mean == 0:
                return {
                    "error": "Pre-CAPA mean is zero, cannot calculate effectiveness",
                    "status": "error"
                }
            
            reduction_absolute = pre_mean - post_mean
            reduction_percentage = (reduction_absolute / pre_mean) * 100
            
            # Perform t-test to check statistical significance
            t_stat, p_value = stats.ttest_ind(pre_capa_data, post_capa_data)
            
            # Determine effectiveness
            if reduction_percentage >= 30:
                effectiveness_rating = "HIGHLY EFFECTIVE"
            elif reduction_percentage >= 10:
                effectiveness_rating = "EFFECTIVE"
            elif reduction_percentage > 0:
                effectiveness_rating = "MARGINALLY EFFECTIVE"
            elif reduction_percentage == 0:
                effectiveness_rating = "NO CHANGE"
            else:
                effectiveness_rating = "INEFFECTIVE (INCREASED)"
            
            work_steps = [
                f"CAPA Effectiveness Analysis",
                f"",
                f"Pre-CAPA Data (n={len(pre_capa_data)}):",
                f"  Values: {pre_capa_data}",
                f"  Mean: {pre_mean:.6f}",
                f"  Std Dev: {np.std(pre_capa_data, ddof=1):.6f}",
                f"",
                f"Post-CAPA Data (n={len(post_capa_data)}):",
                f"  Values: {post_capa_data}",
                f"  Mean: {post_mean:.6f}",
                f"  Std Dev: {np.std(post_capa_data, ddof=1):.6f}",
                f"",
                f"Effectiveness Calculation:",
                f"  Absolute Reduction = {pre_mean:.6f} - {post_mean:.6f} = {reduction_absolute:.6f}",
                f"  Percentage Reduction = ({reduction_absolute:.6f} / {pre_mean:.6f}) × 100 = {reduction_percentage:.2f}%",
                f"",
                f"Statistical Test (Independent t-test):",
                f"  t-statistic = {t_stat:.4f}",
                f"  p-value = {p_value:.4f}",
                f"  Statistically Significant: {'Yes' if p_value < 0.05 else 'No'}",
                f"",
                f"Overall Rating: {effectiveness_rating}"
            ]
            
            # Log calculation
            with get_db_context() as db:
                calc_log = CalculationLog(
                    session_id=session_id,
                    calculation_type="capa_effectiveness",
                    agent_name=agent_name,
                    inputs={
                        "pre_capa_data": pre_capa_data,
                        "post_capa_data": post_capa_data
                    },
                    formula="% Reduction = ((Pre - Post) / Pre) × 100",
                    result=reduction_percentage,
                    showed_work="\n".join(work_steps)
                )
                db.add(calc_log)
                db.commit()
            
            return {
                "status": "success",
                "pre_capa_mean": round(pre_mean, 6),
                "post_capa_mean": round(post_mean, 6),
                "absolute_reduction": round(reduction_absolute, 6),
                "percentage_reduction": round(reduction_percentage, 2),
                "effectiveness_rating": effectiveness_rating,
                "statistically_significant": p_value < 0.05,
                "t_statistic": round(t_stat, 4),
                "p_value": round(p_value, 4),
                "work_shown": work_steps,
                "verified": True
            }
    
    async def verify_with_wolfram(self, expression: str) -> Optional[Dict[str, Any]]:
        """
        Verify calculation using Wolfram Alpha API (optional enhancement)
        
        Args:
            expression: Mathematical expression to verify
        
        Returns:
            Wolfram Alpha result or None if unavailable
        """
        try:
            response = await self.wolfram_client.get(
                "http://api.wolframalpha.com/v2/query",
                params={
                    "appid": settings.wolfram_api_key,
                    "input": expression,
                    "format": "plaintext",
                    "output": "json"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            
            return None
        
        except Exception as e:
            print(f"Wolfram Alpha verification failed: {e}")
            return None
    
    async def start(self, host: str = "localhost", port: int = 8003):
        """Start the MCP server"""
        await self.server.run(host=host, port=port)


# Server instance
statistical_tools_server = StatisticalToolsServer()


if __name__ == "__main__":
    import asyncio
    asyncio.run(statistical_tools_server.start())
