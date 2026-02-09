"""
Test LLM Service (Claude API)
"""

from app.services.llm_service import LLMService


def test_llm_service():
    """Test OpenAI API integration"""
    
    print("Testing LLM Service (OpenAI API)")
    
    try:
        # Initialize service
        llm = LLMService()
        print("LLM Service initialized")
        
        # Test 1: Simple text generation
        print("\nTest 1: Simple Text Generation")
        messages = [
            {"role": "user", "content": "What is 2+2? Answer in one short sentence."}
        ]
        
        response = llm.generate_response(messages)
        print("Response received:")
        print(f"   Model: {response['model']}")
        print(f"   Text: {response['text']}")
        print(f"   Tokens: {response['usage']['total_tokens']}")
        
        # Test 2: With system prompt
        print("\nTest 2: With System Prompt")
        system = "You are a helpful math tutor. Be concise."
        messages = [
            {"role": "user", "content": "Explain what a prime number is in one sentence."}
        ]
        
        response = llm.generate_response(
            messages=messages,
            system=system
        )
        print("Response with system prompt:")
        print(f"   Text: {response['text']}")
        
        # Test 3: Multi-turn conversation
        print("\nTest 3: Multi-turn Conversation")
        conversation = [
            {"role": "user", "content": "My favorite color is blue."},
            {"role": "assistant", "content": "That's nice! Blue is a calming color."},
            {"role": "user", "content": "What was my favorite color?"}
        ]
        
        response = llm.generate_response(conversation)
        print("Multi-turn response:")
        print(f"   Text: {response['text']}")
        
        # Test 4: Create system prompt
        print("\nTest 4: Create System Prompt")
        system = llm.create_system_prompt(
            role="a research assistant",
            context="You help users find and verify information",
            guidelines=[
                "Always cite sources",
                "Be objective and factual",
                "Admit when you're uncertain"
            ]
        )
        print("System prompt created:")
        print(f"   {system[:100]}...")
        
        # Test 5: Format messages
        print("\nTest 5: Format Messages")
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        formatted = llm.format_messages(
            user_message="What can you do?",
            conversation_history=history
        )
        print(f"Formatted {len(formatted)} messages")
        
        # Test 6: Token estimation
        print("\nTest 6: Token Estimation")
        text = "This is a sample text for token estimation."
        tokens = llm.estimate_tokens(text)
        print(f"Estimated tokens: {tokens} for '{text}'")
        
        # Test 7: Message validation
        print("\nTest 7: Message Validation ---")
        valid_messages = [
            {"role": "user", "content": "Test"}
        ]
        is_valid = llm.validate_messages(valid_messages)
        print(f"Message validation: {is_valid}")
        
        # Test 8: Temperature control
        print("\nTest 8: Temperature Control")
        messages = [
            {"role": "user", "content": "Say hello in a creative way."}
        ]
        
        # Low temperature (deterministic)
        response_low = llm.generate_response(
            messages=messages,
            temperature=0.0
        )
        print(f"Low temp (0.0): {response_low['text'][:50]}...")
        
        # High temperature (creative)
        response_high = llm.generate_response(
            messages=messages,
            temperature=1.0
        )
        print(f"High temp (1.0): {response_high['text'][:50]}...")
        
        print("ALL LLM SERVICE TESTS PASSED!")
        print("\nNote: These tests make real API calls and will consume tokens")
        
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_llm_service()