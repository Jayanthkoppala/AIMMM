import httpx
import json
from typing import Dict, Optional
from app.config import settings
from app.models.agent import LLMDecision
from app.utils.logger import logger


async def get_llm_decision(token_a_price: float, token_b_price: float) -> LLMDecision:
    """
    Get trading decision from OpenRouter LLM.
    Returns LLMDecision with action and confidence.
    """
    prompt = f"""You are a crypto trading agent.

Token A price: {token_a_price}
Token B price: {token_b_price}

Rules:
- Only suggest BUY, SELL, or HOLD
- Include confidence from 0 to 1
- No explanations

Respond in JSON:
{{
  "action": "BUY | SELL | HOLD",
  "confidence": number
}}"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/ai-trading-agent",
                    "X-Title": "AI Trading Agent"
                },
                json={
                    "model": settings.OPENROUTER_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract JSON from response
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            
            # Parse JSON response
            try:
                decision_data = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                    decision_data = json.loads(content)
                elif "```" in content:
                    json_start = content.find("```") + 3
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                    decision_data = json.loads(content)
                else:
                    raise ValueError("No valid JSON found in response")
            
            # Validate and create LLMDecision
            action = decision_data.get("action", "HOLD").upper()
            if action not in ["BUY", "SELL", "HOLD"]:
                action = "HOLD"
            
            confidence = float(decision_data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
            
            return LLMDecision(action=action, confidence=confidence)
            
    except httpx.HTTPError as e:
        logger.error(f"OpenRouter API error: {e}", exc_info=True)
        # Fallback to HOLD with low confidence
        return LLMDecision(action="HOLD", confidence=0.3)
    except Exception as e:
        logger.error(f"Error getting LLM decision: {e}", exc_info=True)
        return LLMDecision(action="HOLD", confidence=0.3)

