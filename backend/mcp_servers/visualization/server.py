"""
MCP Visualization Server
Generates charts, graphs, and tables for PSUR sections
"""

from typing import Dict, List, Any, Optional
from mcp.server import Server
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import numpy as np
import pandas as pd
from io import BytesIO
import base64
from datetime import datetime


class VisualizationServer:
    """MCP Server for visualization generation"""
    
    def __init__(self):
        self.server = Server("visualization")
        self.register_tools()
        
        # Set matplotlib style
        plt.style.use('seaborn-v0_8-darkgrid')
        plt.rcParams['figure.facecolor'] = 'white'
        plt.rcParams['axes.facecolor'] = '#f8f9fa'
    
    def register_tools(self):
        """Register all visualization tools"""
        
        @self.server.tool()
        async def create_line_chart(
            session_id: int,
            title: str,
            data: List[Dict[str, Any]],
            x_label: str = "Period",
            y_label: str = "Value",
            save_path: Optional[str] = None,
            agent_name: str = "Unknown"
        ) -> Dict[str, Any]:
            """
            Create a line chart for trend analysis
            
            Args:
                session_id: PSUR session ID
                title: Chart title
                data: List of dicts with 'period' and 'value' keys
                x_label: X-axis label
                y_label: Y-axis label
                save_path: Optional path to save chart
                agent_name: Name of requesting agent
            
            Returns:
                Dict with chart path or base64 image
            """
            try:
                # Extract data
                periods = [d['period'] for d in data]
                values = [float(d['value']) for d in data]
                
                # Create figure
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Plot line
                ax.plot(periods, values, marker='o', linewidth=2, markersize=8, 
                       color='#6366f1', label='Trend')
                
                # Styling
                ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
                ax.set_xlabel(x_label, fontsize=12)
                ax.set_ylabel(y_label, fontsize=12)
                ax.grid(True, alpha=0.3)
                ax.legend()
                
                # Add value labels
                for i, (period, value) in enumerate(zip(periods, values)):
                    ax.annotate(f'{value:.2f}', 
                               xy=(i, value),
                               xytext=(0, 10),
                               textcoords='offset points',
                               ha='center',
                               fontsize=9)
                
                plt.tight_layout()
                
                # Save or encode
                if save_path:
                    plt.savefig(save_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    return {
                        "status": "success",
                        "chart_type": "line",
                        "save_path": save_path,
                        "data_points": len(data)
                    }
                else:
                    # Convert to base64
                    buffer = BytesIO()
                    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
                    buffer.seek(0)
                    image_base64 = base64.b64encode(buffer.read()).decode()
                    plt.close()
                    
                    return {
                        "status": "success",
                        "chart_type": "line",
                        "image_base64": image_base64,
                        "data_points": len(data)
                    }
                
            except Exception as e:
                return {
                    "error": f"Failed to create line chart: {str(e)}",
                    "status": "error"
                }
        
        @self.server.tool()
        async def create_bar_chart(
            session_id: int,
            title: str,
            categories: List[str],
            values: List[float],
            x_label: str = "Category",
            y_label: str = "Count",
            save_path: Optional[str] = None,
            agent_name: str = "Unknown"
        ) -> Dict[str, Any]:
            """
            Create a bar chart for categorical data
            
            Args:
                session_id: PSUR session ID
                title: Chart title
                categories: Category names
                values: Values for each category
                x_label: X-axis label
                y_label: Y-axis label
                save_path: Optional path to save chart
                agent_name: Name of requesting agent
            
            Returns:
                Dict with chart path or base64 image
            """
            try:
                # Create figure
                fig, ax = plt.subplots(figsize=(10, 6))
                
                # Create bars
                bars = ax.bar(range(len(categories)), values, color='#8b5cf6', alpha=0.8)
                
                # Styling
                ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
                ax.set_xlabel(x_label, fontsize=12)
                ax.set_ylabel(y_label, fontsize=12)
                ax.set_xticks(range(len(categories)))
                ax.set_xticklabels(categories, rotation=45, ha='right')
                ax.grid(True, alpha=0.3, axis='y')
                
                # Add value labels on bars
                for bar, value in zip(bars, values):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{value:.0f}',
                           ha='center', va='bottom', fontsize=10)
                
                plt.tight_layout()
                
                # Save or encode
                if save_path:
                    plt.savefig(save_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    return {
                        "status": "success",
                        "chart_type": "bar",
                        "save_path": save_path,
                        "categories": len(categories)
                    }
                else:
                    buffer = BytesIO()
                    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
                    buffer.seek(0)
                    image_base64 = base64.b64encode(buffer.read()).decode()
                    plt.close()
                    
                    return {
                        "status": "success",
                        "chart_type": "bar",
                        "image_base64": image_base64,
                        "categories": len(categories)
                    }
                
            except Exception as e:
                return {
                    "error": f"Failed to create bar chart: {str(e)}",
                    "status": "error"
                }
        
        @self.server.tool()
        async def create_control_chart(
            session_id: int,
            title: str,
            data_points: List[float],
            ucl: float,
            lcl: float,
            mean: float,
            save_path: Optional[str] = None,
            agent_name: str = "Unknown"
        ) -> Dict[str, Any]:
            """
            Create a statistical process control chart
            
            Args:
                session_id: PSUR session ID
                title: Chart title
                data_points: Data points to plot
                ucl: Upper Control Limit
                lcl: Lower Control Limit
                mean: Mean value
                save_path: Optional path to save chart
                agent_name: Name of requesting agent
            
            Returns:
                Dict with chart path or base64 image
            """
            try:
                # Create figure
                fig, ax = plt.subplots(figsize=(12, 6))
                
                # Plot data points
                x = range(1, len(data_points) + 1)
                ax.plot(x, data_points, marker='o', linestyle='-', linewidth=1.5,
                       markersize=6, color='#3b82f6', label='Data')
                
                # Plot control limits
                ax.axhline(y=ucl, color='#ef4444', linestyle='--', linewidth=2, label=f'UCL ({ucl:.4f})')
                ax.axhline(y=mean, color='#10b981', linestyle='-', linewidth=2, label=f'Mean ({mean:.4f})')
                ax.axhline(y=lcl, color='#ef4444', linestyle='--', linewidth=2, label=f'LCL ({lcl:.4f})')
                
                # Highlight out-of-control points
                out_of_control = []
                for i, value in enumerate(data_points):
                    if value > ucl or value < lcl:
                        ax.plot(i+1, value, marker='X', markersize=12, color='#ef4444')
                        out_of_control.append(i+1)
                
                # Styling
                ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
                ax.set_xlabel('Sample Number', fontsize=12)
                ax.set_ylabel('Value', fontsize=12)
                ax.grid(True, alpha=0.3)
                ax.legend(loc='best')
                
                plt.tight_layout()
                
                # Save or encode
                if save_path:
                    plt.savefig(save_path, dpi=300, bbox_inches='tight')
                    plt.close()
                    result = {
                        "status": "success",
                        "chart_type": "control_chart",
                        "save_path": save_path,
                        "data_points": len(data_points),
                        "out_of_control_points": out_of_control
                    }
                else:
                    buffer = BytesIO()
                    plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
                    buffer.seek(0)
                    image_base64 = base64.b64encode(buffer.read()).decode()
                    plt.close()
                    
                    result = {
                        "status": "success",
                        "chart_type": "control_chart",
                        "image_base64": image_base64,
                        "data_points": len(data_points),
                        "out_of_control_points": out_of_control
                    }
                
                return result
                
            except Exception as e:
                return {
                    "error": f"Failed to create control chart: {str(e)}",
                    "status": "error"
                }
    
    async def start(self, host: str = "localhost", port: int = 8005):
        """Start the MCP server"""
        await self.server.run(host=host, port=port)


# Server instance
visualization_server = VisualizationServer()


if __name__ == "__main__":
    import asyncio
    asyncio.run(visualization_server.start())
