import httpx
import json
from typing import Dict, Optional, Any
from app.config import settings
from app.models.agent import LLMDecision
from app.utils.logger import logger


# Models that DON'T support response_format: json_object
# These need special handling with prompt-based JSON extraction
MODELS_WITHOUT_JSON_MODE = {
    "openai/o1",
    "openai/o1-mini", 
    "openai/o3-mini",
    "deepseek/deepseek-r1",
    "deepseek/deepseek-reasoner",
    "qwen/qwq-32b-preview",
    "google/gemini-2.0-flash-thinking-exp",
    "x-ai/grok-2-1212",
    "x-ai/grok-2-vision-1212",
    "anthropic/claude-opus-4.1",
}


def _supports_json_mode(model: str) -> bool:
    """Check if a model supports response_format: json_object"""
    return model not in MODELS_WITHOUT_JSON_MODE


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
        model = settings.OPENROUTER_MODEL
        supports_json = _supports_json_mode(model)
        
        # Build request payload
        request_payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
        }
        
        # Only add response_format for models that support it
        if supports_json:
            request_payload["response_format"] = {"type": "json_object"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/aimmm",
                    "X-Title": "AIMMM"
                },
                json=request_payload,
                timeout=60.0  # Increased timeout for reasoning models
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract JSON from response
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            
            # Parse JSON response - handle various formats
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
                    # Try to find JSON object in text
                    import re
                    json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', content, re.DOTALL)
                    if json_match:
                        decision_data = json.loads(json_match.group())
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


