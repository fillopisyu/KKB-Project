"""
Mathematical calculation tool for accurate numerical operations.
Provides safe expression evaluation and unit conversions.
"""

import ast
import operator
import re
from typing import Union, Dict, Optional
from core.logger import logger


# Safe operators for mathematical expressions
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}

# Common unit conversions
UNIT_CONVERSIONS = {
    # Energy
    ('mwh', 'kwh'): 1000,
    ('kwh', 'wh'): 1000,
    ('gwh', 'mwh'): 1000,
    ('gwh', 'kwh'): 1_000_000,
    
    # Mass
    ('ton', 'kg'): 1000,
    ('kg', 'g'): 1000,
    ('ton', 'g'): 1_000_000,
    ('tonne', 'kg'): 1000,
    ('mt', 'kg'): 1000,  # metric ton
    
    # Volume
    ('m3', 'l'): 1000,
    ('m³', 'l'): 1000,
    ('l', 'ml'): 1000,
    
    # CO2 equivalents
    ('tco2e', 'kgco2e'): 1000,
    ('tco2', 'kgco2'): 1000,
    ('mtco2e', 'tco2e'): 1_000_000,
}


def safe_eval(expression: str) -> Optional[float]:
    """
    Safely evaluate a mathematical expression.
    
    Args:
        expression: Mathematical expression as string (e.g., "24 * 1000")
        
    Returns:
        Result as float, or None if evaluation fails
        
    Example:
        >>> safe_eval("24 * 1000")
        24000.0
        >>> safe_eval("100 / 4 + 5")
        30.0
    """
    try:
        # Remove whitespace and replace common symbols
        expr = expression.strip()
        expr = expr.replace('×', '*').replace('÷', '/')
        expr = expr.replace(',', '')  # Remove thousand separators
        
        # Parse the expression into an AST
        node = ast.parse(expr, mode='eval')
        
        # Evaluate the AST safely
        result = _eval_node(node.body)
        
        logger.info(f"Math evaluation: {expression} = {result}")
        return float(result)
        
    except Exception as e:
        logger.warning(f"Failed to evaluate expression '{expression}': {e}")
        return None


def _eval_node(node):
    """Recursively evaluate AST nodes with only safe operators."""
    if isinstance(node, ast.Num):  # Number
        return node.n
    elif isinstance(node, ast.BinOp):  # Binary operation
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsafe operator: {op_type}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return SAFE_OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):  # Unary operation (e.g., -5)
        op_type = type(node.op)
        if op_type not in SAFE_OPERATORS:
            raise ValueError(f"Unsafe operator: {op_type}")
        operand = _eval_node(node.operand)
        return SAFE_OPERATORS[op_type](operand)
    else:
        raise ValueError(f"Unsupported node type: {type(node)}")


def convert_units(value: float, from_unit: str, to_unit: str) -> Optional[Dict[str, Union[float, str]]]:
    """
    Convert a value from one unit to another.
    
    Args:
        value: Numeric value to convert
        from_unit: Source unit (e.g., "MWh", "ton")
        to_unit: Target unit (e.g., "kWh", "kg")
        
    Returns:
        Dictionary with converted value and explanation, or None if conversion not found
        
    Example:
        >>> convert_units(24, "MWh", "kWh")
        {'value': 24000.0, 'calculation': '24 MWh × 1000 = 24,000 kWh'}
    """
    try:
        # Normalize units to lowercase
        from_unit_norm = from_unit.lower().strip()
        to_unit_norm = to_unit.lower().strip()
        
        # Check if conversion exists
        conversion_key = (from_unit_norm, to_unit_norm)
        
        if conversion_key in UNIT_CONVERSIONS:
            factor = UNIT_CONVERSIONS[conversion_key]
            result = value * factor
            
            # Format the calculation explanation
            calculation = f"{value:,.2f} {from_unit} × {factor:,} = {result:,.2f} {to_unit}"
            
            logger.info(f"Unit conversion: {calculation}")
            
            return {
                'value': result,
                'calculation': calculation,
                'factor': factor
            }
        
        # Try reverse conversion
        reverse_key = (to_unit_norm, from_unit_norm)
        if reverse_key in UNIT_CONVERSIONS:
            factor = UNIT_CONVERSIONS[reverse_key]
            result = value / factor
            
            calculation = f"{value:,.2f} {from_unit} ÷ {factor:,} = {result:,.2f} {to_unit}"
            
            logger.info(f"Unit conversion (reverse): {calculation}")
            
            return {
                'value': result,
                'calculation': calculation,
                'factor': 1/factor
            }
        
        logger.warning(f"No conversion found for {from_unit} to {to_unit}")
        return None
        
    except Exception as e:
        logger.error(f"Unit conversion error: {e}")
        return None


