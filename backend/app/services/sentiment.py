"""
Sentiment Analysis Service - Grok AI Integration
Analyzes social media and market sentiment for cryptocurrency tokens.
Uses database cache - only fetches from API if data is older than 24 hours.
"""
import httpx
import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from app.config import settings
from app.utils.logger import logger
from app.utils.database import db_connection


class GrokSentimentClient:
    """Client for Grok AI sentiment analysis"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GROK_API_KEY", None)
        self.base_url = "https://api.x.ai/v1"
        self.model = "grok-3"
        self.max_tokens = 1000
        self.temperature = 0.1
        self.timeout = 30
        
        if not self.api_key:
            logger.warning("GROK_API_KEY not set - sentiment analysis will use fallback")
    
    async def get_token_sentiment(
        self, 
        tokens: List[Dict[str, str]], 
        timeframe: str = "24h"
    ) -> Dict[str, Any]:
        """
        Get sentiment analysis for specified tokens using Grok AI
        
        Args:
            tokens: List of dicts with 'symbol' and 'address' keys
            timeframe: Time period for analysis (default: "24h")
        
        Returns:
            Dictionary with sentiment analysis results
        """
        if not self.api_key:
            return self._get_fallback_sentiment(tokens)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Build token list for prompt
        token_list = ", ".join([f"{t['symbol']} ({t['address']})" for t in tokens])
        token_a_symbol_lower = tokens[0]['symbol'].lower()
        token_b_symbol_lower = tokens[1]['symbol'].lower() if len(tokens) > 1 else 'token2'
        
        prompt = f"""Analyze the current social media sentiment for these cryptocurrency tokens over the last {timeframe}: {token_list}

For each token, provide a JSON object with this exact structure (use the token symbol in lowercase as the key):
{{
  "{token_a_symbol_lower}": {{
    "sentiment_score": <number between -1 and 1>,
    "sentiment_label": "<bullish|bearish|neutral>",
    "confidence": <number between 0 and 1>,
    "key_factors": ["<factor1>", "<factor2>", "<factor3>"],
    "social_volume": <integer>,
    "mentions_24h": <integer>,
    "dominant_emotion": "<emotion>"
  }},
  "{token_b_symbol_lower}": {{
    "sentiment_score": <number between -1 and 1>,
    "sentiment_label": "<bullish|bearish|neutral>",
    "confidence": <number between 0 and 1>,
    "key_factors": ["<factor1>", "<factor2>", "<factor3>"],
    "social_volume": <integer>,
    "mentions_24h": <integer>,
    "dominant_emotion": "<emotion>"
  }}
}}

