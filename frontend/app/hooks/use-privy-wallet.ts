import { usePrivy } from "@privy-io/react-auth";

export function usePrivyWallet() {
  const { 
    ready, 
    authenticated, 
    user, 
    login, 
    logout,
    getAccessToken 
  } = usePrivy();

  return {
    ready,
    authenticated,
    user,
    privyUserId: user?.id,
    login,
    logout,
    getAccessToken, // Used to authenticate backend requests
  };
}