def extract_number_and_unit(text: str) -> Optional[Dict[str, Union[float, str]]]:
    """
    Extract number and unit from text.
    
    Args:
        text: Text containing number and unit (e.g., "24 MWh", "11.932 tCO2e")
        
    Returns:
        Dictionary with number and unit, or None if not found
        
    Example:
        >>> extract_number_and_unit("24 MWh")
        {'number': 24.0, 'unit': 'MWh'}
    """
    try:
        # Pattern to match number (with optional comma/decimal) and unit
        pattern = r'([\d,]+\.?\d*)\s*([a-zA-Z0-9²³]+)'
        match = re.search(pattern, text)
        
        if match:
            number_str = match.group(1).replace(',', '')
            unit = match.group(2)
            
            return {
                'number': float(number_str),
                'unit': unit
            }
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to extract number and unit from '{text}': {e}")
        return None


def calculate_with_context(question: str, context_data: str) -> Optional[Dict[str, Union[float, str]]]:
    """
    Perform calculation based on question context and available data.
    
    Args:
        question: The question being asked
        context_data: Available data from documents/tables
        
    Returns:
        Dictionary with calculation result and explanation
        
    Example:
        >>> calculate_with_context(
        ...     "What is total emissions in kg?",
        ...     "Total emissions: 11.932 tCO2e"
        ... )
        {'result': 11932.0, 'explanation': '11.932 tCO2e × 1000 = 11,932 kgCO2e'}
    """
    try:
        # Extract units from question
        question_lower = question.lower()
        
        # Common patterns for unit requests
        unit_patterns = {
            'kg': r'\bkg\b',
            'kwh': r'\bkwh\b',
            'l': r'\bliter|litre\b',
            'g': r'\bgram\b',
        }
        
        target_unit = None
        for unit, pattern in unit_patterns.items():
            if re.search(pattern, question_lower):
                target_unit = unit
                break
        
        if not target_unit:
            return None
        
        # Extract number and unit from context
        extracted = extract_number_and_unit(context_data)
        if not extracted:
            return None
        
        source_value = extracted['number']
        source_unit = extracted['unit']
        
        # Perform conversion
        conversion = convert_units(source_value, source_unit, target_unit)
        
        if conversion:
            return {
                'result': conversion['value'],
                'explanation': conversion['calculation'],
                'source_value': source_value,
                'source_unit': source_unit,
                'target_unit': target_unit
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Calculation with context failed: {e}")
        return None


# Example usage and tests
if __name__ == "__main__":
    # Test safe_eval
    print("Testing safe_eval:")
    print(f"24 * 1000 = {safe_eval('24 * 1000')}")
    print(f"100 / 4 + 5 = {safe_eval('100 / 4 + 5')}")
    print(f"2 ** 3 = {safe_eval('2 ** 3')}")
    
    # Test convert_units
    print("\nTesting convert_units:")
    result = convert_units(24, "MWh", "kWh")
    print(f"24 MWh to kWh: {result}")
    
    result = convert_units(11.932, "ton", "kg")
    print(f"11.932 ton to kg: {result}")
    
    # Test extract_number_and_unit
    print("\nTesting extract_number_and_unit:")
    result = extract_number_and_unit("24 MWh")
    print(f"Extract from '24 MWh': {result}")
    
    result = extract_number_and_unit("11.932 tCO2e")
    print(f"Extract from '11.932 tCO2e': {result}")
