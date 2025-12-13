"""
Unit tests for FinSage core modules
"""
import pytest
from core.unit_converter import extract_value_and_unit, convert_unit, validate_and_convert_answer
from utils.validators import should_use_web_scraper, validate_ai_response


class TestUnitConverter:
    """Test unit conversion functionality"""
    
    def test_extract_value_and_unit(self):
        """Test extracting numeric values and units from text"""
        # Energy units
        assert extract_value_and_unit("150 MWh") == (150.0, "MWh")
        assert extract_value_and_unit("1,234.56 kWh") == (1234.56, "kWh")
        assert extract_value_and_unit("500MWh") == (500.0, "MWh")  # No space
        
        # Mass units
        assert extract_value_and_unit("100 ton") == (100.0, "ton")
        assert extract_value_and_unit("5,000 kg") == (5000.0, "kg")
        
        # Volume units
        assert extract_value_and_unit("250 m³") == (250.0, "m³")
        assert extract_value_and_unit("1000 litre") == (1000.0, "litre")
        
        # No match
        assert extract_value_and_unit("no numbers here") == (None, None)
    
    def test_convert_unit(self):
        """Test unit conversions"""
        # Energy conversions
        assert convert_unit(150, 'MWh', 'kWh') == 150000
        assert convert_unit(1000, 'kWh', 'MWh') == 1.0
        assert convert_unit(1, 'GWh', 'kWh') == 1000000
        
        # Mass conversions
        assert convert_unit(1, 'ton', 'kg') == 1000
        assert convert_unit(5000, 'kg', 'ton') == 5.0
        
        # Volume conversions
        assert convert_unit(5, 'm³', 'litre') == 5000
        assert convert_unit(1000, 'litre', 'm³') == 1.0
        
        # Same unit
        assert convert_unit(100, 'kWh', 'kWh') == 100
        
        # Unsupported conversion
        assert convert_unit(100, 'kWh', 'kg') is None
    
    def test_validate_and_convert_answer(self):
        """Test automatic answer conversion based on question"""
        # Should convert MWh to kWh
        question = "Elektrik tüketimi kWh cinsinden?"
        answer = "150 MWh"
        result = validate_and_convert_answer(question, answer)
        assert "150,000 kWh" in result
        assert "150 MWh" in result  # Should show source
        
        # No conversion needed
        question = "Elektrik tüketimi kWh cinsinden?"
        answer = "1000 kWh"
        result = validate_and_convert_answer(question, answer)
        assert result == "1000 kWh"


class TestValidators:
    """Test validation utilities"""
    
    def test_should_use_web_scraper(self):
        """Test web scraper trigger logic"""
        # Both responses are insufficient
        assert should_use_web_scraper("bulunamadı", "Veri Yok") == True
        assert should_use_web_scraper("bilgi yok", "mevcut değil") == True
        assert should_use_web_scraper("kısa", "kısa") == True  # Both too short
        
        # Document has info
        assert should_use_web_scraper("Bu dokümanda detaylı bilgi var" * 10, "Veri Yok") == False
        
        # Data has info
        assert should_use_web_scraper("bulunamadı", "Tabloda 150 MWh değeri mevcut") == False
        
        # Both have info
        assert should_use_web_scraper("Dokümanda var" * 10, "Tabloda var" * 10) == False
    
    def test_validate_ai_response_single_choice(self):
        """Test AI response validation for single choice questions"""
        question = {
            "questionId": 1,
            "questionType": "singleChoice",
            "answers": [
                {"answerId": 10, "answerDescription": "Evet"},
                {"answerId": 20, "answerDescription": "Hayır"}
            ]
        }
        
        # Valid response
        ai_result = {"selected_id": 10, "suggested_value": "Evet"}
        validated = validate_ai_response(question, ai_result)
        assert validated["selected_id"] == 10
        
        # Invalid ID but valid text - should auto-fix
        ai_result = {"selected_id": 999, "suggested_value": "Evet"}
        validated = validate_ai_response(question, ai_result)
        assert validated["selected_id"] == 10  # Auto-fixed to correct ID
        
        # Invalid ID and no match - should default to first
        ai_result = {"selected_id": 999, "suggested_value": "Invalid"}
        validated = validate_ai_response(question, ai_result)
        assert validated["selected_id"] == 10  # Defaults to first option
    
    def test_validate_ai_response_multi_choice(self):
        """Test AI response validation for multi choice questions"""
        question = {
            "questionId": 2,
            "questionType": "multiChoice",
            "answers": [
                {"answerId": 1, "answerDescription": "Option 1"},
                {"answerId": 2, "answerDescription": "Option 2"},
                {"answerId": 3, "answerDescription": "Option 3"}
            ]
        }
        
        # Valid response
        ai_result = {"selected_ids": [1, 3]}
        validated = validate_ai_response(question, ai_result)
        assert validated["selected_ids"] == [1, 3]
        
        # Some invalid IDs - should filter them out
        ai_result = {"selected_ids": [1, 999, 3, 888]}
        validated = validate_ai_response(question, ai_result)
        assert validated["selected_ids"] == [1, 3]  # Invalid IDs removed
        
        # All invalid IDs
        ai_result = {"selected_ids": [999, 888]}
        validated = validate_ai_response(question, ai_result)
        assert validated["selected_ids"] == []


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
