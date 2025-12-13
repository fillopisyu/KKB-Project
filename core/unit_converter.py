import re
from typing import Tuple, Optional

# Unit conversion mappings
UNIT_CONVERSIONS = {
    # Energy conversions
    'MWh': {'kWh': 1000, 'GWh': 0.001, 'MWh': 1},
    'kWh': {'MWh': 0.001, 'GWh': 0.000001, 'kWh': 1},
    'GWh': {'MWh': 1000, 'kWh': 1000000, 'GWh': 1},
    
    # Mass conversions
    'ton': {'kg': 1000, 'kton': 0.001, 'ton': 1, 't': 1},
    't': {'kg': 1000, 'kton': 0.001, 'ton': 1, 't': 1},
    'kg': {'ton': 0.001, 'kton': 0.000001, 'kg': 1, 't': 0.001},
    'kton': {'ton': 1000, 'kg': 1000000, 'kton': 1},
    
    # Volume conversions
    'm³': {'litre': 1000, 'L': 1000, 'm³': 1, 'm3': 1},
    'm3': {'litre': 1000, 'L': 1000, 'm³': 1, 'm3': 1},
    'litre': {'m³': 0.001, 'L': 1, 'litre': 1, 'm3': 0.001},
    'L': {'m³': 0.001, 'litre': 1, 'L': 1, 'm3': 0.001},
}

# Common unit aliases
UNIT_ALIASES = {
    'megawatt-hour': 'MWh',
    'megawatt hour': 'MWh',
    'kilowatt-hour': 'kWh',
    'kilowatt hour': 'kWh',
    'gigawatt-hour': 'GWh',
    'gigawatt hour': 'GWh',
    'tonne': 'ton',
    'tonnes': 'ton',
    'metric ton': 'ton',
    'liter': 'litre',
    'liters': 'litre',
    'litres': 'litre',
}


def normalize_unit(unit: str) -> str:
    """Normalize unit to standard form."""
    unit_lower = unit.lower().strip()
    return UNIT_ALIASES.get(unit_lower, unit)


def extract_value_and_unit(text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Extract numeric value and unit from text.
    
    Examples:
        "150 MWh" -> (150.0, "MWh")
        "1,234.56 kWh" -> (1234.56, "kWh")
        "500 ton CO2" -> (500.0, "ton")
    
    Args:
        text: Input text containing value and unit
    
    Returns:
        Tuple of (value, unit) or (None, None) if not found
    """
    # Pattern to match number (with optional comma/dot) followed by unit
    # Supports: 150 MWh, 1,234.56 kWh, 500ton, etc.
    pattern = r'([\d,\.]+)\s*([a-zA-Z³₃]+)'
    
    match = re.search(pattern, text)
    if match:
        try:
            # Remove commas and convert to float
            value_str = match.group(1).replace(',', '')
            value = float(value_str)
            unit = match.group(2)
            
            # Normalize unit
            unit = normalize_unit(unit)
            
            return value, unit
        except ValueError:
            return None, None
    
    return None, None


def convert_unit(value: float, from_unit: str, to_unit: str) -> Optional[float]:
    """
    Convert value from one unit to another.
    
    Args:
        value: Numeric value to convert
        from_unit: Source unit
        to_unit: Target unit
    
    Returns:
        Converted value or None if conversion not supported
    """
    # Normalize units
    from_unit = normalize_unit(from_unit)
    to_unit = normalize_unit(to_unit)
    
    # Same unit, no conversion needed
    if from_unit == to_unit:
        return value
    
    # Check if conversion exists
    if from_unit in UNIT_CONVERSIONS:
        if to_unit in UNIT_CONVERSIONS[from_unit]:
            conversion_factor = UNIT_CONVERSIONS[from_unit][to_unit]
            return value * conversion_factor
    
    return None  # Conversion not supported


def validate_and_convert_answer(question_text: str, answer_text: str) -> str:
    """
    Check if question asks for specific unit and convert answer if needed.
    
    Examples:
        Q: "Elektrik tüketimi kWh cinsinden?"
        A: "150 MWh"
        → "150,000 kWh (Kaynak: 150 MWh)"
    
    Args:
        question_text: The question text
        answer_text: The answer text from AI
    
    Returns:
        Converted answer or original if no conversion needed
    """
    if not answer_text or not question_text:
        return answer_text
    
    # Extract unit from question (what user is asking for)
    q_value, q_unit = extract_value_and_unit(question_text)
    
    # If no unit in question, try to find unit keywords
    if not q_unit:
        # Look for unit keywords in question
        for keyword in ['kWh', 'MWh', 'GWh', 'ton', 'kg', 'litre', 'L', 'm³', 'm3']:
            if keyword in question_text:
                q_unit = keyword
                break
    
    # Extract unit from answer
    a_value, a_unit = extract_value_and_unit(answer_text)
    
    # If we have both values and units, and they differ, convert
    if a_value and a_unit and q_unit and a_unit != q_unit:
        converted = convert_unit(a_value, a_unit, q_unit)
        
        if converted is not None:
            # Format with thousand separators
            if converted >= 1000:
                converted_str = f"{converted:,.0f}"
            else:
                converted_str = f"{converted:.2f}".rstrip('0').rstrip('.')
            
            return f"{converted_str} {q_unit} (Kaynak: {a_value} {a_unit})"
    
    return answer_text


def format_number_with_unit(value: float, unit: str) -> str:
    """
    Format number with appropriate precision and unit.
    
    Args:
        value: Numeric value
        unit: Unit string
    
    Returns:
        Formatted string like "1,234.56 kWh"
    """
    if value >= 1000:
        return f"{value:,.0f} {unit}"
    else:
        formatted = f"{value:.2f}".rstrip('0').rstrip('.')
        return f"{formatted} {unit}"
