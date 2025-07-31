"""Wake Window Calculator Tools - Individual Function Tools"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from google.adk.tools import FunctionTool, ToolContext
import json
import os
import sys

# Add parent directory to import knowledge base
sys.path.append(os.path.dirname(__file__))
from knowledge_base_tool import SleepKnowledgeBaseTool
from wake_window_assessment_tool import (
    SleepType, PutDownBehavior, WakeMood, NightSleepPattern,
    assess_wake_window_adjustment, get_baseline_wake_windows
)


# Math calculation tools
def calculate_sleep_duration(
    put_down_time: str, 
    wake_up_time: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Calculate exact duration between put down and wake up times.
    
    Args:
        put_down_time: Time baby was put down (HH:MM format, 24-hour)
        wake_up_time: Time baby woke up (HH:MM format, 24-hour)
        tool_context: Context for storing calculation results
        
    Returns:
        Dictionary with duration in minutes and formatted string
    """
    try:
        # Parse times
        put_down = datetime.strptime(put_down_time, "%H:%M")
        wake_up = datetime.strptime(wake_up_time, "%H:%M")
        
        # Handle day boundary
        if wake_up < put_down:
            wake_up += timedelta(days=1)
        
        # Calculate duration
        duration_seconds = (wake_up - put_down).total_seconds()
        duration_minutes = int(duration_seconds / 60)
        
        # Format result
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        formatted = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"
        
        # Store in context
        tool_context.state["last_sleep_duration"] = {
            "put_down": put_down_time,
            "wake_up": wake_up_time,
            "minutes": duration_minutes,
            "formatted": formatted
        }
        
        return {
            "status": "success",
            "duration_minutes": duration_minutes,
            "formatted": formatted,
            "calculation": f"Sleep from {put_down_time} to {wake_up_time} = {formatted}"
        }
        
    except ValueError as e:
        return {
            "status": "error",
            "error": f"Invalid time format. Please use HH:MM (24-hour format). Error: {str(e)}"
        }


def calculate_next_sleep_time(
    wake_time: str,
    wake_window_minutes: int,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Calculate when next sleep time should be based on wake window.
    
    Args:
        wake_time: Time baby woke up (HH:MM format)
        wake_window_minutes: Length of wake window in minutes
        tool_context: Context for storing results
        
    Returns:
        Dictionary with next sleep time
    """
    try:
        wake = datetime.strptime(wake_time, "%H:%M")
        next_sleep = wake + timedelta(minutes=wake_window_minutes)
        next_sleep_time = next_sleep.strftime("%H:%M")
        
        # Format wake window
        hours = wake_window_minutes // 60
        minutes = wake_window_minutes % 60
        ww_formatted = f"{hours}h {minutes}min" if hours > 0 else f"{minutes}min"
        
        tool_context.state["last_schedule_calculation"] = {
            "wake_time": wake_time,
            "wake_window": wake_window_minutes,
            "next_sleep": next_sleep_time
        }
        
        return {
            "status": "success",
            "next_sleep_time": next_sleep_time,
            "wake_window_formatted": ww_formatted,
            "calculation": f"Wake at {wake_time} + {ww_formatted} = Sleep at {next_sleep_time}"
        }
        
    except ValueError as e:
        return {
            "status": "error",
            "error": f"Invalid time format. Use HH:MM. Error: {str(e)}"
        }


def adjust_wake_window(
    current_window_minutes: int,
    adjustment_minutes: int,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Calculate new wake window after adjustment.
    
    Args:
        current_window_minutes: Current wake window in minutes
        adjustment_minutes: Minutes to adjust (negative to shorten, positive to extend)
        tool_context: Context for storing results
        
    Returns:
        Dictionary with new wake window
    """
    try:
        new_window = current_window_minutes + adjustment_minutes
        
        # Ensure minimum 30 minutes
        if new_window < 30:
            new_window = 30
            
        # Format results
        current_formatted = f"{current_window_minutes // 60}h {current_window_minutes % 60}min" if current_window_minutes >= 60 else f"{current_window_minutes}min"
        new_formatted = f"{new_window // 60}h {new_window % 60}min" if new_window >= 60 else f"{new_window}min"
        
        action = "Extended" if adjustment_minutes > 0 else "Shortened"
        
        tool_context.state["wake_window_adjustment"] = {
            "original": current_window_minutes,
            "adjustment": adjustment_minutes,
            "new": new_window
        }
        
        return {
            "status": "success",
            "original_minutes": current_window_minutes,
            "new_minutes": new_window,
            "original_formatted": current_formatted,
            "new_formatted": new_formatted,
            "calculation": f"{action} {current_formatted} by {abs(adjustment_minutes)}min = {new_formatted}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Calculation error: {str(e)}"
        }


def calculate_daily_schedule(
    wake_time: str,
    wake_windows: List[int],
    nap_count: int,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """Calculate full day schedule based on wake windows.
    
    Args:
        wake_time: Morning wake time (HH:MM)
        wake_windows: List of wake windows in minutes for each period
        nap_count: Number of naps expected
        tool_context: Context for storing results
        
    Returns:
        Dictionary with full day schedule
    """
    try:
        schedule = []
        current_time = datetime.strptime(wake_time, "%H:%M")
        
        # Morning wake
        schedule.append({
            "event": "Morning Wake",
            "time": wake_time
        })
        
        # Calculate naps and bedtime
        for i in range(len(wake_windows)):
            # Calculate next sleep time
            ww_minutes = wake_windows[i]
            sleep_time = current_time + timedelta(minutes=ww_minutes)
            
            if i < nap_count:
                # It's a nap
                schedule.append({
                    "event": f"Nap {i+1}",
                    "time": sleep_time.strftime("%H:%M"),
                    "wake_window": f"{ww_minutes}min"
                })
                
                # Assume average nap duration (will be adjusted based on age)
                nap_duration = 90 if i == 0 else 60  # Longer first nap
                wake_from_nap = sleep_time + timedelta(minutes=nap_duration)
                
                schedule.append({
                    "event": f"Wake from Nap {i+1}",
                    "time": wake_from_nap.strftime("%H:%M"),
                    "duration": f"{nap_duration}min"
                })
                
                current_time = wake_from_nap
            else:
                # It's bedtime
                schedule.append({
                    "event": "Bedtime",
                    "time": sleep_time.strftime("%H:%M"),
                    "wake_window": f"{ww_minutes}min"
                })
                break
        
        tool_context.state["daily_schedule"] = schedule
        
        return {
            "status": "success",
            "schedule": schedule,
            "total_events": len(schedule)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Schedule calculation error: {str(e)}"
        }


# Create FunctionTool instances - ADK gets name and description from function docstrings
sleep_duration_tool = FunctionTool(func=calculate_sleep_duration)
next_sleep_tool = FunctionTool(func=calculate_next_sleep_time)
adjust_window_tool = FunctionTool(func=adjust_wake_window)
daily_schedule_tool = FunctionTool(func=calculate_daily_schedule)

# Assessment tools (from our assessment module)
wake_assessment_tool = FunctionTool(func=assess_wake_window_adjustment)
baseline_windows_tool = FunctionTool(func=get_baseline_wake_windows)

# List of all wake window tools
WAKE_WINDOW_TOOLS = [
    sleep_duration_tool,
    next_sleep_tool,
    adjust_window_tool,
    daily_schedule_tool,
    wake_assessment_tool,
    baseline_windows_tool
]