Return ONLY valid JSON, no other text."""
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert cryptocurrency sentiment analyst. You MUST respond with valid JSON only. Analyze social media sentiment for crypto tokens based on community discussions, social media posts, and market chatter."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"}
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract the content from the response
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '{}')
                
                logger.debug(f"Grok API response content (first 500 chars): {content[:500]}")
                
                # Try to parse the JSON response
                try:
                    # First try direct JSON parsing
                    sentiment_data = json.loads(content)
                    
                    # Validate that we have the expected structure
                    if isinstance(sentiment_data, dict) and len(sentiment_data) > 0:
                        # Check if keys match our token symbols (case-insensitive)
                        token_symbols_lower = [t['symbol'].lower() for t in tokens]
                        found_keys = [k.lower() for k in sentiment_data.keys()]
                        
                        # If we found matching keys, return the data
                        if any(key in found_keys for key in token_symbols_lower):
                            logger.info(f"Successfully parsed Grok response with keys: {list(sentiment_data.keys())}")
                            return sentiment_data
                        else:
                            logger.warning(f"Grok response keys {list(sentiment_data.keys())} don't match expected tokens {token_symbols_lower}")
                            # Try to extract data anyway - maybe format is different
                            return self._normalize_response(sentiment_data, tokens)
                    else:
                        logger.warning("Grok response is not a valid dict or is empty")
                        return self._parse_text_response(content, tokens)
                        
                except json.JSONDecodeError as je:
                    logger.warning(f"JSON decode error: {je}. Attempting to extract JSON from text...")
                    # Try to extract JSON from markdown code blocks or text
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start != -1 and json_end > json_start:
                        try:
                            json_str = content[json_start:json_end]
                            sentiment_data = json.loads(json_str)
                            logger.info("Successfully extracted JSON from text response")
                            return self._normalize_response(sentiment_data, tokens)
                        except:
                            pass
                    
                    # If JSON parsing fails, parse the text response
                    logger.info("Falling back to text parsing")
                    return self._parse_text_response(content, tokens)
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error in Grok sentiment analysis: {e.response.status_code} - {e.response.text[:200]}")
            return self._get_fallback_sentiment(tokens)
        except httpx.RequestError as e:
            logger.error(f"Request error in Grok sentiment analysis: {e}")
            return self._get_fallback_sentiment(tokens)
        except Exception as e:
            logger.error(f"Error in Grok sentiment analysis: {e}", exc_info=True)
            return self._get_fallback_sentiment(tokens)
    
    def _normalize_response(
        self,
        sentiment_data: Dict[str, Any],
        tokens: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Normalize Grok response to expected format."""
        normalized = {}
        token_symbols_lower = [t['symbol'].lower() for t in tokens]
        
        # Try to find matching keys (case-insensitive)
        for token in tokens:
            symbol_lower = token['symbol'].lower()
            found_data = None
            
            # Try exact match first
            if symbol_lower in sentiment_data:
                found_data = sentiment_data[symbol_lower]
            else:
                # Try case-insensitive match
                for key, value in sentiment_data.items():
                    if key.lower() == symbol_lower:
                        found_data = value
                        break
                
                # If still not found, try to get first dict value if structure is different
                if not found_data and isinstance(sentiment_data, dict):
                    # Maybe the response has a different structure
                    for key, value in sentiment_data.items():
                        if isinstance(value, dict) and 'sentiment_score' in value:
                            # This might be our token data
                            found_data = value
                            break
            
            # Normalize the data structure
            if found_data and isinstance(found_data, dict):
                normalized[symbol_lower] = {
                    "sentiment_score": float(found_data.get('sentiment_score', 0.0)),
                    "sentiment_label": str(found_data.get('sentiment_label', 'neutral')).lower(),
                    "confidence": float(found_data.get('confidence', 0.5)),
                    "key_factors": found_data.get('key_factors', []) if isinstance(found_data.get('key_factors'), list) else [],
                    "social_volume": int(found_data.get('social_volume', 0)),
                    "mentions_24h": int(found_data.get('mentions_24h', 0)),
                    "dominant_emotion": str(found_data.get('dominant_emotion', 'neutral')),
                    "token_address": token['address']
                }
            else:
                # If we can't find the data, use fallback
                normalized[symbol_lower] = {
                    "sentiment_score": 0.0,
                    "sentiment_label": "neutral",
                    "confidence": 0.3,
                    "key_factors": ["Unable to parse response format"],
                    "social_volume": 0,
                    "mentions_24h": 0,
                    "dominant_emotion": "neutral",
                    "token_address": token['address']
                }
        
        return normalized
    
    def _parse_text_response(
        self, 
        content: str, 
        tokens: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Parse text response from Grok AI when JSON parsing fails"""
        logger.warning(f"Parsing text response from Grok AI (JSON parsing failed). Content length: {len(content)}")
        logger.debug(f"Response content (first 1000 chars): {content[:1000]}")
        
        result = {}
        content_lower = content.lower()
        
        for token in tokens:
            symbol = token['symbol'].lower()
            symbol_upper = token['symbol'].upper()
            
            # Try to find token-specific sentiment in the text
            token_section = ""
            # Look for sections mentioning this token
            token_mentions = [
                f"{symbol}",
                f"{symbol_upper}",
                f"{token['symbol']}",
                token['address'][:20]  # First part of address
            ]
            
            for mention in token_mentions:
                if mention.lower() in content_lower:
                    # Try to extract context around the mention
                    idx = content_lower.find(mention.lower())
                    if idx != -1:
                        start = max(0, idx - 200)
                        end = min(len(content), idx + 500)
                        token_section = content_lower[start:end]
                        break
            
            # Use token-specific section if found, otherwise use full content
            search_text = token_section if token_section else content_lower
            
            # Count positive and negative indicators
            positive_indicators = ['bull', 'bullish', 'positive', 'up', 'moon', 'buy', 'strong', 'gains', 'pump', 'success', 'growth', 'rising', 'optimistic']
            negative_indicators = ['bear', 'bearish', 'negative', 'down', 'dump', 'sell', 'weak', 'losses', 'crash', 'risk', 'declining', 'pessimistic', 'drop']
            
            pos_count = sum(1 for indicator in positive_indicators if indicator in search_text)
            neg_count = sum(1 for indicator in negative_indicators if indicator in search_text)
            
            # Try to extract numeric sentiment scores if mentioned
            score_patterns = [
                rf'{symbol}.*sentiment.*?(-?\d+\.?\d*)',
                rf'sentiment.*?{symbol}.*?(-?\d+\.?\d*)',
                rf'{symbol}.*?score.*?(-?\d+\.?\d*)',
            ]
            
            extracted_score = None
            for pattern in score_patterns:
                match = re.search(pattern, search_text, re.IGNORECASE)
                if match:
                    try:
                        extracted_score = float(match.group(1))
                        extracted_score = max(-1.0, min(1.0, extracted_score))  # Clamp to -1 to 1
                        break
                    except:
                        pass
            
            # Calculate sentiment score (-1 to 1)
            if extracted_score is not None:
                sentiment_score = extracted_score
            elif pos_count + neg_count > 0:
                sentiment_score = (pos_count - neg_count) / (pos_count + neg_count)
            else:
                sentiment_score = 0.0
            
            # Determine sentiment label
            if sentiment_score > 0.2:
                sentiment_label = "bullish"
            elif sentiment_score < -0.2:
                sentiment_label = "bearish"
            else:
                sentiment_label = "neutral"
            
            # Extract key factors (look for lists or bullet points)
            factors = []
            factor_patterns = [
                rf'{symbol}.*?factor[s]?[:\-]\s*(.+?)(?:\n|$)',
                rf'factor[s]?.*?{symbol}[:\-]\s*(.+?)(?:\n|$)',
            ]
            for pattern in factor_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                if matches:
                    factors.extend([m.strip() for m in matches[:3]])
            
            if not factors:
                factors = [f"Based on text analysis for {token['symbol']}"]
            
            result[symbol] = {
                "sentiment_score": round(sentiment_score, 2),
                "sentiment_label": sentiment_label,
                "confidence": 0.5 if extracted_score is None else 0.7,  # Higher confidence if we extracted a score
                "key_factors": factors[:3],  # Limit to 3 factors
                "social_volume": 100,  # Default volume
                "mentions_24h": 50,    # Default mentions
                "dominant_emotion": "mixed" if abs(sentiment_score) < 0.3 else ("positive" if sentiment_score > 0 else "negative"),
                "token_address": token['address']
            }
        
        logger.info(f"Parsed text response: {[(k, v.get('sentiment_score'), v.get('sentiment_label')) for k, v in result.items()]}")
        return result
    
    def _get_fallback_sentiment(
        self, 
        tokens: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Return fallback sentiment data when API fails"""
        logger.warning("Using fallback sentiment data due to API error or missing key")
        
        result = {}
        for token in tokens:
            result[token['symbol'].lower()] = {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "confidence": 0.3,
                "key_factors": ["No data available - API error or missing key"],
                "social_volume": 0,
                "mentions_24h": 0,
                "dominant_emotion": "neutral",
                "token_address": token['address']
            }
        
        return result


class SentimentAnalyzer:
    """Main sentiment analysis service - uses database cache (24h)"""
    
    def __init__(self, grok_api_key: Optional[str] = None):
        self.grok_client = GrokSentimentClient(grok_api_key)
    
    def _get_sentiment_from_db(
        self,
        token_a_address: str,
        token_b_address: str
    ) -> Optional[Dict[str, Any]]:
        """Get sentiment from database if it exists and is less than 24 hours old."""
        if not db_connection.pool:
            return None
        
        try:
            query = """
                SELECT 
                    token_a_symbol, token_b_symbol,
                    token_a_sentiment_score, token_a_sentiment_label, token_a_confidence,
                    token_a_key_factors, token_a_social_volume, token_a_mentions_24h, token_a_dominant_emotion,
                    token_b_sentiment_score, token_b_sentiment_label, token_b_confidence,
                    token_b_key_factors, token_b_social_volume, token_b_mentions_24h, token_b_dominant_emotion,
                    timeframe, analyzed_at
                FROM sentiment_analysis
                WHERE token_a_address = %s
                AND token_b_address = %s
                AND analyzed_at >= NOW() - INTERVAL '24 hours'
                ORDER BY analyzed_at DESC
                LIMIT 1
            """
            result = db_connection.execute_query(
                query,
                (token_a_address, token_b_address),
                fetch_one=True
            )
            
            if not result:
                return None
            
            # Parse key_factors from JSONB
            token_a_factors = result.get('token_a_key_factors', [])
            token_b_factors = result.get('token_b_key_factors', [])
            if isinstance(token_a_factors, str):
                try:
                    token_a_factors = json.loads(token_a_factors)
                except:
                    token_a_factors = []
            if isinstance(token_b_factors, str):
                try:
                    token_b_factors = json.loads(token_b_factors)
                except:
                    token_b_factors = []
            
            return {
                "token_a": {
                    "token_symbol": result.get('token_a_symbol', 'A'),
                    "token_address": token_a_address,
                    "sentiment_score": float(result.get('token_a_sentiment_score', 0.0)),
                    "sentiment_label": result.get('token_a_sentiment_label', 'neutral'),
                    "confidence": float(result.get('token_a_confidence', 0.5)),
                    "key_factors": token_a_factors if isinstance(token_a_factors, list) else [],
                    "social_volume": int(result.get('token_a_social_volume', 0)),
                    "mentions_24h": int(result.get('token_a_mentions_24h', 0)),
                    "dominant_emotion": result.get('token_a_dominant_emotion', 'neutral')
                },
                "token_b": {
                    "token_symbol": result.get('token_b_symbol', 'B'),
                    "token_address": token_b_address,
                    "sentiment_score": float(result.get('token_b_sentiment_score', 0.0)),
                    "sentiment_label": result.get('token_b_sentiment_label', 'neutral'),
                    "confidence": float(result.get('token_b_confidence', 0.5)),
                    "key_factors": token_b_factors if isinstance(token_b_factors, list) else [],
                    "social_volume": int(result.get('token_b_social_volume', 0)),
                    "mentions_24h": int(result.get('token_b_mentions_24h', 0)),
                    "dominant_emotion": result.get('token_b_dominant_emotion', 'neutral')
                },
                "timeframe": result.get('timeframe', '24h'),
                "timestamp": result.get('analyzed_at').isoformat() if result.get('analyzed_at') else datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.debug(f"Error fetching sentiment from database: {e}")
            return None
    
    def _store_sentiment_in_db(
        self,
        token_a_address: str,
        token_b_address: str,
        token_a_symbol: Optional[str],
        token_b_symbol: Optional[str],
        sentiment_data: Dict[str, Any]
    ) -> bool:
        """Store sentiment analysis in database."""
        if not db_connection.pool:
            return False
        
        try:
            token_a = sentiment_data.get('token_a', {})
            token_b = sentiment_data.get('token_b', {})
            
            query = """
                INSERT INTO sentiment_analysis (
                    token_a_address, token_b_address,
                    token_a_symbol, token_b_symbol,
                    token_a_sentiment_score, token_a_sentiment_label, token_a_confidence,
                    token_a_key_factors, token_a_social_volume, token_a_mentions_24h, token_a_dominant_emotion,
                    token_b_sentiment_score, token_b_sentiment_label, token_b_confidence,
                    token_b_key_factors, token_b_social_volume, token_b_mentions_24h, token_b_dominant_emotion,
                    timeframe, analyzed_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, NOW()
                )
                ON CONFLICT (token_a_address, token_b_address, analyzed_at) DO NOTHING
            """
            
            params = (
                token_a_address, token_b_address,
                token_a_symbol, token_b_symbol,
                token_a.get('sentiment_score', 0.0),
                token_a.get('sentiment_label', 'neutral'),
                token_a.get('confidence', 0.5),
                json.dumps(token_a.get('key_factors', [])),
                token_a.get('social_volume', 0),
                token_a.get('mentions_24h', 0),
                token_a.get('dominant_emotion', 'neutral'),
                token_b.get('sentiment_score', 0.0),
                token_b.get('sentiment_label', 'neutral'),
                token_b.get('confidence', 0.5),
                json.dumps(token_b.get('key_factors', [])),
                token_b.get('social_volume', 0),
                token_b.get('mentions_24h', 0),
                token_b.get('dominant_emotion', 'neutral'),
                sentiment_data.get('timeframe', '24h')
            )
            
            result = db_connection.execute_query(query, params, fetch_all=False)
            return result is not None
            
        except Exception as e:
            logger.error(f"Error storing sentiment in database: {e}", exc_info=True)
            return False
    
    async def analyze_token_pair_sentiment(
        self,
        token_a_address: str,
        token_b_address: str,
        token_a_symbol: Optional[str] = None,
        token_b_symbol: Optional[str] = None,
        timeframe: str = "24h"
    ) -> Dict[str, Any]:
        """
        Perform sentiment analysis on a token pair.
        Checks database first (24h cache), only calls API if needed.
        
        Args:
            token_a_address: Address of token A
            token_b_address: Address of token B
            token_a_symbol: Optional symbol for token A (for better analysis)
            token_b_symbol: Optional symbol for token B (for better analysis)
            timeframe: Time period for analysis (default: "24h")
        
        Returns:
            Dictionary with sentiment analysis for both tokens
        """
        # First, check database for recent sentiment (within 24 hours)
        db_sentiment = self._get_sentiment_from_db(token_a_address, token_b_address)
        if db_sentiment:
            logger.info(f"Using cached sentiment from database for {token_a_symbol or token_a_address[:8]}/{token_b_symbol or token_b_address[:8]}")
            return db_sentiment
        
        # No recent sentiment in DB, fetch from API
        # Use symbols if provided, otherwise use address prefixes
        token_a_symbol = token_a_symbol or token_a_address[:8]
        token_b_symbol = token_b_symbol or token_b_address[:8]
        
        tokens = [
            {
                "symbol": token_a_symbol.upper(),
                "address": token_a_address
            },
            {
                "symbol": token_b_symbol.upper(),
                "address": token_b_address
            }
        ]
        
        logger.info(f"Fetching new sentiment from API for token pair: {token_a_symbol}/{token_b_symbol}")
        
        # Get sentiment from Grok AI
        grok_sentiment = await self.grok_client.get_token_sentiment(tokens, timeframe)
        
        # Process the results
        processed_results = {}
        for token in tokens:
            symbol_lower = token['symbol'].lower()
            token_sentiment = grok_sentiment.get(symbol_lower, {})
            
            processed_results[symbol_lower] = {
                "sentiment_score": token_sentiment.get('sentiment_score', 0.0),
                "sentiment_label": token_sentiment.get('sentiment_label', 'neutral'),
                "confidence": token_sentiment.get('confidence', 0.5),
                "key_factors": token_sentiment.get('key_factors', ['No specific factors identified']),
                "social_volume": token_sentiment.get('social_volume', 0),
                "mentions_24h": token_sentiment.get('mentions_24h', 0),
                "dominant_emotion": token_sentiment.get('dominant_emotion', 'neutral'),
                "token_address": token['address'],
                "token_symbol": token['symbol']
            }
        
        # Create comprehensive response
        response = {
            "token_a": processed_results.get(token_a_symbol.lower(), {}),
            "token_b": processed_results.get(token_b_symbol.lower(), {}),
            "timeframe": timeframe,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Store in database for future use
        self._store_sentiment_in_db(
            token_a_address=token_a_address,
            token_b_address=token_b_address,
            token_a_symbol=token_a_symbol,
            token_b_symbol=token_b_symbol,
            sentiment_data=response
        )
        
        logger.info("Sentiment analysis completed and stored in database")
        return response
    
    async def format_sentiment_for_llm(
        self,
        sentiment_data: Dict[str, Any]
    ) -> str:
        """
        Format sentiment data as a string for LLM context
        
        Args:
            sentiment_data: Result from analyze_token_pair_sentiment
        
        Returns:
            Formatted string for LLM prompt
        """
        token_a = sentiment_data.get('token_a', {})
        token_b = sentiment_data.get('token_b', {})
        
        lines = [
            "Sentiment Analysis:",
            f"Token A ({token_a.get('token_symbol', 'A')}):",
            f"  - Sentiment: {token_a.get('sentiment_label', 'neutral').upper()} (score: {token_a.get('sentiment_score', 0.0):.2f})",
            f"  - Confidence: {token_a.get('confidence', 0.5):.2f}",
            f"  - Key Factors: {', '.join(token_a.get('key_factors', [])[:3])}",
            f"  - Social Volume: {token_a.get('social_volume', 0)}",
            f"",
            f"Token B ({token_b.get('token_symbol', 'B')}):",
            f"  - Sentiment: {token_b.get('sentiment_label', 'neutral').upper()} (score: {token_b.get('sentiment_score', 0.0):.2f})",
            f"  - Confidence: {token_b.get('confidence', 0.5):.2f}",
            f"  - Key Factors: {', '.join(token_b.get('key_factors', [])[:3])}",
            f"  - Social Volume: {token_b.get('social_volume', 0)}",
        ]
        
        return "\n".join(lines)


# Create singleton instance
sentiment_analyzer = SentimentAnalyzer()

