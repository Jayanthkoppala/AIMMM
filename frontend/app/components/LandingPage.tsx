"use client";

import { Button } from "./ui/button";
import { WalletSelectionModal } from "./wallet-selection-modal";
import { 
  Wallet, 
  Brain, 
  BarChart3, 
  TrendingUp, 
  Zap, 
  CreditCard,
  Activity,
  LineChart,
  MessageSquare
} from "lucide-react";

const features = [
  {
    icon: Brain,
    title: "AI Agent",
    description: "LLM-powered decision making with advanced market analysis",
    bgClass: "bg-cyber-indigo/20",
    textClass: "text-cyber-indigo",
  },
  {
    icon: BarChart3,
    title: "OHLCV Data",
    description: "Real-time candlestick data with 1-minute granularity",
    bgClass: "bg-cyber-blue/20",
    textClass: "text-cyber-blue",
  },
  {
    icon: MessageSquare,
    title: "Sentiment",
    description: "Social media sentiment analysis from multiple sources",
    bgClass: "bg-cyber-purple/20",
    textClass: "text-cyber-purple",
  },
  {
    icon: LineChart,
    title: "70+ Indicators",
    description: "Technical indicators including RSI, MACD, Bollinger Bands",
    bgClass: "bg-cyber-green/20",
    textClass: "text-cyber-green",
  },
  {
    icon: Zap,
    title: "Auto Execution",
    description: "24/7 autonomous trading with Privy embedded wallets",
    bgClass: "bg-cyber-amber/20",
    textClass: "text-cyber-amber",
  },
  {
    icon: CreditCard,
    title: "x402 Payments",
    description: "Integrated payment protocol for seamless transactions",
    bgClass: "bg-cyber-red/20",
    textClass: "text-cyber-red",
  },
];

const stats = [
  { label: "Trading Volume", value: "$2.3M+" },
  { label: "Trades Today", value: "1.2K+" },
  { label: "Success Rate", value: "94%" },
];

export function LandingPage() {
  return (
    <div className="min-h-screen">
      <section className="relative pt-20 pb-32 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-cyber-indigo/5 via-transparent to-transparent" />
        
        <div className="absolute top-20 left-1/4 w-96 h-96 bg-cyber-indigo/10 rounded-full blur-3xl" />
        <div className="absolute top-40 right-1/4 w-80 h-80 bg-cyber-purple/10 rounded-full blur-3xl" />

        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="flex flex-col items-center text-center max-w-4xl mx-auto">
            <div className="mb-8 animate-float">
              <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-cyber-indigo to-cyber-purple flex items-center justify-center shadow-glow-lg">
                <Brain className="h-12 w-12 text-white" />
              </div>
            </div>

            <h1 className="text-hero-mobile md:text-hero text-white mb-6 glow-text">
              <span className="text-cyber-indigo">AI</span> Trading Agent
            </h1>

            <p className="text-xl md:text-2xl text-gray-400 mb-4 max-w-2xl">
              Your AI-Powered Trading Companion
            </p>
            <p className="text-lg text-gray-500 mb-10">
              on <span className="text-cyber-purple font-semibold">Movement Network</span>
            </p>

            <WalletSelectionModal>
              <Button 
                size="lg" 
                className="cyber-button text-white px-8 py-6 text-lg font-semibold animate-pulse-glow border-0"
              >
                <Wallet className="h-5 w-5 mr-2" />
                Connect Wallet
              </Button>
            </WalletSelectionModal>

            <div className="mt-16 flex flex-wrap justify-center gap-8 md:gap-16">
              {stats.map((stat) => (
                <div key={stat.label} className="text-center">
                  <div className="text-3xl md:text-4xl font-bold text-white mb-1">
                    {stat.value}
                  </div>
                  <div className="text-sm text-gray-500">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="py-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
              Powerful Trading Features
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Everything you need for intelligent, automated trading on the Movement Network
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="feature-card group"
              >
                <div className={`w-12 h-12 rounded-xl ${feature.bgClass} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                  <feature.icon className={`h-6 w-6 ${feature.textClass}`} />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-400">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16 border-t border-cyber-indigo/10">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            <div>
              <h3 className="text-2xl font-bold text-white mb-2">
                Ready to Start Trading?
              </h3>
              <p className="text-gray-400">
                Connect your wallet and let the AI do the work
              </p>
            </div>
            <WalletSelectionModal>
              <Button 
                size="lg" 
                className="cyber-button text-white px-8 border-0"
              >
                <Activity className="h-5 w-5 mr-2" />
                Launch App
              </Button>
            </WalletSelectionModal>
          </div>
        </div>
      </section>
    </div>
  );
}
