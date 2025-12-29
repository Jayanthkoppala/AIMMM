from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from app.models.agent import (
    AgentRunRequest,
    AgentRunResponse,
    PaymentRequiredResponse,
    OraclePrice,
    LLMDecision,
    SentimentAnalysis,
    TokenSentiment,
    RiskManagementData
)
from app.services import oracle, llm, mosaic, x402, supabase, sentiment, risk_management, privy_service, autonomous_wallet
from app.services.ohlcv import ohlcv_service
from app.services.technical_indicators import technical_indicators_calculator
from app.services.wallet import get_wallet_balance_usd
from app.utils.database import db_connection
from app.config import settings
from app.utils.validation import validate_address
from app.utils.logger import logger
from app.exceptions import (
    ValidationError,
    PaymentRequiredError,
    PaymentVerificationError,
    DatabaseError
)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/run", response_model=AgentRunResponse)
async def run_agent(
    request: AgentRunRequest,
    req: Request,
    x_payment: Optional[str] = Header(None, alias="X-PAYMENT")
):
    """
    Run AI trading agent.
    Returns 402 Payment Required if payment is needed.
    """
    logger.info(f"Agent run request: mode={request.mode}, token_a={request.token_pair.token_a[:10]}..., token_b={request.token_pair.token_b[:10]}...")
    
    # Validate token addresses
    if not validate_address(request.token_pair.token_a):
        raise ValidationError("Invalid token_a address", field="token_pair.token_a")
    if not validate_address(request.token_pair.token_b):
        raise ValidationError("Invalid token_b address", field="token_pair.token_b")
    
    # Handle autonomous mode differently
    wallet_address = None
    user = None
    payment_tx_hash = None
    privy_user_id = None
    
    if request.mode == "autonomous":
        # Autonomous mode uses Privy authentication instead of payment
        if not request.privy_access_token:
            raise ValidationError("Privy access token required for autonomous mode", field="privy_access_token")
        
        # Verify Privy user
        privy_user = await privy_service.privy_service.verify_access_token(request.privy_access_token)
        if not privy_user:
            raise ValidationError("Invalid Privy access token")
        
        privy_user_id = privy_user.get('id')
        logger.info(f"Privy user verified: {privy_user_id}")
        
        # Get or create autonomous wallet
        wallet_info = await autonomous_wallet.autonomous_wallet_service.get_wallet(privy_user_id)
        if not wallet_info:
            # Create wallet on first use
            logger.info(f"Creating autonomous wallet for Privy user {privy_user_id}")
            await autonomous_wallet.autonomous_wallet_service.create_wallet_for_user(privy_user_id)
            wallet_info = await autonomous_wallet.autonomous_wallet_service.get_wallet(privy_user_id)
        
        if not wallet_info:
            raise DatabaseError("Failed to create/get autonomous wallet")
        
        wallet_address = wallet_info['wallet_address']
        
        # Get or create user using wallet address
        user = await supabase.supabase_service.get_or_create_user(wallet_address)
        if not user:
            logger.error(f"Failed to get/create user for wallet: {wallet_address[:10]}...")
            raise DatabaseError("Failed to get/create user")
    else:
        # Standard mode: require payment
        payment_header = x_payment or x402.check_payment_header(dict(req.headers))
        
        if not payment_header:
            # Return 402 Payment Required
            cost = settings.BASE_AGENT_COST_USDC
            if request.mode == "trade":
                cost += 0.0005  # Additional cost for trade execution
            
            payment_req = x402.get_payment_requirements(cost)
            logger.info(f"Payment required: cost={cost} USDC")
            raise PaymentRequiredError(payment_req)
        
        # Verify payment
        execution_cost = settings.BASE_AGENT_COST_USDC
        if request.mode == "trade":
            execution_cost += 0.0005
        
        payment_req = x402.get_payment_requirements(execution_cost)
        verified, payment_tx_hash, invoice_id = await x402.verify_payment(payment_header, payment_req)
        
        if not verified:
            logger.warning("Payment verification failed")
            raise PaymentVerificationError()
        
        # Extract wallet address from payment header
        wallet_address = x402.extract_wallet_address(payment_header)
        if not wallet_address:
            logger.error("Could not extract wallet address from payment header")
            raise ValidationError("Could not extract wallet address from payment")
        
        logger.info(f"Payment verified: wallet={wallet_address[:10]}..., tx_hash={payment_tx_hash[:10] if payment_tx_hash else 'N/A'}...")
        
        # Get or create user
        user = await supabase.supabase_service.get_or_create_user(wallet_address)
        if not user:
            logger.error(f"Failed to get/create user for wallet: {wallet_address[:10]}...")
            raise DatabaseError("Failed to get/create user")
    
    # Fetch oracle prices from CoinGecko pool
    if not request.pool_address:
        raise ValidationError("pool_address is required for CoinGecko integration", field="pool_address")
    
    price_data = await oracle.get_token_prices(
        request.token_pair.token_a,
        request.token_pair.token_b,
        pool_address=request.pool_address
    )
    
    oracle_price = OraclePrice(
        token_a=price_data["token_a_price"],
        token_b=price_data["token_b_price"],
        timestamp=price_data["timestamp"]
    )
    
    # Get OHLCV historical data for LLM context
    ohlcv_context = None
    try:
        ohlcv_context = await ohlcv_service.format_for_llm(
            pool_address=request.pool_address
        )
        logger.info(f"OHLCV context retrieved: {len(ohlcv_context)} characters")
    except Exception as e:
        logger.warning(f"Failed to get OHLCV context: {e}. Continuing without historical data.")
        ohlcv_context = None
    
    # Get technical indicators context for LLM
    technical_context = None
    try:
        technical_context = technical_indicators_calculator.format_for_llm(
            pool_address=request.pool_address,
            indicators=['RSI', 'MACD', 'SMA_20', 'SMA_50', 'EMA_50', 'BB', 'ATR', 'ADX', 'Stoch', 'OBV', 'MFI', 'VWAP']
        )
        if technical_context:
            logger.info(f"Technical indicators context retrieved: {len(technical_context)} characters")
    except Exception as e:
        logger.warning(f"Failed to get technical indicators context: {e}. Continuing without indicators.")
        technical_context = None
    
    # Get token symbols from database if available
    token_a_symbol = None
    token_b_symbol = None
    if db_connection.pool and request.pool_address:
        try:
            query = """
                SELECT token_a_symbol, token_b_symbol, token_a_address, token_b_address
                FROM pools
                WHERE pool_address = %s AND network = 'movement'
                LIMIT 1
            """
            pool_info = db_connection.execute_query(
                query, 
                (request.pool_address,), 
                fetch_one=True
            )
            if pool_info:
                # Match addresses to determine which is token_a and token_b
                if pool_info.get('token_a_address') == request.token_pair.token_a:
                    token_a_symbol = pool_info.get('token_a_symbol')
                    token_b_symbol = pool_info.get('token_b_symbol')
                elif pool_info.get('token_b_address') == request.token_pair.token_a:
                    token_a_symbol = pool_info.get('token_b_symbol')
                    token_b_symbol = pool_info.get('token_a_symbol')
        except Exception as e:
            logger.debug(f"Could not fetch token symbols from database: {e}")
    
    # Get sentiment analysis
    sentiment_data = None
    sentiment_context = None
    try:
        sentiment_result = await sentiment.sentiment_analyzer.analyze_token_pair_sentiment(
            token_a_address=request.token_pair.token_a,
            token_b_address=request.token_pair.token_b,
            token_a_symbol=token_a_symbol,
            token_b_symbol=token_b_symbol,
            timeframe="24h"
        )
        
        # Format sentiment for LLM context
        sentiment_context = await sentiment.sentiment_analyzer.format_sentiment_for_llm(sentiment_result)
        logger.info(f"Sentiment analysis retrieved: {len(sentiment_context)} characters")
        
        # Convert to response model
        sentiment_data = SentimentAnalysis(
            token_a=TokenSentiment(
                token_symbol=sentiment_result['token_a'].get('token_symbol', 'A'),
                token_address=sentiment_result['token_a'].get('token_address', request.token_pair.token_a),
                sentiment_score=sentiment_result['token_a'].get('sentiment_score', 0.0),
                sentiment_label=sentiment_result['token_a'].get('sentiment_label', 'neutral'),
                confidence=sentiment_result['token_a'].get('confidence', 0.5),
                key_factors=sentiment_result['token_a'].get('key_factors', []),
                social_volume=sentiment_result['token_a'].get('social_volume', 0),
                mentions_24h=sentiment_result['token_a'].get('mentions_24h', 0),
                dominant_emotion=sentiment_result['token_a'].get('dominant_emotion', 'neutral')
            ),
            token_b=TokenSentiment(
                token_symbol=sentiment_result['token_b'].get('token_symbol', 'B'),
                token_address=sentiment_result['token_b'].get('token_address', request.token_pair.token_b),
                sentiment_score=sentiment_result['token_b'].get('sentiment_score', 0.0),
                sentiment_label=sentiment_result['token_b'].get('sentiment_label', 'neutral'),
                confidence=sentiment_result['token_b'].get('confidence', 0.5),
                key_factors=sentiment_result['token_b'].get('key_factors', []),
                social_volume=sentiment_result['token_b'].get('social_volume', 0),
                mentions_24h=sentiment_result['token_b'].get('mentions_24h', 0),
                dominant_emotion=sentiment_result['token_b'].get('dominant_emotion', 'neutral')
            ),
            timeframe=sentiment_result.get('timeframe', '24h'),
            timestamp=sentiment_result.get('timestamp', '')
        )
    except Exception as e:
        logger.warning(f"Failed to get sentiment analysis: {e}. Continuing without sentiment data.", exc_info=True)
        sentiment_context = None
        sentiment_data = None
    
    # Get LLM decision with OHLCV, sentiment, and technical indicators context
    llm_decision = await llm.get_llm_decision(
        oracle_price.token_a,
        oracle_price.token_b,
        ohlcv_context=ohlcv_context,
        sentiment_context=sentiment_context,
        technical_context=technical_context
    )
    
    # Execute trade if mode is "trade" and action is not HOLD
    executed = False
    tx_hash = None
    position_size_info = None
    stop_loss_info = None
    take_profit_info = None
    stop_loss_price = None
    
    if request.mode == "trade" and llm_decision.action != "HOLD":
        # Get wallet balance dynamically
        try:
            account_balance_usd = await get_wallet_balance_usd(wallet_address)
            logger.info(f"Wallet balance: ${account_balance_usd:.2f} USD")
        except Exception as e:
            logger.warning(f"Could not fetch wallet balance: {e}, using default $1000")
            account_balance_usd = 1000.0  # Fallback default
        
        # Get ATR for volatility-based stop loss
        atr_value = None
        try:
            if db_connection.pool and request.pool_address:
                # Get latest ATR from technical indicators
                pool_query = """
                    SELECT id FROM pools
                    WHERE pool_address = %s AND network = 'movement'
                    LIMIT 1
                """
                pool_result = db_connection.execute_query(
                    pool_query,
                    (request.pool_address,),
                    fetch_one=True
                )
                if pool_result:
                    atr_query = """
                        SELECT atr FROM technical_indicators
                        WHERE pool_id = %s AND atr IS NOT NULL
                        ORDER BY timestamp DESC
                        LIMIT 1
                    """
                    atr_result = db_connection.execute_query(
                        atr_query,
                        (pool_result['id'],),
                        fetch_one=True
                    )
                    if atr_result and atr_result.get('atr'):
                        atr_value = float(atr_result['atr'])
        except Exception as e:
            logger.debug(f"Could not fetch ATR: {e}")
        
        # Calculate stop loss
        stop_loss_info = risk_management.risk_agent.calculate_stop_loss(
            entry_price=oracle_price.token_a,
            volatility=None,
            risk_tolerance="moderate",
            atr_value=atr_value
        )
        
        # Use appropriate stop loss based on trade direction
        if llm_decision.action == "BUY":
            stop_loss_price = stop_loss_info['stop_loss_long']
        else:  # SELL
            stop_loss_price = stop_loss_info['stop_loss_short']
        
        # Calculate position size dynamically
        position_size_info = risk_management.risk_agent.calculate_position_size(
            account_balance=account_balance_usd,
            entry_price=oracle_price.token_a,
            stop_loss_price=stop_loss_price,
            risk_per_trade=0.02,  # 2% risk per trade
            max_position_pct=0.10  # Max 10% of account
        )
        
        # Validate trade risk
        is_valid, error_msg = risk_management.risk_agent.validate_trade_risk(
            account_balance=account_balance_usd,
            position_value=position_size_info['position_value'],
            risk_amount=position_size_info['risk_amount']
        )
        
        if not is_valid:
            logger.warning(f"Trade risk validation failed: {error_msg}. Using minimum position size.")
            # Use minimum position as fallback
            position_size_info = {
                "position_size": 1000000 / oracle_price.token_a if oracle_price.token_a > 0 else 1000000,
                "risk_amount": account_balance_usd * 0.02,
                "position_value": 100.0,  # Minimum $100 position
                "risk_percentage": 2.0,
                "position_percentage": 10.0
            }
        
        # Calculate take profit
        take_profit_info = risk_management.risk_agent.calculate_take_profit(
            entry_price=oracle_price.token_a,
            stop_loss_price=stop_loss_price,
            reward_ratio=2.0  # 2:1 reward to risk
        )
        
        # Determine swap direction
        direction = "X_TO_Y" if llm_decision.action == "BUY" else "Y_TO_X"
        
        # Convert position size to token units
        # Position size is already in token units (calculated from USD / price)
        position_size_tokens = position_size_info['position_size']
        
        # Convert to smallest unit (assuming 6 decimals for most tokens)
        # For more accuracy, we could fetch token decimals from blockchain
        # For now, using 6 decimals as standard
        token_decimals = 6
        amount_in = int(position_size_tokens * (10 ** token_decimals))
        
        # Ensure minimum amount (at least 1 token unit)
        if amount_in < 1:
            logger.warning(f"Calculated amount_in ({amount_in}) too small, using minimum")
            amount_in = 1
        
        # Calculate minimum amount out with slippage tolerance
        # Use 1% slippage (100 basis points)
        slippage_tolerance = 0.01
        min_amount_out = int(amount_in * (1 - slippage_tolerance))
        
        logger.info(
            f"Dynamic position sizing: "
            f"Size={position_size_info['position_size']:.4f} tokens, "
            f"Value=${position_size_info['position_value']:.2f}, "
            f"Risk=${position_size_info['risk_amount']:.2f} ({position_size_info['risk_percentage']:.2f}%), "
            f"Stop Loss=${stop_loss_price:.4f}, "
            f"Take Profit=${take_profit_info.get('take_profit_long') or take_profit_info.get('take_profit_short') or 0:.4f}"
        )
        
        # Execute swap
        if request.mode == "autonomous" and privy_user_id:
            # Use autonomous wallet service for signing
            tx_hash = await autonomous_wallet.autonomous_wallet_service.sign_and_submit_transaction(
                privy_user_id=privy_user_id,
                transaction_payload={
                    "token_a": request.token_pair.token_a,
                    "token_b": request.token_pair.token_b,
                    "direction": direction,
                    "amount_in": amount_in,
                    "min_amount_out": min_amount_out
                }
            )
        else:
            # Standard mode: use mosaic service (frontend will sign)
            tx_hash = await mosaic.execute_swap(
                request.token_pair.token_a,
                request.token_pair.token_b,
                direction,
                amount_in,
                min_amount_out,
                wallet_address
            )
        
        executed = tx_hash is not None
    
    # Calculate execution cost (0 for autonomous mode)
    execution_cost = None
    if request.mode != "autonomous":
        execution_cost = settings.BASE_AGENT_COST_USDC
        if request.mode == "trade":
            execution_cost += 0.0005
    
    # Store execution in database
    execution = await supabase.supabase_service.create_agent_execution(
        user_id=user["id"],
        mode=request.mode,
        token_a_address=request.token_pair.token_a,
        token_b_address=request.token_pair.token_b,
        switchboard_feed_id=None,  # Deprecated - using pool_address instead
        oracle_price_a=oracle_price.token_a,
        oracle_price_b=oracle_price.token_b,
        llm_action=llm_decision.action,
        llm_confidence=llm_decision.confidence,
        executed=executed,
        tx_hash=tx_hash,
        execution_cost=execution_cost
    )
    
    if not execution:
        logger.error("Failed to create agent execution record")
        raise DatabaseError("Failed to create agent execution record")
    
    execution_id = execution.get("id")
    logger.info(f"Agent execution created: execution_id={execution_id}")
    
    # Store payment record (only for non-autonomous modes)
    if payment_tx_hash and execution_id and request.mode != "autonomous":
        payment_record = await supabase.supabase_service.create_payment_record(
            agent_execution_id=execution_id,  # Fixed: use execution ID, not user ID
            invoice_id=invoice_id or "",
            amount=execution_cost,
            tx_hash=payment_tx_hash,
            status="verified"
        )
        if payment_record:
            logger.info(f"Payment record created: payment_id={payment_record.get('id')}")
        else:
            logger.warning("Failed to create payment record")
    
    # Prepare risk management data for response
    risk_data = None
    if request.mode == "trade" and position_size_info and stop_loss_info and take_profit_info and stop_loss_price:
        # Determine take profit price based on direction
        if llm_decision.action == "BUY":
            take_profit_price = take_profit_info.get('take_profit_long')
        else:  # SELL
            take_profit_price = take_profit_info.get('take_profit_short')
        
        risk_data = RiskManagementData(
            position_size=position_size_info['position_size'],
            position_value_usd=position_size_info['position_value'],
            risk_amount_usd=position_size_info['risk_amount'],
            risk_percentage=position_size_info['risk_percentage'],
            position_percentage=position_size_info['position_percentage'],
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            reward_ratio=take_profit_info.get('reward_ratio')
        )
    
    return AgentRunResponse(
        oracle_price=oracle_price,
        llm_decision=llm_decision,
        sentiment=sentiment_data,
        risk_management=risk_data,
        executed=executed,
        tx_hash=tx_hash,
        execution_cost=str(int(execution_cost * 1_000_000_000))
    )

