const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface AgentRunRequest {
  mode: 'analysis' | 'trade' | 'autonomous';
  token_pair: {
    token_a: string;
    token_b: string;
  };
  pool_address?: string;  // CoinGecko pool address
  privy_access_token?: string;  // For autonomous mode
}

export interface AgentRunResponse {
  oracle_price: {
    token_a: number;
    token_b: number;
    timestamp: number;
  };
  llm_decision: {
    action: 'BUY' | 'SELL' | 'HOLD';
    confidence: number;
  };
  executed: boolean;
  tx_hash: string | null;
  execution_cost: string | null;
}

export interface PaymentRequirements {
  network: string;
  asset: string;
  payTo: string;
  maxAmountRequired: string;
  description: string;
}

export interface PaymentRequiredResponse {
  status: number;
  accepts: PaymentRequirements[];
}

export async function runAgent(
  request: AgentRunRequest,
  paymentHeader?: string
): Promise<AgentRunResponse | PaymentRequiredResponse> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  if (paymentHeader) {
    headers['X-PAYMENT'] = paymentHeader;
  }

  if (request.privy_access_token) {
    headers['Authorization'] = `Bearer ${request.privy_access_token}`;
  }

  const response = await fetch(`${API_BASE_URL}/agent/run`, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  });

  if (response.status === 402) {
    const data = await response.json();
    return data.detail as PaymentRequiredResponse;
  }

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json() as Promise<AgentRunResponse>;
}

export async function getHealth(): Promise<{ status: string }> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) {
    throw new Error('Health check failed');
  }
  return response.json();
}


