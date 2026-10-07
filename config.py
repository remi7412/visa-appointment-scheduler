import json
import os

def load_config(path="config.json"):
    if not os.path.exists(path):
        # Fallback to parent directory just in case it's run from the 'dist' folder
        parent_path = os.path.join("..", path)
        if os.path.exists(parent_path):
            path = parent_path
        else:
            raise FileNotFoundError(f"Config file not found: {path}")
        
    with open(path, 'r') as f:
        config = json.load(f)
        
    # Basic Schema Validation
    required_keys = ["chrome", "cities", "dates", "wait_times", "proxies", "telegram"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required key in config.json: {key}")
            
    if not isinstance(config['cities'], list) or len(config['cities']) == 0:
        raise ValueError("'cities' must be a non-empty list.")
        
    if not isinstance(config['dates'], list) or len(config['dates']) == 0:
        raise ValueError("'dates' must be a non-empty list.")
    
    for i, date_obj in enumerate(config['dates']):
        if not isinstance(date_obj, dict):
            raise ValueError(f"Date entry at index {i} must be an object.")
        if "year" not in date_obj or "month" not in date_obj or "range" not in date_obj:
            raise ValueError(f"Date entry at index {i} is missing 'year', 'month', or 'range'.")
        
    return config
