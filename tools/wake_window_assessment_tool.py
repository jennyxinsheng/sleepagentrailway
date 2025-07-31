"""Wake Window Assessment Tool - Implements the decision tree logic"""

from typing import Dict, Any, Tuple, Optional
from enum import Enum
import json
import os
import sys

# Add parent directory to import knowledge base
sys.path.append(os.path.dirname(__file__))
from knowledge_base_tool import SleepKnowledgeBaseTool

# Enums for sleep assessment
class SleepType(Enum):
    INDEPENDENT = "independent"
    ASSISTED = "assisted"

class PutDownBehavior(Enum):
    CRIES_IMMEDIATELY = "cries_immediately"
    PLAYS_FUSSES_LONG = "plays_fusses_long"
    CALM = "calm"

class WakeMood(Enum):
    CRYING = "crying"
    HAPPY = "happy"
    NEUTRAL = "neutral"

class NightSleepPattern(Enum):
    FREQUENT_WAKINGS = "frequent_wakings"
    SPLIT_NIGHTS = "split_nights"
    NORMAL = "normal"


def assess_wake_window_adjustment(
    window_id: str,
    sleep_type: str,
    putdown_behavior: str,
    time_to_sleep_minutes: int,
    is_bedtime: bool = False,
    wake_mood: str = "neutral",
    nap_duration_minutes: Optional[int] = None,
    night_pattern: str = "normal",
    crying_before_offered: bool = False
) -> Dict[str, Any]:
    """Assess wake window and determine adjustment using decision tree logic.
    
    This implements the exact decision tree provided, returning adjustment recommendations.
    
    Args:
        window_id: Identifier for this window (e.g., "nap1", "bedtime")
        sleep_type: "independent" or "assisted"
        putdown_behavior: "cries_immediately", "plays_fusses_long", or "calm"
        time_to_sleep_minutes: Minutes taken to fall asleep
        is_bedtime: Whether this is bedtime or nap
        wake_mood: "crying", "happy", or "neutral"
        nap_duration_minutes: Duration of nap in minutes (if applicable)
        night_pattern: "frequent_wakings", "split_nights", or "normal"
        crying_before_offered: For assisted sleep, was baby crying before offered
        
    Returns:
        Dictionary with assessment results and recommendations
    """
    try:
        # Convert to enums
        sleep_type_enum = SleepType(sleep_type)
        putdown_enum = PutDownBehavior(putdown_behavior)
        wake_mood_enum = WakeMood(wake_mood)
        night_pattern_enum = NightSleepPattern(night_pattern)
        
        # Initialize return values
        adjustment_minutes = 0
        assessment = "unclear"
        reason = f"{window_id}: incomplete data"
        
        # INDEPENDENT SLEEP DECISION TREE
        if sleep_type_enum == SleepType.INDEPENDENT:
            
            # Cries immediately at putdown → overtired
            if putdown_enum == PutDownBehavior.CRIES_IMMEDIATELY:
                adjustment_minutes = -15
                assessment = "overtired"
                reason = f"{window_id}: crying immediately = overtired"
            
            # Plays/fusses for long time OR takes >20 min → undertired
            elif putdown_enum == PutDownBehavior.PLAYS_FUSSES_LONG or time_to_sleep_minutes > 20:
                adjustment_minutes = 15
                assessment = "undertired"
                reason = f"{window_id}: playing/slow to sleep = undertired"
            
            # Falls asleep within 20 minutes calmly
            elif time_to_sleep_minutes <= 20:
                # Check night sleep patterns for bedtime
                if is_bedtime and night_pattern_enum:
                    if night_pattern_enum == NightSleepPattern.FREQUENT_WAKINGS:
                        adjustment_minutes = -15
                        assessment = "overtired"
                        reason = f"{window_id}: frequent night wakings + crying = overtired"
                    elif night_pattern_enum == NightSleepPattern.SPLIT_NIGHTS:
                        adjustment_minutes = 15
                        assessment = "undertired"
                        reason = f"{window_id}: split nights (happy wake) = undertired"
                    else:
                        adjustment_minutes = 0
                        assessment = "optimal"
                        reason = f"{window_id}: fell asleep calmly <20min"
                
                # Check nap quality for non-bedtime windows
                elif nap_duration_minutes is not None and not is_bedtime:
                    # Short nap (<60 min) + crying wake = overtired
                    if nap_duration_minutes < 60 and wake_mood_enum == WakeMood.CRYING:
                        adjustment_minutes = -15
                        assessment = "overtired"
                        reason = f"{window_id}: short nap + crying = overtired"
                    
                    # Short nap (<60 min) + happy wake = undertired
                    elif nap_duration_minutes < 60 and wake_mood_enum == WakeMood.HAPPY:
                        adjustment_minutes = 15
                        assessment = "undertired"
                        reason = f"{window_id}: short nap + happy = undertired"
                    
                    # Slept for more than an hour independently = optimal
                    elif nap_duration_minutes >= 60:
                        adjustment_minutes = 0
                        assessment = "optimal"
                        reason = f"{window_id}: 60+ min nap = optimal timing"
                else:
                    # Default for independent sleep falling asleep <20min
                    adjustment_minutes = 0
                    assessment = "optimal"
                    reason = f"{window_id}: fell asleep calmly <20min"
        
        # ASSISTED SLEEP DECISION TREE
        elif sleep_type_enum == SleepType.ASSISTED:
            
            # Crying before sleep is offered → overtired
            if crying_before_offered:
                adjustment_minutes = -15
                assessment = "overtired"
                reason = f"{window_id}: crying before offered = overtired"
            
            # Calm and looking around when offered sleep
            else:
                # Check night patterns for bedtime assisted sleep
                if is_bedtime and night_pattern_enum:
                    if night_pattern_enum == NightSleepPattern.FREQUENT_WAKINGS:
                        adjustment_minutes = -15
                        assessment = "overtired"
                        reason = f"{window_id}: frequent night wakings = overtired"
                    elif night_pattern_enum == NightSleepPattern.SPLIT_NIGHTS:
                        adjustment_minutes = 15
                        assessment = "undertired"
                        reason = f"{window_id}: split nights = undertired"
                
                # Fell asleep in <15 minutes = perfect window
                if time_to_sleep_minutes < 15:
                    adjustment_minutes = 0
                    assessment = "optimal"
                    reason = f"{window_id}: calm + quick sleep = perfect window"
                
                # Taking >20 minutes to fall asleep = undertired
                elif time_to_sleep_minutes > 20:
                    adjustment_minutes = 15
                    assessment = "undertired"
                    reason = f"{window_id}: calm but slow sleep = undertired"
                
                # 15-20 minutes
                else:
                    adjustment_minutes = 0
                    assessment = "optimal"
                    reason = f"{window_id}: calm + reasonable time = good window"
        
        # Build comprehensive response
        return {
            "status": "success",
            "window_id": window_id,
            "assessment": assessment,
            "adjustment_minutes": adjustment_minutes,
            "reason": reason,
            "action": "shorten" if adjustment_minutes < 0 else "extend" if adjustment_minutes > 0 else "maintain",
            "recommendation": f"{'Shorten' if adjustment_minutes < 0 else 'Extend' if adjustment_minutes > 0 else 'Maintain'} {window_id} wake window by {abs(adjustment_minutes)} minutes",
            "details": {
                "sleep_type": sleep_type,
                "putdown_behavior": putdown_behavior,
                "time_to_sleep": time_to_sleep_minutes,
                "is_bedtime": is_bedtime,
                "wake_mood": wake_mood,
                "nap_duration": nap_duration_minutes,
                "night_pattern": night_pattern,
                "crying_before_offered": crying_before_offered
            }
        }
        
    except ValueError as e:
        return {
            "status": "error",
            "error": f"Invalid input value: {str(e)}",
            "window_id": window_id
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Assessment error: {str(e)}",
            "window_id": window_id
        }


