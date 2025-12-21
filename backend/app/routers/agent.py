from fastapi import APIRouter, Request, HTTPException, Header
from typing import Optional
from app.models.agent import (
    AgentRunRequest,
    AgentRunResponse,
    PaymentRequiredResponse,
    OraclePrice,
    LLMDecision
)
from app.services import oracle, llm, uniswap, x402, supabase
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
    
    # Check for payment
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
    
    # Fetch oracle prices
    price_data = await oracle.get_token_prices(
        request.token_pair.token_a,
        request.token_pair.token_b,
        request.switchboard_feed_id
    )
    
    oracle_price = OraclePrice(
        token_a=price_data["token_a_price"],
        token_b=price_data["token_b_price"],
        timestamp=price_data["timestamp"]
    )
    
    # Get LLM decision
    llm_decision = await llm.get_llm_decision(
        oracle_price.token_a,
        oracle_price.token_b
    )
    
    # Execute trade if mode is "trade" and action is not HOLD
    executed = False
    tx_hash = None
    
    if request.mode == "trade" and llm_decision.action != "HOLD":
        # Determine swap direction
        direction = "X_TO_Y" if llm_decision.action == "BUY" else "Y_TO_X"
        
        # Calculate swap amounts (simplified)
        amount_in = 1000000  # 1 token with 6 decimals
        min_amount_out = int(amount_in * 0.95)  # 5% slippage tolerance
        
        # Execute swap
        tx_hash = await uniswap.execute_swap(
            request.token_pair.token_a,
            request.token_pair.token_b,
            direction,
            amount_in,
            min_amount_out,
            wallet_address
        )
        
        executed = tx_hash is not None
    
    # Store execution in database
    execution = await supabase.supabase_service.create_agent_execution(
        user_id=user["id"],
        mode=request.mode,
        token_a_address=request.token_pair.token_a,
        token_b_address=request.token_pair.token_b,
        switchboard_feed_id=request.switchboard_feed_id,
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
    
    # Store payment record
    if payment_tx_hash and execution_id:
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
    
    return AgentRunResponse(
        oracle_price=oracle_price,
        llm_decision=llm_decision,
        executed=executed,
        tx_hash=tx_hash,
        execution_cost=str(int(execution_cost * 1_000_000_000))
    )

