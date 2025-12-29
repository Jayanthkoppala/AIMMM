"use client";

import { useState, useEffect, useCallback } from "react";
import {
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus,
  Activity,
  BarChart3,
  Brain,
  Loader2,
  ChevronDown,
  ChevronUp,
  Zap,
  Target,
  Gauge,
  Volume2,
  MessageCircle,
  Users,
  Sparkles
} from "lucide-react";
import { Button } from "./ui/button";
import {
  getOHLCV,
  getIndicators,
  getSentiment,
  OHLCVCandle,
  IndicatorData,
  TokenSentimentData
} from "@/app/lib/api";

const POOLS = [
  {
    id: 1,
    name: "USDC.e / WETH.e",
    address: "0x83193fdc4d23fca53b2a36aef082886f4ef1c345a2c721b31c6e90a51173014d",
    tokens: ["USDC.e", "WETH.e"]
  },
  {
    id: 2,
    name: "USDC.e / MOVE",
    address: "0xbcbf55e1004687d412f05856ef7c17dcaacc1be632ba2d67b71073d25b425c3b",
    tokens: ["USDC.e", "MOVE"]
  }
];

interface PoolData {
  ohlcv: OHLCVCandle[] | null;
  indicators: IndicatorData | null;
  sentiment: {
    token_a: TokenSentimentData;
    token_b: TokenSentimentData;
    analyzed_at: string;
  } | null;
  loading: boolean;
  error: string | null;
}

function formatNumber(num: number | null | undefined, decimals: number = 2): string {
  if (num === null || num === undefined || isNaN(num)) return "—";
  if (Math.abs(num) < 0.0001) return num.toExponential(2);
  return num.toLocaleString(undefined, { 
    minimumFractionDigits: decimals, 
    maximumFractionDigits: decimals 
  });
}

function formatPrice(num: number | null | undefined): string {
  if (num === null || num === undefined || isNaN(num)) return "—";
  if (num < 0.01) return num.toFixed(6);
  if (num < 1) return num.toFixed(4);
  return num.toFixed(2);
}

function getRSIColor(rsi: number | null): string {
  if (rsi === null) return "text-[#006600]";
  if (rsi >= 70) return "text-[#ff3333]"; // Overbought
  if (rsi <= 30) return "text-[#00ff00]"; // Oversold
  return "text-[#ffaa00]"; // Neutral
}

function getSentimentColor(score: number): string {
  if (score >= 0.3) return "text-[#00ff00]";
  if (score <= -0.3) return "text-[#ff3333]";
  return "text-[#ffaa00]";
}

function getSentimentBg(score: number): string {
  if (score >= 0.3) return "bg-[#00ff00]/10 border-[#00ff00]/30";
  if (score <= -0.3) return "bg-[#ff3333]/10 border-[#ff3333]/30";
  return "bg-[#ffaa00]/10 border-[#ffaa00]/30";
}

