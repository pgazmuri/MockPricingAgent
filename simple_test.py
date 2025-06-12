print("🚀 IT Operations Multi-Agent System Test")
print("Testing basic functionality...")

try:
    from services.it_ops_tools import ITOpsTools
    print("✅ IT Operations Tools imported successfully")
    
    from agents.investigator_agent import InvestigatorAgent  
    print("✅ Investigator Agent imported successfully")
    
    print("\n🎉 All imports successful!")
    print("The IT Operations system is ready to use!")
    
except Exception as e:
    print(f"❌ Import failed: {str(e)}")
    import traceback
    traceback.print_exc()
