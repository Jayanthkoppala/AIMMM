import httpx
import json
from typing import Dict, Optional
from app.config import settings
from app.models.agent import LLMDecision
from app.utils.logger import logger


async def get_llm_decision(
    token_a_price: float, 
    token_b_price: float,
    ohlcv_context: Optional[str] = None,
    sentiment_context: Optional[str] = None,
    technical_context: Optional[str] = None
) -> LLMDecision:
    """
    Get trading decision from OpenRouter LLM.
    Returns LLMDecision with action and confidence.
    
    Args:
        token_a_price: Current price of token A
        token_b_price: Current price of token B
        ohlcv_context: Optional formatted OHLCV historical data string
        sentiment_context: Optional formatted sentiment analysis string
        technical_context: Optional formatted technical indicators string
    """
    # Build prompt with available context
    price_info = f"Token A price: {token_a_price}\nToken B price: {token_b_price}"
    
    # Build context sections
    context_sections = []
    if ohlcv_context:
        context_sections.append(f"Historical Market Data:\n{ohlcv_context}")
    if technical_context:
        context_sections.append(f"{technical_context}")
    if sentiment_context:
        context_sections.append(f"{sentiment_context}")
    
    context_text = "\n\n".join(context_sections) if context_sections else None
    
    if context_text:
        prompt = f"""You are an expert crypto trading agent. Analyze the market data and make a trading decision.

Current Prices:
{price_info}

{context_text}

Analysis Guidelines:
- Consider price trends (up/down/sideways) from OHLCV data
- Evaluate technical indicators (RSI, MACD, moving averages, Bollinger Bands)
- Consider sentiment analysis when available
- Look for patterns in the recent candles
- Higher confidence (0.7-1.0) when technical indicators, sentiment, and price action align
- Lower confidence (0.3-0.6) for sideways or volatile markets or conflicting signals
- Very low confidence (0.1-0.3) if data is insufficient
- Sentiment can reinforce or contradict technical signals
- RSI > 70 suggests overbought, RSI < 30 suggests oversold
- MACD crossing above signal is bullish, below is bearish
- Price above moving averages suggests uptrend, below suggests downtrend

Rules:
- Only suggest BUY, SELL, or HOLD
- Include confidence from 0 to 1
- BUY if trend is up, price is near support, and sentiment is bullish
- SELL if trend is down, price is near resistance, and sentiment is bearish
- HOLD if market is sideways, uncertain, or conflicting signals
- No explanations, only JSON response

Respond in JSON:
{{
  "action": "BUY | SELL | HOLD",
  "confidence": number
}}"""
    else:
        prompt = f"""You are a crypto trading agent.

{price_info}

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

