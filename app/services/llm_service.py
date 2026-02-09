"""
LLM Service - OpenAI API Integration
Handles all interactions with OpenAI's API
"""

import json
from typing import Dict, List, Optional, Any
from openai import OpenAI, APIError, APIConnectionError, RateLimitError

from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import (
    LLMError,
    APIError as CustomAPIError,
    ValidationError
)


class LLMService:
    """
    Service for interacting with OpenAI API
    Handles message generation, tool calling, and streaming
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM service
        
        Args:
            api_key: OpenAI API key (defaults to settings)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        
        if not self.api_key:
            raise ValidationError("OPENAI_API_KEY not found in environment")
        
        # Initialize OpenAI client
        try:
            self.client = OpenAI(api_key=self.api_key)
            logger.info("LLMService initialized with OpenAI API")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise LLMError(f"Cannot initialize OpenAI API: {e}")
        
        # Default model
        self.default_model = "gpt-3.5-turbo" 
        self.max_tokens = 2000
    
    def generate_response(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        tools: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Generate a response from OpenAI
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system: System prompt
            model: Model to use (defaults to gpt-4-turbo-preview)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-2 for OpenAI)
            tools: List of tool definitions for function calling
            
        Returns:
            Response dictionary with content and metadata
        """
        try:
            # Use defaults if not specified
            model = model or self.default_model
            max_tokens = max_tokens or self.max_tokens
            
            # Prepare messages with system prompt
            api_messages = []
            
            # Add system message if provided
            if system:
                api_messages.append({
                    "role": "system",
                    "content": system
                })
            
            # Add conversation messages
            api_messages.extend(messages)
            
            # Build API call parameters
            api_params = {
                "model": model,
                "messages": api_messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            # Add tools if provided (OpenAI function calling)
            if tools:
                api_params["tools"] = self._convert_tools_format(tools)
                api_params["tool_choice"] = "auto"
            
            # Log the request
            logger.info(
                "Sending request to OpenAI API",
                extra={
                    "model": model,
                    "message_count": len(api_messages),
                    "has_tools": bool(tools),
                    "max_tokens": max_tokens
                }
            )
            
            # Make API call
            response = self.client.chat.completions.create(**api_params)
            
            # Parse response
            result = self._parse_response(response)
            
            # Log success
            logger.info(
                "Received response from OpenAI API",
                extra={
                    "model": response.model,
                    "finish_reason": response.choices[0].finish_reason,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens
                }
            )
            
            return result
            
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise CustomAPIError(f"Rate limit exceeded: {e}")
        
        except APIConnectionError as e:
            logger.error(f"API connection error: {e}")
            raise CustomAPIError(f"Failed to connect to OpenAI API: {e}")
        
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise CustomAPIError(f"OpenAI API error: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error in LLM service: {e}")
            raise LLMError(f"Unexpected error: {e}")
    
    def _convert_tools_format(self, tools: List[Dict]) -> List[Dict]:
        """
        Convert tools to OpenAI format if needed
        
        Args:
            tools: Tool definitions
            
        Returns:
            OpenAI-formatted tools
        """
        # OpenAI uses "function" type for tools
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": tool
            })
        return openai_tools
    
    def _parse_response(self, response) -> Dict[str, Any]:
        """
        Parse OpenAI API response into standardized format
        
        Args:
            response: Raw API response
            
        Returns:
            Parsed response dictionary
        """
        choice = response.choices[0]
        message = choice.message
        
        result = {
            "id": response.id,
            "model": response.model,
            "role": message.role,
            "content": [],
            "text": "",
            "tool_calls": [],
            "stop_reason": choice.finish_reason,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
        
        # Parse text content
        if message.content:
            result["content"].append({
                "type": "text",
                "text": message.content
            })
            result["text"] = message.content
        
        # Parse tool calls
        if message.tool_calls:
            for tool_call in message.tool_calls:
                tool_call_dict = {
                    "type": "tool_use",
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "input": json.loads(tool_call.function.arguments)
                }
                result["content"].append(tool_call_dict)
                result["tool_calls"].append(tool_call_dict)
        
        return result
    
    def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict],
        system: Optional[str] = None,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Generate response with automatic tool calling loop
        
        Args:
            messages: Conversation messages
            tools: Available tools
            system: System prompt
            max_iterations: Maximum tool calling iterations
            
        Returns:
            Final response after all tool calls
        """
        conversation = messages.copy()
        iteration = 0
        
        logger.info(f"Starting tool calling loop (max {max_iterations} iterations)")
        
        while iteration < max_iterations:
            iteration += 1
            
            # Generate response
            response = self.generate_response(
                messages=conversation,
                system=system,
                tools=tools
            )
            
            # Check if OpenAI wants to use tools
            if not response["tool_calls"]:
                logger.info(f"Tool loop completed in {iteration} iterations")
                return response
            
            # Add assistant's response to conversation
            conversation.append({
                "role": "assistant",
                "content": response["text"],
                "tool_calls": response["tool_calls"]
            })
            
            # Process each tool call
            for tool_call in response["tool_calls"]:
                logger.info(
                    f"Tool call requested: {tool_call['name']}",
                    extra={"tool_input": tool_call['input']}
                )
                
                # Here you would actually execute the tool
                # For now, we'll add a placeholder result
                conversation.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": "Tool execution placeholder"
                })
        
        logger.warning(f"Tool loop exceeded max iterations ({max_iterations})")
        return response
    
    def create_system_prompt(
        self,
        role: str,
        context: Optional[str] = None,
        guidelines: Optional[List[str]] = None
    ) -> str:
        """
        Create a formatted system prompt
        
        Args:
            role: Role description for the agent
            context: Additional context
            guidelines: List of guidelines/instructions
            
        Returns:
            Formatted system prompt
        """
        prompt_parts = [f"You are {role}."]
        
        if context:
            prompt_parts.append(f"\n\nContext:\n{context}")
        
        if guidelines:
            prompt_parts.append("\n\nGuidelines:")
            for i, guideline in enumerate(guidelines, 1):
                prompt_parts.append(f"{i}. {guideline}")
        
        return "\n".join(prompt_parts)
    
    def format_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        Format messages for OpenAI API
        
        Args:
            user_message: Current user message
            conversation_history: Previous conversation messages
            
        Returns:
            Formatted message list
        """
        messages = []
        
        # Add conversation history if provided
        if conversation_history:
            messages.extend(conversation_history)
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        return messages
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text
        (Rough approximation: 1 token ≈ 4 characters)
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def validate_messages(self, messages: List[Dict[str, str]]) -> bool:
        """
        Validate message format
        
        Args:
            messages: Messages to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError if invalid
        """
        if not messages:
            raise ValidationError("Messages cannot be empty")
        
        for i, msg in enumerate(messages):
            if "role" not in msg:
                raise ValidationError(f"Message {i} missing 'role'")
            
            if "content" not in msg and msg["role"] != "tool":
                raise ValidationError(f"Message {i} missing 'content'")
            
            if msg["role"] not in ["user", "assistant", "system", "tool"]:
                raise ValidationError(f"Message {i} has invalid role: {msg['role']}")
        
        return True
    
    def truncate_conversation(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 50000
    ) -> List[Dict[str, str]]:
        """
        Truncate conversation to fit within token limit
        
        Args:
            messages: Conversation messages
            max_tokens: Maximum tokens allowed
            
        Returns:
            Truncated message list
        """
        # Estimate tokens
        total_tokens = sum(
            self.estimate_tokens(json.dumps(msg)) for msg in messages
        )
        
        if total_tokens <= max_tokens:
            return messages
        
        # Keep most recent messages (but preserve system message if present)
        truncated = []
        system_message = None
        
        # Extract system message if present
        if messages and messages[0].get("role") == "system":
            system_message = messages[0]
            messages = messages[1:]
        
        current_tokens = 0
        
        # Add system message tokens
        if system_message:
            current_tokens += self.estimate_tokens(json.dumps(system_message))
        
        # Add messages from most recent
        for msg in reversed(messages):
            msg_tokens = self.estimate_tokens(json.dumps(msg))
            if current_tokens + msg_tokens > max_tokens:
                break
            truncated.insert(0, msg)
            current_tokens += msg_tokens
        
        # Re-add system message at the beginning
        if system_message:
            truncated.insert(0, system_message)
        
        logger.warning(
            f"Conversation truncated from {len(messages)} to {len(truncated)} messages",
            extra={"original_tokens": total_tokens, "max_tokens": max_tokens}
        )
        
        return truncated

# Global instance
_llm_service = None


def get_llm_service() -> LLMService:
    """Get or create global LLMService instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service