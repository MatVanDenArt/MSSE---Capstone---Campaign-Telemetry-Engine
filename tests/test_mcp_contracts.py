"""
Layer 2: MCP contract testing (preventing schema drift).

Architectural purpose:
In an agentic LLM architecture, the model relies on a declarative OpenAPI/JSON schema
(`mcp_tools`) to understand the backend tools it can invoke. 
If a developer alters a Python function signature (e.g. renaming an argument or adding
a mandatory parameter) without synchronizing the schema, the LLM will generate tool calls
that fail at runtime.

This test suite utilizes Python runtime reflection (`inspect.signature`) to programmatically
assert that:
  1. Every tool defined in the schema exists as a callable in `app.services.analytics`.
  2. Every parameter promised in the JSON schema is accepted by the underlying Python function.
  3. No schema drift can pass into production.
"""

import inspect
import app.services.analytics as analytics
from app.services.llm_rotator import mcp_tools

def test_mcp_schema_parity():
    # Programmatically verifies 1:1 parity between the LLM tool declaration schema
    # and the Python analytical service layer.
    
    missing_functions = []
    
    for tool in mcp_tools:
        func_name = tool["name"]
        
        # 1. Assert the function actually exists in analytics.py facade
        if not hasattr(analytics, func_name):
            missing_functions.append(func_name)
            continue
            
        func = getattr(analytics, func_name)
        
        # 2. Assert the exported attribute is an executable callable
        assert callable(func), f"Exported symbol '{func_name}' is not callable"
        
        # 3. Assert parameter signature parity via runtime introspection
        sig = inspect.signature(func)
        schema_params = tool.get("parameters", {}).get("properties", {}).keys()
        
        # Check that any parameter promised to the LLM in the schema is accepted by Python
        for param in schema_params:
            assert param in sig.parameters, (
                f"MCP Schema drift detected: Tool '{func_name}' declares parameter '{param}', "
                f"but the Python function signature in analytics.py does not accept it."
            )

    # Fail the suite if any schema-declared tool is missing from the service layer
    assert not missing_functions, f"The following MCP tools are missing from analytics.py: {missing_functions}"