def get_baseline_wake_windows(age_months: int) -> Dict[str, Any]:
    """Get age-appropriate baseline wake windows from knowledge base.
    
    Args:
        age_months: Child's age in months
        
    Returns:
        Dictionary with baseline wake window information
    """
    try:
        kb = SleepKnowledgeBaseTool()
        
        # Determine age range string
        if age_months <= 3:
            age_str = "0-3 months"
        elif age_months == 4:
            age_str = "4 months"
        elif age_months == 5:
            age_str = "5 months"
        elif age_months == 6:
            age_str = "6 months"
        elif age_months == 7:
            age_str = "7 months"
        elif age_months == 8:
            age_str = "8 months"
        elif age_months == 9:
            age_str = "9 months"
        elif age_months <= 12:
            age_str = "10-12 months"
        elif age_months <= 15:
            age_str = "12-15 months"
        elif age_months <= 18:
            age_str = "15-18 months"
        elif age_months <= 24:
            age_str = "18-24 months"
        else:
            age_str = "24+ months"
        
        # Get data from knowledge base
        age_data = kb.get_age_specific_info(age_str)
        
        if age_data and age_data['wake_windows']:
            wake_window_str = age_data['wake_windows']['wake_window']
            naps = age_data['wake_windows']['naps']
            
            # Parse wake window range
            if '-' in wake_window_str:
                parts = wake_window_str.replace(' minutes', '').split('-')
                min_minutes = int(parts[0])
                max_minutes = int(parts[1])
            else:
                # Single value
                minutes = int(wake_window_str.replace(' minutes', ''))
                min_minutes = max_minutes = minutes
            
            return {
                "status": "success",
                "age_months": age_months,
                "age_range": age_str,
                "wake_window_range": wake_window_str,
                "min_minutes": min_minutes,
                "max_minutes": max_minutes,
                "average_minutes": (min_minutes + max_minutes) // 2,
                "number_of_naps": naps,
                "source": "sleep_knowledge_base"
            }
        else:
            return {
                "status": "error",
                "error": f"No wake window data found for {age_months} months",
                "age_months": age_months
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": f"Error retrieving baseline data: {str(e)}",
            "age_months": age_months
        }