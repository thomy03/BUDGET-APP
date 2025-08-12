#!/usr/bin/env python3
"""
Simple test to isolate Pydantic issues
"""

# Test just the basic model creation
try:
    from pydantic import BaseModel, Field
    from typing import Optional, List, Dict, Any
    
    class SimpleTagRequest(BaseModel):
        """Simple test model"""
        transaction_label: str = Field(min_length=1, max_length=200)
        amount: Optional[float] = None
    
    # Test creating an instance
    request = SimpleTagRequest(
        transaction_label="NETFLIX SARL 12.99",
        amount=12.99
    )
    
    print("✅ Simple Pydantic model test passed")
    print(f"  Request: {request.transaction_label}")
    
except Exception as e:
    print(f"❌ Simple Pydantic model test failed: {e}")
    import traceback
    traceback.print_exc()

# Test importing the problematic router
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    # Just try to import - don't create instances
    from routers.classification import TagSuggestionRequest
    print("✅ Router import test passed")
    
except Exception as e:
    print(f"❌ Router import test failed: {e}")
    import traceback
    traceback.print_exc()