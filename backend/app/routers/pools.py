"""
Pools Router - Endpoints for retrieving trading pools
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.utils.database import db_connection
from app.utils.logger import logger
from pydantic import BaseModel

router = APIRouter(prefix="/pools", tags=["pools"])


class Pool(BaseModel):
    """Pool model"""
    id: int
    pool_address: str
    network: str
    pool_name: Optional[str]
    token_a_symbol: Optional[str]
    token_a_address: Optional[str]
    token_b_symbol: Optional[str]
    token_b_address: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str


@router.get("", response_model=List[Pool])
async def get_pools(
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    network: Optional[str] = Query("movement", description="Filter by network"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of pools to return"),
    search: Optional[str] = Query(None, description="Search by token symbols or pool name")
):
    """
    Get list of trading pools.
    
    Args:
        is_active: Filter by active status (default: True)
        network: Filter by network (default: movement)
        limit: Maximum number of pools to return
        search: Search term for filtering pools
    
    Returns:
        List of Pool objects
    """
    try:
        # Build query with filters
        query = """
            SELECT 
                id,
                pool_address,
                network,
                pool_name,
                token_a_symbol,
                token_a_address,
                token_b_symbol,
                token_b_address,
                is_active,
                created_at::text,
                updated_at::text
            FROM pools
            WHERE 1=1
        """
        params = []
        
        if is_active is not None:
            query += " AND is_active = %s"
            params.append(is_active)
        
        if network:
            query += " AND network = %s"
            params.append(network)
        
        if search:
            query += " AND (token_a_symbol ILIKE %s OR token_b_symbol ILIKE %s OR pool_name ILIKE %s)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)
        
        pools = db_connection.execute_query(query, tuple(params), fetch_all=True)
        
        if pools is None:
            return []
        
        # Convert to Pool objects
        pool_list = []
        for pool in pools:
            pool_list.append(Pool(
                id=pool[0],
                pool_address=pool[1],
                network=pool[2],
                pool_name=pool[3],
                token_a_symbol=pool[4],
                token_a_address=pool[5],
                token_b_symbol=pool[6],
                token_b_address=pool[7],
                is_active=pool[8],
                created_at=pool[9],
                updated_at=pool[10]
            ))
        
        logger.info(f"Retrieved {len(pool_list)} pools")
        return pool_list
        
    except Exception as e:
        logger.error(f"Error fetching pools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch pools: {str(e)}")


@router.get("/{pool_id}", response_model=Pool)
async def get_pool(pool_id: int):
    """
    Get a specific pool by ID.
    
    Args:
        pool_id: Integer ID of the pool
    
    Returns:
        Pool object
    """
    try:
        query = """
            SELECT 
                id,
                pool_address,
                network,
                pool_name,
                token_a_symbol,
                token_a_address,
                token_b_symbol,
                token_b_address,
                is_active,
                created_at::text,
                updated_at::text
            FROM pools
            WHERE id = %s
        """
        
        result = db_connection.execute_query(query, (pool_id,), fetch_all=False)
        
        if not result:
            raise HTTPException(status_code=404, detail="Pool not found")
        
        return Pool(
            id=result[0],
            pool_address=result[1],
            network=result[2],
            pool_name=result[3],
            token_a_symbol=result[4],
            token_a_address=result[5],
            token_b_symbol=result[6],
            token_b_address=result[7],
            is_active=result[8],
            created_at=result[9],
            updated_at=result[10]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pool {pool_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch pool: {str(e)}")

