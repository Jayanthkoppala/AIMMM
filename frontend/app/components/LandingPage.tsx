"use client";

import { Button } from "./ui/button";
import { WalletSelectionModal } from "./wallet-selection-modal";
import { 
  Wallet, 
  Brain, 
  BarChart3, 
  Zap, 
  CreditCard,
  ArrowRight,
  LineChart,
  MessageSquare,
  ChevronRight
} from "lucide-react";

const features = [
  {
    icon: Brain,
    title: "AI-Powered Analysis",
    description: "Advanced LLM decision making with real-time market analysis and sentiment tracking",
  },
  {
    icon: BarChart3,
    title: "Real-Time Data",
    description: "OHLCV candlestick data with 1-minute granularity and 70+ technical indicators",
  },
  {
    icon: MessageSquare,
    title: "Sentiment Analysis",
    description: "Social media sentiment tracking from multiple sources for informed decisions",
  },
  {
    icon: LineChart,
    title: "Technical Indicators",
    description: "RSI, MACD, Bollinger Bands, and more for comprehensive market analysis",
  },
  {
    icon: Zap,
    title: "Auto Execution",
    description: "24/7 autonomous trading with secure Privy embedded wallets",
  },
  {
    icon: CreditCard,
    title: "x402 Payments",
    description: "Integrated payment protocol for seamless on-chain transactions",
  },
];

const stats = [
  { label: "Trading Volume", value: "$2.3M+", suffix: "" },
  { label: "Daily Trades", value: "1.2K", suffix: "+" },
  { label: "Success Rate", value: "94", suffix: "%" },
];

export function LandingPage() {
  return (
    <div className="min-h-screen">
      <section className="relative pt-24 pb-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#111317] border border-[#2A2D33] text-sm text-gray-400 mb-8">
              <span className="w-2 h-2 rounded-full bg-emerald animate-pulse-subtle"></span>
              Live on Movement Network
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-semibold text-white mb-6 tracking-tight leading-tight">
              AI Trading Agent
            </h1>

            <p className="text-lg sm:text-xl text-gray-400 mb-10 max-w-2xl mx-auto leading-relaxed">
              Autonomous trading powered by AI. Real-time analysis, intelligent execution, and 24/7 market monitoring.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <WalletSelectionModal>
                <Button 
                  size="lg" 
                  className="bg-emerald hover:bg-emerald-dark text-white px-8 py-6 text-base font-medium border-0 w-full sm:w-auto"
                >
                  <Wallet className="h-5 w-5 mr-2" />
                  Connect Wallet
                </Button>
              </WalletSelectionModal>
              <Button 
                variant="outline"
                size="lg"
                className="bg-transparent border-[#2A2D33] hover:border-gray-500 text-white px-8 py-6 text-base font-medium w-full sm:w-auto"
              >
                View Documentation
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>

          <div className="mt-20 grid grid-cols-3 gap-8 max-w-2xl mx-auto">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-3xl sm:text-4xl font-semibold text-white mb-1 font-mono">
                  {stat.value}<span className="text-emerald">{stat.suffix}</span>
                </div>
                <div className="text-sm text-gray-500">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="h-px bg-[#1F1F24]" />
      </div>

      <section id="features" className="py-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-2xl sm:text-3xl font-semibold text-white mb-4">
              Built for Intelligent Trading
            </h2>
            <p className="text-gray-400 max-w-xl mx-auto">
              Everything you need for automated trading on Movement Network
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="p-6 rounded-xl bg-[#111317] border border-[#1F1F24] hover:border-[#2A2D33] transition-colors"
              >
                <div className="w-10 h-10 rounded-lg bg-emerald/10 flex items-center justify-center mb-4">
                  <feature.icon className="h-5 w-5 text-emerald" />
                </div>
                <h3 className="text-lg font-medium text-white mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-400 text-sm leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="h-px bg-[#1F1F24]" />
      </div>

      <section className="py-16">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8 p-8 rounded-2xl bg-[#111317] border border-[#1F1F24]">
            <div>
              <h3 className="text-xl font-semibold text-white mb-2">
                Ready to start trading?
              </h3>
              <p className="text-gray-400">
                Connect your wallet and let AI handle the rest
              </p>
            </div>
            <WalletSelectionModal>
              <Button 
                size="lg" 
                className="bg-emerald hover:bg-emerald-dark text-white px-8 border-0 whitespace-nowrap"
              >
                Get Started
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </WalletSelectionModal>
          </div>
        </div>
      </section>
    </div>
  );
}
