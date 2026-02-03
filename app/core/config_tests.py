"""
Test configuration system
"""

from config import settings

if __name__ == "__main__":
    # Display all settings
    print(settings.display_settings())
    
    # Test validation
    print("\nValidating API Keys...")
    validation = settings.validate_api_keys()
    
    if validation["valid"]:
        print("All API keys are configured!")
    else:
        print("Configuration issues found:")
        for issue in validation["issues"]:
            print(f"   - {issue}")
    
    # Test LLM config
    print("\nLLM Configuration:")
    llm_config = settings.get_llm_config()
    for key, value in llm_config.items():
        if 'key' in key.lower():
            value = "***hidden***"
        print(f"   {key}: {value}")
    
    # Test agent config
    print("\nAgent Configurations:")
    for agent_type in ['planner', 'research', 'verification', 'synthesis', 'reflection']:
        config = settings.get_agent_config(agent_type)
        print(f"   {agent_type}: temp={config['temperature']}, retries={config['max_retries']}")
    
    # Test directory creation
    print("\nDirectories:")
    print(f"   Memory: {settings.MEMORY_DIR}")
    print(f"   Logs: {settings.LOG_DIR}")
    
    print("\nConfiguration system working!")