function PriceChange({ current, previous }: { current: number; previous: number }) {
  const change = ((current - previous) / previous) * 100;
  const isPositive = change >= 0;
  
  return (
    <span className={`flex items-center gap-1 text-xs ${isPositive ? "text-[#00ff00]" : "text-[#ff3333]"}`}>
      {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
      {isPositive ? "+" : ""}{change.toFixed(2)}%
    </span>
  );
}

function IndicatorRow({ 
  label, 
  value, 
  suffix = "",
  color = "text-[#00ff00]" 
}: { 
  label: string; 
  value: number | null; 
  suffix?: string;
  color?: string;
}) {
  return (
    <div className="flex justify-between items-center py-1 border-b border-[#1a1a1a] last:border-0">
      <span className="text-[10px] text-[#006600] font-mono">{label}</span>
      <span className={`text-[11px] font-mono ${color}`}>
        {formatNumber(value)}{suffix}
      </span>
    </div>
  );
}

function MiniCandleChart({ candles }: { candles: OHLCVCandle[] }) {
  if (!candles || candles.length === 0) return null;
  
  const lastN = candles.slice(-30);
  const highs = lastN.map(c => c.high);
  const lows = lastN.map(c => c.low);
  const maxPrice = Math.max(...highs);
  const minPrice = Math.min(...lows);
  const range = maxPrice - minPrice || 1;
  
  return (
    <div className="flex items-end gap-[2px] h-12">
      {lastN.map((candle, i) => {
        const isGreen = candle.close >= candle.open;
        const bodyTop = Math.max(candle.open, candle.close);
        const bodyBottom = Math.min(candle.open, candle.close);
        const bodyHeight = ((bodyTop - bodyBottom) / range) * 100;
        const bodyBottom_pct = ((bodyBottom - minPrice) / range) * 100;
        
        return (
          <div
            key={i}
            className="relative w-[3px]"
            style={{ height: "100%" }}
          >
            {/* Wick */}
            <div
              className="absolute w-[1px] left-[1px]"
              style={{
                bottom: `${((candle.low - minPrice) / range) * 100}%`,
                height: `${((candle.high - candle.low) / range) * 100}%`,
                backgroundColor: isGreen ? "#00ff00" : "#ff3333"
              }}
            />
            {/* Body */}
            <div
              className="absolute w-full"
              style={{
                bottom: `${bodyBottom_pct}%`,
                height: `${Math.max(bodyHeight, 2)}%`,
                backgroundColor: isGreen ? "#00ff00" : "#ff3333"
              }}
            />
          </div>
        );
      })}
    </div>
  );
}

function PoolAnalyticsCard({ pool, data, onRefresh }: { 
  pool: typeof POOLS[0]; 
  data: PoolData;
  onRefresh: () => void;
}) {
  const [expanded, setExpanded] = useState(true);
  
  const latestCandle = data.ohlcv && data.ohlcv.length > 0 
    ? data.ohlcv[data.ohlcv.length - 1] 
    : null;
  const prevCandle = data.ohlcv && data.ohlcv.length > 1 
    ? data.ohlcv[data.ohlcv.length - 2] 
    : null;
  
  return (
    <div className="border border-[#1a1a1a] bg-[#0a0a0a]">
      {/* Header */}
      <div 
        className="flex items-center justify-between p-3 border-b border-[#1a1a1a] cursor-pointer hover:bg-[#111]"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <Activity className="h-4 w-4 text-[#00ff00]" />
          <div>
            <span className="text-sm font-mono text-[#00ff00]">{pool.name}</span>
            {latestCandle && (
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-lg font-bold text-[#00ff00] glow-text-subtle">
                  ${formatPrice(latestCandle.close)}
                </span>
                {prevCandle && (
                  <PriceChange current={latestCandle.close} previous={prevCandle.close} />
                )}
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => { e.stopPropagation(); onRefresh(); }}
            disabled={data.loading}
            className="h-7 w-7 p-0 hover:bg-[#00ff00]/10"
          >
            <RefreshCw className={`h-3 w-3 text-[#00ff00] ${data.loading ? "animate-spin" : ""}`} />
          </Button>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-[#006600]" />
          ) : (
            <ChevronDown className="h-4 w-4 text-[#006600]" />
          )}
        </div>
      </div>
      
      {expanded && (
        <div className="p-3 space-y-4">
          {data.loading && !data.ohlcv ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 text-[#00ff00] animate-spin" />
            </div>
          ) : data.error ? (
            <div className="text-center py-4 text-[#ff3333] text-xs font-mono">
              Error: {data.error}
            </div>
          ) : (
            <>
              {/* OHLCV Section */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-3 w-3 text-[#00ff00]" />
                  <span className="text-[10px] text-[#006600] uppercase font-mono">
                    OHLCV (1m candles)
                  </span>
                  {data.ohlcv && (
                    <span className="text-[10px] text-[#004400] font-mono">
                      [{data.ohlcv.length} candles]
                    </span>
                  )}
                </div>
                
                {data.ohlcv && data.ohlcv.length > 0 && (
                  <>
                    <MiniCandleChart candles={data.ohlcv} />
                    
                    <div className="grid grid-cols-5 gap-2 text-center">
                      {[
                        { label: "O", value: latestCandle?.open },
                        { label: "H", value: latestCandle?.high },
                        { label: "L", value: latestCandle?.low },
                        { label: "C", value: latestCandle?.close },
                        { label: "V", value: latestCandle?.volume }
                      ].map(({ label, value }) => (
                        <div key={label} className="p-2 bg-black border border-[#1a1a1a]">
                          <div className="text-[9px] text-[#006600] font-mono">{label}</div>
                          <div className="text-[10px] text-[#00ff00] font-mono">
                            {label === "V" ? formatNumber(value, 0) : formatPrice(value)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
              
              {/* Divider */}
              <div className="h-px bg-gradient-to-r from-transparent via-[#00ff00]/30 to-transparent" />
              
              {/* Technical Indicators Section */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Target className="h-3 w-3 text-[#00ff00]" />
                  <span className="text-[10px] text-[#006600] uppercase font-mono">
                    Technical Indicators
                  </span>
                </div>
                
                {data.indicators ? (
                  <div className="grid grid-cols-2 gap-3">
                    {/* Momentum */}
                    <div className="p-2 bg-black border border-[#1a1a1a]">
                      <div className="flex items-center gap-1 mb-2 pb-1 border-b border-[#1a1a1a]">
                        <Zap className="h-3 w-3 text-[#00ff00]" />
                        <span className="text-[9px] text-[#00ff00] uppercase font-mono">Momentum</span>
                      </div>
                      <IndicatorRow 
                        label="RSI" 
                        value={data.indicators.momentum.rsi} 
                        color={getRSIColor(data.indicators.momentum.rsi)}
                      />
                      <IndicatorRow label="Stoch" value={data.indicators.momentum.stoch} suffix="%" />
                      <IndicatorRow label="MFI" value={data.indicators.momentum.mfi} />
                      <IndicatorRow label="Williams %R" value={data.indicators.momentum.williams_r} />
                      <IndicatorRow label="CCI" value={data.indicators.momentum.cci} />
                    </div>
                    
                    {/* Trend */}
                    <div className="p-2 bg-black border border-[#1a1a1a]">
                      <div className="flex items-center gap-1 mb-2 pb-1 border-b border-[#1a1a1a]">
                        <TrendingUp className="h-3 w-3 text-[#00ff00]" />
                        <span className="text-[9px] text-[#00ff00] uppercase font-mono">Trend</span>
                      </div>
                      <IndicatorRow label="MACD" value={data.indicators.trend.macd} />
                      <IndicatorRow label="Signal" value={data.indicators.trend.macd_signal} />
                      <IndicatorRow label="SMA 20" value={data.indicators.trend.sma_20} />
                      <IndicatorRow label="SMA 50" value={data.indicators.trend.sma_50} />
                      <IndicatorRow label="ADX" value={data.indicators.trend.adx} />
                    </div>
                    
                    {/* Volatility */}
                    <div className="p-2 bg-black border border-[#1a1a1a]">
                      <div className="flex items-center gap-1 mb-2 pb-1 border-b border-[#1a1a1a]">
                        <Gauge className="h-3 w-3 text-[#00ff00]" />
                        <span className="text-[9px] text-[#00ff00] uppercase font-mono">Volatility</span>
                      </div>
                      <IndicatorRow label="BB Upper" value={data.indicators.volatility.bb_hband} />
                      <IndicatorRow label="BB Mid" value={data.indicators.volatility.bb_mavg} />
                      <IndicatorRow label="BB Lower" value={data.indicators.volatility.bb_lband} />
                      <IndicatorRow label="ATR" value={data.indicators.volatility.atr} />
                      <IndicatorRow label="BB %B" value={data.indicators.volatility.bb_pband} suffix="%" />
                    </div>
                    
                    {/* Volume */}
                    <div className="p-2 bg-black border border-[#1a1a1a]">
                      <div className="flex items-center gap-1 mb-2 pb-1 border-b border-[#1a1a1a]">
                        <Volume2 className="h-3 w-3 text-[#00ff00]" />
                        <span className="text-[9px] text-[#00ff00] uppercase font-mono">Volume</span>
                      </div>
                      <IndicatorRow label="OBV" value={data.indicators.volume.obv} />
                      <IndicatorRow label="VWAP" value={data.indicators.volume.vwap} />
                      <IndicatorRow label="CMF" value={data.indicators.volume.cmf} />
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-3 text-[#006600] text-[10px] font-mono">
                    No indicator data available
                  </div>
                )}
              </div>
              
              {/* Divider */}
              <div className="h-px bg-gradient-to-r from-transparent via-[#00ff00]/30 to-transparent" />
              
              {/* Sentiment Section - Only Token B (WETH.e / MOVE) */}
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Brain className="h-3 w-3 text-[#00ff00]" />
                  <span className="text-[10px] text-[#006600] uppercase font-mono">
                    Sentiment Analysis — {pool.tokens[1]}
                  </span>
                </div>
                
                {data.sentiment ? (
                  <div className="space-y-3">
                    {/* Main Sentiment Card */}
                    <div className={`p-4 border ${getSentimentBg(data.sentiment.token_b.score)}`}>
                      {/* Header with symbol and label */}
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <Sparkles className="h-4 w-4 text-[#00ff00]" />
                          <span className="text-base font-bold font-mono text-[#00ff00]">
                            {data.sentiment.token_b.symbol || pool.tokens[1]}
                          </span>
                        </div>
                        <span className={`text-sm font-bold uppercase px-2 py-1 rounded ${getSentimentColor(data.sentiment.token_b.score)} bg-black/50`}>
                          {data.sentiment.token_b.label}
                        </span>
                      </div>
                      
                      {/* Sentiment Score Bar */}
                      <div className="mb-4">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-[10px] text-[#006600]">Sentiment Score</span>
                          <span className={`text-sm font-bold ${getSentimentColor(data.sentiment.token_b.score)}`}>
                            {data.sentiment.token_b.score >= 0 ? "+" : ""}{(data.sentiment.token_b.score * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="h-2 bg-[#1a1a1a] rounded overflow-hidden relative">
                          <div className="absolute inset-0 flex items-center justify-center">
                            <div className="w-px h-full bg-[#333]" />
                          </div>
                          <div
                            className={`h-full transition-all duration-500 ${data.sentiment.token_b.score >= 0 ? "bg-[#00ff00] ml-[50%]" : "bg-[#ff3333] mr-[50%] ml-auto"}`}
                            style={{ width: `${Math.abs(data.sentiment.token_b.score) * 50}%` }}
                          />
                        </div>
                      </div>
                      
                      {/* Stats Grid */}
                      <div className="grid grid-cols-2 gap-3 mb-4">
                        <div className="p-2 bg-black border border-[#1a1a1a]">
                          <div className="flex items-center gap-1 mb-1">
                            <Target className="h-3 w-3 text-[#006600]" />
                            <span className="text-[9px] text-[#006600]">Confidence</span>
                          </div>
                          <span className="text-base font-bold text-[#00ff00]">
                            {(data.sentiment.token_b.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="p-2 bg-black border border-[#1a1a1a]">
                          <div className="flex items-center gap-1 mb-1">
                            <Zap className="h-3 w-3 text-[#006600]" />
                            <span className="text-[9px] text-[#006600]">Emotion</span>
                          </div>
                          <span className="text-base font-bold text-[#ffaa00] capitalize">
                            {data.sentiment.token_b.dominant_emotion}
                          </span>
                        </div>
                        <div className="p-2 bg-black border border-[#1a1a1a]">
                          <div className="flex items-center gap-1 mb-1">
                            <Users className="h-3 w-3 text-[#006600]" />
                            <span className="text-[9px] text-[#006600]">Social Volume</span>
                          </div>
                          <span className="text-base font-bold text-[#00ff00]">
                            {(data.sentiment.token_b.social_volume || 0).toLocaleString()}
                          </span>
                        </div>
                        <div className="p-2 bg-black border border-[#1a1a1a]">
                          <div className="flex items-center gap-1 mb-1">
                            <MessageCircle className="h-3 w-3 text-[#006600]" />
                            <span className="text-[9px] text-[#006600]">Mentions (24h)</span>
                          </div>
                          <span className="text-base font-bold text-[#00ff00]">
                            {(data.sentiment.token_b.mentions_24h || 0).toLocaleString()}
                          </span>
                        </div>
                      </div>
                      
                      {/* Key Factors */}
                      {data.sentiment.token_b.key_factors && data.sentiment.token_b.key_factors.length > 0 && (
                        <div>
                          <div className="flex items-center gap-1 mb-2">
                            <BarChart3 className="h-3 w-3 text-[#006600]" />
                            <span className="text-[9px] text-[#006600] uppercase">Key Factors</span>
                          </div>
                          <div className="space-y-1">
                            {(Array.isArray(data.sentiment.token_b.key_factors) 
                              ? data.sentiment.token_b.key_factors 
                              : JSON.parse(data.sentiment.token_b.key_factors as unknown as string || '[]')
                            ).map((factor: string, idx: number) => (
                              <div 
                                key={idx} 
                                className="flex items-start gap-2 p-2 bg-black/50 border border-[#1a1a1a] text-[10px]"
                              >
                                <span className="text-[#00ff00] mt-0.5">▸</span>
                                <span className="text-[#00cc00] font-mono">{factor}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-4 text-[#006600] text-[10px] font-mono border border-[#1a1a1a] bg-black">
                    No sentiment data available
                  </div>
                )}
                
                {data.sentiment?.analyzed_at && (
                  <div className="text-[9px] text-[#004400] font-mono text-right">
                    Last analyzed: {new Date(data.sentiment.analyzed_at).toLocaleString()}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export function MarketAnalytics() {
  const [poolData, setPoolData] = useState<Record<string, PoolData>>({});
  const [autoRefresh, setAutoRefresh] = useState(false);
  
  const fetchPoolData = useCallback(async (pool: typeof POOLS[0]) => {
    setPoolData(prev => ({
      ...prev,
      [pool.address]: { ...prev[pool.address], loading: true, error: null }
    }));
    
    try {
      const [ohlcvRes, indicatorsRes, sentimentRes] = await Promise.all([
        getOHLCV(pool.address, 100).catch(() => null),
        getIndicators(pool.address, 1).catch(() => null),
        getSentiment(pool.address).catch(() => null)
      ]);
      
      setPoolData(prev => ({
        ...prev,
        [pool.address]: {
          ohlcv: ohlcvRes?.data?.candles || null,
          indicators: indicatorsRes?.data?.indicators?.[0] || null,
          sentiment: sentimentRes?.data?.sentiment || null,
          loading: false,
          error: null
        }
      }));
    } catch (error) {
      setPoolData(prev => ({
        ...prev,
        [pool.address]: {
          ...prev[pool.address],
          loading: false,
          error: error instanceof Error ? error.message : "Failed to fetch data"
        }
      }));
    }
  }, []);
  
  const fetchAllData = useCallback(() => {
    POOLS.forEach(pool => fetchPoolData(pool));
  }, [fetchPoolData]);
  
  useEffect(() => {
    fetchAllData();
  }, [fetchAllData]);
  
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(fetchAllData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [autoRefresh, fetchAllData]);
  
  return (
    <div className="space-y-6 font-mono">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#00ff00] glow-text">
            ./market_analytics
          </h1>
          <p className="text-xs text-[#006600] mt-1">
            {">"} Real-time OHLCV, Technical Indicators & Sentiment
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="accent-[#00ff00]"
            />
            <span className="text-[10px] text-[#006600]">Auto-refresh (1m)</span>
          </label>
          <Button
            onClick={fetchAllData}
            variant="outline"
            size="sm"
            className="border-[#00ff00] text-[#00ff00] hover:bg-[#00ff00]/10 font-mono text-xs"
          >
            <RefreshCw className="h-3 w-3 mr-2" />
            REFRESH_ALL
          </Button>
        </div>
      </div>
      
      {/* Pool Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {POOLS.map(pool => (
          <PoolAnalyticsCard
            key={pool.address}
            pool={pool}
            data={poolData[pool.address] || { ohlcv: null, indicators: null, sentiment: null, loading: true, error: null }}
            onRefresh={() => fetchPoolData(pool)}
          />
        ))}
      </div>
    </div>
  );
}