async def get_strategy_decision(
    portfolio_state: Dict[str, Any],
    market_data: Dict[str, Any],
    strategy_config: Dict[str, Any],
    strategy_description: Optional[str] = None,
    llm_model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get trading decision for DEX spot strategy execution.
    
    Args:
        portfolio_state: Current portfolio balances and value
        market_data: OHLCV, technical indicators, sentiment data
        strategy_config: Strategy configuration
        strategy_description: User's strategy description/instructions (used as main prompt)
        llm_model: Optional LLM model override
    
    Returns:
        {
            "action": "BUY" | "SELL" | "HOLD" | "CLOSE_POSITION",
            "token": str (optional),
            "amount_usdc": float (optional),
            "confidence": float,
            "reasoning": str
        }
    """
    try:
        # Log strategy description usage
        if strategy_description:
            logger.info(f"[LLM] Using user's strategy description: {strategy_description[:100]}...")
        else:
            logger.warning("[LLM] No strategy description provided, using default trading approach")
        
        # Extract paper trading config
        paper_config = strategy_config.get('paper_trading_config', {})
        capital_per_trade = paper_config.get('capital_per_trade', 100)
        max_positions = paper_config.get('max_concurrent_positions', 5)
        stop_loss_pct = paper_config.get('stop_loss_pct', 0.05)
        take_profit_pct = paper_config.get('take_profit_pct', 0.10)
        
        # Extract portfolio info
        balances = portfolio_state.get('balances', [])
        total_value = portfolio_state.get('total_value', 0)
        initial_capital = portfolio_state.get('initial_capital', 1000)
        unrealized_pnl = portfolio_state.get('unrealized_pnl', 0)
        
        # Format balances for prompt
        balance_str = "\n".join([
            f"- {b['token_symbol']}: {b['balance']:.4f} (${b['usd_value']:.2f})"
            for b in balances
        ])
        
        # Count active positions (non-USDC)
        active_positions = sum(1 for b in balances if b['token_symbol'] != 'USDC' and b['balance'] > 0)
        
        # Get available USDC
        usdc_balance = next((b['balance'] for b in balances if b['token_symbol'] == 'USDC'), 0)
        
        # Extract market data
        ohlcv_data = market_data.get('ohlcv', '')
        technical_data = market_data.get('technical', '')
        sentiment_data = market_data.get('sentiment', '')
        current_price = market_data.get('current_price', 0)
        token_symbol = market_data.get('token_symbol', 'MOVE')
        
        # Build system prompt with safety rules and context (execution governor)
        system_prompt = f"""You are an execution advisor for DEX spot paper trading. You enforce safety and risk rules while executing the user's trading strategy.

**CURRENT PORTFOLIO:**
{balance_str}
- Total Portfolio Value: ${total_value:.2f}
- Initial Capital: ${initial_capital:.2f}
- Unrealized P&L: ${unrealized_pnl:.2f} ({portfolio_state.get('unrealized_pnl_pct', 0):.2f}%)

**PAPER TRADING PARAMETERS:**
- Available USDC: ${usdc_balance:.2f}
- Capital per trade: ${capital_per_trade}
- Max concurrent positions: {max_positions}
- Current active positions: {active_positions}
- Stop-loss: {stop_loss_pct * 100}%
- Take-profit: {take_profit_pct * 100}%

**CURRENT MARKET ({token_symbol}):**
- Current Price: ${current_price:.6f}

**MARKET DATA:**
HISTORICAL OHLCV:
{ohlcv_data}

TECHNICAL INDICATORS:
{technical_data}

SENTIMENT ANALYSIS:
{sentiment_data}

**SAFETY RULES (MANDATORY):**
1. Minimum confidence for new trades: 0.70
2. Cannot open new positions if active positions >= max positions ({active_positions}/{max_positions})
3. Cannot buy if USDC balance < capital_per_trade (available: ${usdc_balance:.2f})
4. Consider gas costs and slippage on Movement network
5. Always analyze technical indicators and sentiment before making decisions

**OUTPUT FORMAT (JSON only, no markdown, no text outside JSON):**
{{
  "action": "BUY | SELL | HOLD | CLOSE_POSITION",
  "token": "{token_symbol}",
  "amount_usdc": {capital_per_trade},
  "confidence": 0.70-1.0,
  "reasoning": "Detailed explanation covering: 1) Market context, 2) Indicator analysis, 3) Risk assessment, 4) Decision rationale based on the user's strategy"
}}

**CRITICAL:** Follow the USER STRATEGY provided in the user message. Your job is to faithfully execute their strategy while enforcing the safety rules above."""

        # Build user prompt with the user's strategy description as the main instruction
        if strategy_description and strategy_description.strip():
            user_prompt = f"""**YOUR TRADING STRATEGY:**
{strategy_description}

**TASK:**
Execute the strategy above for {token_symbol}. Analyze the market data provided in the system message and make a trading decision that follows your strategy rules.

Provide a detailed analysis in the "reasoning" field covering:
1. Market context: Current price action, trend, volatility
2. Indicator analysis: Which indicators support/oppose this decision (cite specific values)
3. Risk assessment: Position limits, capital availability, stop-loss logic
4. Decision rationale: Why this action fits your strategy and confidence justification

Return ONLY raw JSON (no markdown, no text outside JSON)."""
        else:
            # Fallback if no strategy description provided
            user_prompt = f"""**DEFAULT TRADING APPROACH:**
Analyze the current market conditions for {token_symbol} using the provided technical indicators, sentiment data, and historical price action.

**GUIDELINES:**
- BUY if indicators show bullish signals (RSI < 70, MACD positive, price above moving averages, positive sentiment)
- SELL if indicators show bearish signals (RSI > 70, MACD negative, price below moving averages, negative sentiment)
- HOLD if signals are mixed or unclear
- Minimum confidence: 0.70 for new trades
- Consider risk/reward ratio and position limits

**TASK:**
Make a trading decision based on the market data provided in the system message. Provide detailed reasoning covering market context, indicator analysis, risk assessment, and decision rationale.

Return ONLY raw JSON (no markdown, no text outside JSON)."""
        
        # Call LLM
        model = llm_model or strategy_config.get('llm_provider', settings.OPENROUTER_MODEL)
        supports_json = _supports_json_mode(model)
        
        logger.info(f"[LLM] Using model: {model} (JSON mode: {supports_json})")
        
        # Build request payload
        request_payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
        }
        
        # Only add response_format for models that support it
        if supports_json:
            request_payload["response_format"] = {"type": "json_object"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/aimmm",
                    "X-Title": "AIMMM - Strategy Executor"
                },
                json=request_payload,
                timeout=90.0  # Increased timeout for reasoning models
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract and parse JSON
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            
            try:
                decision_data = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code blocks or text
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
                    # Try to find JSON object in text (for reasoning models)
                    import re
                    json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', content, re.DOTALL)
                    if json_match:
                        decision_data = json.loads(json_match.group())
                    else:
                        raise ValueError("No valid JSON found in response")
            
            # Validate decision
            action = decision_data.get("action", "HOLD").upper()
            if action not in ["BUY", "SELL", "HOLD", "CLOSE_POSITION"]:
                action = "HOLD"
            
            confidence = float(decision_data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
            
            return {
                "action": action,
                "token": decision_data.get("token", token_symbol),
                "amount_usdc": float(decision_data.get("amount_usdc", capital_per_trade)),
                "confidence": confidence,
                "reasoning": decision_data.get("reasoning", "No reasoning provided")
            }
            
    except Exception as e:
        logger.error(f"Error getting strategy decision: {e}", exc_info=True)
        return {
            "action": "HOLD",
            "token": None,
            "amount_usdc": 0,
            "confidence": 0.3,
            "reasoning": f"Error occurred: {str(e)}"
        }

