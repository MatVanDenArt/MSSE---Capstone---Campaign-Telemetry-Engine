import inspect
import app.services.analytics as analytics
from app.services.llm_rotator import mcp_tools

def test_mcp_schema_parity():
    """
    Asserts that every tool defined in the LLM's mcp_tools schema
    actually exists in analytics.py and that the expected parameters match.
    """
    missing_functions = []
    
    for tool in mcp_tools:
        func_name = tool["name"]
        
        # 1. Assert the function actually exists in analytics.py
        if not hasattr(analytics, func_name):
            missing_functions.append(func_name)
            continue
            
        func = getattr(analytics, func_name)
        
        # 2. Assert the function is callable
        assert callable(func), f"{func_name} is not callable"
        
        # 3. Assert the parameters match the schema
        sig = inspect.signature(func)
        schema_params = tool.get("parameters", {}).get("properties", {}).keys()
        
        # Check if the schema declares a parameter that the function DOES NOT accept
        # Note: Some functions in analytics.py accept campaign_id implicitly from context or explicit args,
        # but if the schema tells the LLM to provide an arg, the python function MUST accept it.
        for param in schema_params:
            assert param in sig.parameters, f"MCP Schema for {func_name} declares parameter '{param}', but the python function does not accept it."

    assert not missing_functions, f"The following MCP tools are missing from analytics.py: {missing_functions}"
