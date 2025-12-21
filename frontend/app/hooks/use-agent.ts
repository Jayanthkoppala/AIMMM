import { useState } from 'react';
import { runAgent, AgentRunRequest, AgentRunResponse, PaymentRequiredResponse } from '@/app/lib/api';
import { useX402Payment } from './use-x402-payment';
import { toast } from 'sonner';

export function useAgent() {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AgentRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { payForAccess, isConnected } = useX402Payment();

  const runAgentExecution = async (request: AgentRunRequest) => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      // First attempt without payment
      let response = await runAgent(request);

      // Check if payment is required
      if ('status' in response && response.status === 402) {
        const paymentReq = response as PaymentRequiredResponse;
        
        if (!isConnected) {
          throw new Error('Wallet not connected. Please connect your wallet to proceed.');
        }

        // Show payment prompt
        toast.loading('Payment required. Please approve in your wallet...');

        // Sign payment
        const paymentHeader = await payForAccess(paymentReq.accepts[0]);
        toast.success('Payment signed. Processing...');

        // Retry with payment header
        response = await runAgent(request, paymentHeader);
      }

      const agentResponse = response as AgentRunResponse;
      setResult(agentResponse);
      toast.success('Agent execution completed!');
      
      return agentResponse;
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to run agent';
      setError(errorMessage);
      toast.error(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  return {
    runAgent: runAgentExecution,
    isLoading,
    result,
    error,
    isConnected,
  };
}

