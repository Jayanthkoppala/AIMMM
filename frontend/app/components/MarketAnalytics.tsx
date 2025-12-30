"use client";

import { useState, useEffect, useCallback } from "react";
import {
  RefreshCw,
  TrendingUp,
  TrendingDown,
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
  Sparkles,
  Terminal,
  Cpu,
  ScanLine
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

// --- Utility Functions ---

function formatNumber(num: number | null | undefined, decimals: number = 2): string {
  if (num === null || num === undefined || isNaN(num)) return "N/A";
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

// --- UI Components ---

/** * A stylized data cell for the dashboard look.
 * Label small at top, Value large at bottom.
 */
function DataCell({ 
  label, 
  value, 
  subValue,
  color = "text-[#00ff00]",
  icon: Icon
}: { 
  label: string; 
  value: string | number | null; 
  subValue?: string;
  color?: string;
  icon?: any;
}) {
  return (
    <div className="flex flex-col p-2 bg-[#050505] border-l border-[#1a1a1a] hover:bg-[#111] transition-colors group relative overflow-hidden">
      <div className="flex items-center gap-1.5 mb-1">
        {Icon && <Icon className="h-3 w-3 text-[#006600] group-hover:text-[#00ff00] transition-colors" />}
        <span className="text-[9px] text-[#006600] uppercase font-mono tracking-wider">{label}</span>
      </div>
      <div className={`text-sm font-mono font-bold tracking-tight ${color}`}>
        {value}
        {subValue && <span className="text-[10px] text-[#004400] ml-1">{subValue}</span>}
      </div>
      {/* Decorative corner */}
      <div className="absolute top-0 right-0 w-1 h-1 bg-[#006600]/20" />
    </div>
  );
}

function SectionHeader({ icon: Icon, title }: { icon: any, title: string }) {
  return (
    <div className="flex items-center gap-2 mb-2 pb-1 border-b border-[#1a1a1a]">
      <div className="bg-[#00ff00]/10 p-1 rounded-sm">
        <Icon className="h-3 w-3 text-[#00ff00]" />
      </div>
      <span className="text-[10px] font-bold text-[#00ff00] uppercase font-mono tracking-widest">
        {title}
      </span>
      <div className="flex-1 h-px bg-gradient-to-r from-[#00ff00]/30 to-transparent ml-2" />
    </div>
  );
}

function MiniCandleChart({ candles }: { candles: OHLCVCandle[] }) {
  if (!candles || candles.length === 0) return null;
  
  const lastN = candles.slice(-40); // Show a bit more history
  const highs = lastN.map(c => c.high);
  const lows = lastN.map(c => c.low);
  const maxPrice = Math.max(...highs);
  const minPrice = Math.min(...lows);
  const range = maxPrice - minPrice || 1;
  
  return (
    <div className="relative w-full h-24 bg-[#050505] border border-[#1a1a1a] p-2 overflow-hidden">
      {/* Grid Lines Background */}
      <div className="absolute inset-0 opacity-10" 
           style={{ backgroundImage: 'linear-gradient(#00ff00 1px, transparent 1px), linear-gradient(90deg, #00ff00 1px, transparent 1px)', backgroundSize: '20px 20px' }} 
      />
      
      <div className="flex items-end justify-between gap-[1px] h-full relative z-10">
        {lastN.map((candle, i) => {
          const isGreen = candle.close >= candle.open;
          const bodyTop = Math.max(candle.open, candle.close);
          const bodyBottom = Math.min(candle.open, candle.close);
          
          // Percentages
          const wickTopPct = ((candle.high - minPrice) / range) * 100;
          const wickHeightPct = ((candle.high - candle.low) / range) * 100;
          const bodyBottomPct = ((bodyBottom - minPrice) / range) * 100;
          const bodyHeightPct = ((bodyTop - bodyBottom) / range) * 100;
          
          return (
            <div key={i} className="relative flex-1 group" style={{ height: "100%" }}>
              {/* Wick */}
              <div
                className="absolute w-[1px] left-1/2 -translate-x-1/2 opacity-60"
                style={{
                  bottom: `${((candle.low - minPrice) / range) * 100}%`,
                  height: `${Math.max(wickHeightPct, 1)}%`,
                  backgroundColor: isGreen ? "#00ff00" : "#ff3333"
                }}
              />
              {/* Body */}
              <div
                className="absolute w-[80%] left-[10%]"
                style={{
                  bottom: `${bodyBottomPct}%`,
                  height: `${Math.max(bodyHeightPct, 2)}%`,
                  backgroundColor: isGreen ? "#00ff00" : "#ff3333"
                }}
              />
            </div>
          );
        })}
      </div>
      
      {/* Price Labels Overlay */}
      <div className="absolute top-1 right-1 text-[8px] font-mono text-[#006600] bg-black/80 px-1">
        H: {maxPrice.toFixed(2)}
      </div>
      <div className="absolute bottom-1 right-1 text-[8px] font-mono text-[#006600] bg-black/80 px-1">
        L: {minPrice.toFixed(2)}
      </div>
    </div>
  );
}

function PoolAnalyticsCard({ pool, data, onRefresh }: { 
  pool: typeof POOLS[0]; 
  data: PoolData;
  onRefresh: () => void;
}) {
  const [expanded, setExpanded] = useState(true);
  
  const latestCandle = data.ohlcv?.length ? data.ohlcv[data.ohlcv.length - 1] : null;
  const prevCandle = data.ohlcv && data.ohlcv.length > 1 ? data.ohlcv[data.ohlcv.length - 2] : null;
  
  // Calculate Price Change for Header
  const change = latestCandle && prevCandle 
    ? ((latestCandle.close - prevCandle.close) / prevCandle.close) * 100 
    : 0;
  const isPositive = change >= 0;

  return (
    <div className={`border border-[#1a1a1a] bg-[#080808] transition-all duration-300 ${expanded ? 'shadow-[0_0_15px_-5px_rgba(0,255,0,0.1)]' : ''}`}>
      
      {/* --- Collapsed Header Strip --- */}
      <div 
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-[#0f0f0f] border-b border-[#1a1a1a] group"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          {/* Status Indicator */}
          <div className={`h-2 w-2 rounded-full ${data.loading ? 'bg-yellow-500 animate-pulse' : 'bg-[#00ff00] shadow-[0_0_8px_#00ff00]'}`} />
          
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold font-mono text-[#eee] group-hover:text-[#00ff00] transition-colors">
                {pool.name}
              </h3>
              <span className="text-[9px] text-[#004400] font-mono border border-[#004400] px-1 rounded">
                1M
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {latestCandle && (
            <div className="text-right">
              <div className="text-sm font-mono font-bold text-[#00ff00]">
                ${formatPrice(latestCandle.close)}
              </div>
              <div className={`flex items-center justify-end gap-1 text-[10px] font-mono ${isPositive ? "text-[#00ff00]" : "text-[#ff3333]"}`}>
                {isPositive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {change > 0 ? "+" : ""}{change.toFixed(2)}%
              </div>
            </div>
          )}
          
          <div className="flex gap-1">
             <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 text-[#006600] hover:text-[#00ff00] hover:bg-[#00ff00]/10"
              onClick={(e) => { e.stopPropagation(); onRefresh(); }}
            >
              <RefreshCw className={`h-3 w-3 ${data.loading ? "animate-spin" : ""}`} />
            </Button>
            {expanded ? <ChevronUp className="h-4 w-4 text-[#006600]" /> : <ChevronDown className="h-4 w-4 text-[#006600]" />}
          </div>
        </div>
      </div>
      
      {/* --- Expanded Dashboard Content --- */}
      {expanded && (
        <div className="p-4 space-y-5 animate-in slide-in-from-top-2 duration-300">
          
          {data.loading && !data.ohlcv ? (
             <div className="flex flex-col items-center justify-center py-12 gap-2">
              <Loader2 className="h-8 w-8 text-[#00ff00] animate-spin" />
              <span className="text-[10px] text-[#006600] font-mono animate-pulse">INITIALIZING DATA STREAM...</span>
            </div>
          ) : data.error ? (
            <div className="p-4 border border-[#ff3333]/30 bg-[#ff3333]/5 text-[#ff3333] font-mono text-xs flex items-center gap-2">
              <Terminal className="h-4 w-4" />
              ERROR: {data.error}
            </div>
          ) : (
            <>
              {/* --- ZONE 1: MARKET ACTION --- */}
              <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                {/* Chart Area */}
                <div className="md:col-span-8 space-y-2">
                   <SectionHeader icon={BarChart3} title="Price Action [OHLCV]" />
                   <div className="flex gap-4 h-full">
                      <div className="flex-1">
                        {data.ohlcv && <MiniCandleChart candles={data.ohlcv} />}
                      </div>
                   </div>
                </div>

                {/* Latest Candle Stats Grid */}
                <div className="md:col-span-4 space-y-2">
                  <SectionHeader icon={Terminal} title="Latest Candle" />
                  <div className="grid grid-cols-2 gap-[1px] bg-[#1a1a1a] border border-[#1a1a1a]">
                    <DataCell label="Open" value={formatPrice(latestCandle?.open)} />
                    <DataCell label="Close" value={formatPrice(latestCandle?.close)} />
                    <DataCell label="High" value={formatPrice(latestCandle?.high)} />
                    <DataCell label="Low" value={formatPrice(latestCandle?.low)} />
                    <div className="col-span-2">
                      <DataCell label="Volume" value={formatNumber(latestCandle?.volume, 0)} icon={Volume2} />
                    </div>
                  </div>
                </div>
              </div>

              {/* --- ZONE 2: TECHNICAL SYSTEMS --- */}
              {data.indicators && (
                <div>
                   <SectionHeader icon={Cpu} title="Technical Systems" />
                   
                   <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {/* Momentum Panel */}
                      <div className="border border-[#1a1a1a] bg-[#0a0a0a] p-2">
                        <div className="text-[9px] text-[#006600] mb-2 flex items-center gap-1 uppercase tracking-widest">
                           <Zap className="h-3 w-3" /> Momentum
                        </div>
                        <div className="space-y-1">
                          <DataCell label="RSI (14)" value={data.indicators.momentum.rsi?.toFixed(1) ?? null} color={getRSIColor(data.indicators.momentum.rsi)} />
                          <div className="grid grid-cols-2 gap-1 mt-1">
                            <DataCell label="Stoch" value={data.indicators.momentum.stoch?.toFixed(0) ?? null} subValue="%" />
                            <DataCell label="MFI" value={data.indicators.momentum.mfi?.toFixed(0) ?? null} />
                          </div>
                        </div>
                      </div>

                      {/* Trend Panel */}
                      <div className="border border-[#1a1a1a] bg-[#0a0a0a] p-2">
                        <div className="text-[9px] text-[#006600] mb-2 flex items-center gap-1 uppercase tracking-widest">
                           <TrendingUp className="h-3 w-3" /> Trend
                        </div>
                        <div className="space-y-1">
                          <DataCell label="MACD" value={data.indicators.trend.macd?.toFixed(4) ?? null} />
                          <DataCell label="ADX" value={data.indicators.trend.adx?.toFixed(2) ?? null} />
                          <div className="flex justify-between text-[9px] font-mono text-[#004400] pt-1 mt-1 border-t border-[#1a1a1a]">
                             <span>MA20: {formatPrice(data.indicators.trend.sma_20)}</span>
                          </div>
                        </div>
                      </div>

                      {/* Volatility Panel */}
                      <div className="border border-[#1a1a1a] bg-[#0a0a0a] p-2">
                        <div className="text-[9px] text-[#006600] mb-2 flex items-center gap-1 uppercase tracking-widest">
                           <Gauge className="h-3 w-3" /> Volatility
                        </div>
                        <div className="space-y-1">
                          <DataCell label="ATR" value={data.indicators.volatility.atr?.toFixed(4) ?? null} />
                          <DataCell label="BB %B" value={data.indicators.volatility.bb_pband?.toFixed(2) ?? null} />
                          <div className="flex justify-between text-[9px] font-mono text-[#004400] pt-1 mt-1 border-t border-[#1a1a1a]">
                             <span>Width: {((data.indicators.volatility.bb_hband! - data.indicators.volatility.bb_lband!) / data.indicators.volatility.bb_mavg! * 100).toFixed(2)}%</span>
                          </div>
                        </div>
                      </div>

                      {/* Volume Panel */}
                      <div className="border border-[#1a1a1a] bg-[#0a0a0a] p-2">
                        <div className="text-[9px] text-[#006600] mb-2 flex items-center gap-1 uppercase tracking-widest">
                           <Activity className="h-3 w-3" /> Volume Flow
                        </div>
                        <div className="space-y-1">
                           <DataCell 
                              label="CMF" 
                              value={data.indicators.volume.cmf?.toFixed(3) ?? null} 
                              color={(data.indicators.volume.cmf || 0) > 0 ? "text-[#00ff00]" : "text-[#ff3333]"}
                            />
                           <DataCell label="VWAP" value={formatPrice(data.indicators.volume.vwap)} />
                        </div>
                      </div>
                   </div>
                </div>
              )}

              {/* --- ZONE 3: SENTIMENT MATRIX --- */}
              {data.sentiment && (
                <div className="relative">
                  <SectionHeader icon={Brain} title={`Sentiment Matrix [${data.sentiment.token_b.symbol || "UNKNOWN"}]`} />
                  
                  {/* Decorative Background for Sentiment */}
                  <div className={`absolute inset-0 border opacity-10 pointer-events-none ${data.sentiment.token_b.score > 0 ? 'border-[#00ff00] bg-[#00ff00]/5' : 'border-[#ff3333] bg-[#ff3333]/5'}`} />

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-2">
                    
                    {/* Hero Sentiment Score */}
                    <div className="md:col-span-1 flex flex-col justify-center items-center bg-[#000] border border-[#1a1a1a] p-4 relative overflow-hidden">
                       <Sparkles className={`h-8 w-8 mb-2 ${getSentimentColor(data.sentiment.token_b.score)}`} />
                       <div className={`text-4xl font-bold font-mono tracking-tighter ${getSentimentColor(data.sentiment.token_b.score)}`}>
                          {data.sentiment.token_b.score > 0 ? "+" : ""}{(data.sentiment.token_b.score * 100).toFixed(0)}
                       </div>
                       <div className="text-[10px] text-[#006600] uppercase tracking-widest mt-1">Social Score</div>
                       
                       <div className="mt-4 w-full">
                          <div className="flex justify-between text-[9px] text-[#004400] mb-1">
                             <span>BEAR</span>
                             <span>BULL</span>
                          </div>
                          <div className="h-1.5 w-full bg-[#111] rounded-full overflow-hidden">
                             <div 
                                className={`h-full transition-all duration-700 ${data.sentiment.token_b.score > 0 ? "bg-[#00ff00]" : "bg-[#ff3333]"}`}
                                style={{ 
                                  width: `${Math.abs(data.sentiment.token_b.score) * 50}%`,
                                  marginLeft: data.sentiment.token_b.score > 0 ? "50%" : `calc(50% - ${Math.abs(data.sentiment.token_b.score) * 50}%)`
                                }}
                             />
                          </div>
                       </div>
                    </div>

                    {/* Stats Grid */}
                    <div className="md:col-span-2 grid grid-cols-2 gap-2">
                       <DataCell 
                          label="Confidence" 
                          value={`${(data.sentiment.token_b.confidence * 100).toFixed(0)}%`} 
                          icon={Target}
                        />
                       <DataCell 
                          label="Dominant Emotion" 
                          value={data.sentiment.token_b.dominant_emotion} 
                          color="text-[#ffaa00] capitalize"
                          icon={ScanLine}
                        />
                       <DataCell 
                          label="Social Vol" 
                          value={data.sentiment.token_b.social_volume?.toLocaleString() ?? null} 
                          icon={Users}
                        />
                       <DataCell 
                          label="Mentions (24h)" 
                          value={data.sentiment.token_b.mentions_24h?.toLocaleString() ?? null} 
                          icon={MessageCircle}
                        />
                       
                       {/* Factors Ticker */}
                       <div className="col-span-2 bg-[#050505] border border-[#1a1a1a] p-2 mt-1">
                          <div className="text-[9px] text-[#006600] mb-1 flex items-center gap-1">
                             <Target className="h-3 w-3" /> DRIVING FACTORS
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {(Array.isArray(data.sentiment.token_b.key_factors) 
                              ? data.sentiment.token_b.key_factors 
                              : JSON.parse(data.sentiment.token_b.key_factors as unknown as string || '[]')
                            ).slice(0, 3).map((factor: string, idx: number) => (
                               <span key={idx} className="text-[10px] text-[#00cc00] font-mono bg-[#00ff00]/10 px-2 py-0.5 rounded border border-[#00ff00]/20">
                                  {factor}
                               </span>
                            ))}
                          </div>
                       </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// --- Main Layout ---

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
    const interval = setInterval(fetchAllData, 60000); 
    return () => clearInterval(interval);
  }, [autoRefresh, fetchAllData]);
  
  return (
    <div className="space-y-8 font-mono bg-black min-h-screen p-4 md:p-8">
      
      {/* Dashboard Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-[#1a1a1a] pb-6">
        <div>
          <h1 className="text-3xl font-bold text-[#00ff00] tracking-tighter flex items-center gap-3">
             <Terminal className="h-8 w-8" />
             MARKET_ANALYTICS<span className="animate-pulse">_</span>
          </h1>
          <p className="text-xs text-[#006600] mt-2 font-mono flex items-center gap-2">
            <span className="w-2 h-2 bg-[#00ff00] rounded-full inline-block" />
            SYSTEM OPERATIONAL // REAL-TIME DATA STREAM
          </p>
        </div>
        
        <div className="flex items-center gap-4 bg-[#0a0a0a] p-2 border border-[#1a1a1a] rounded-sm">
          <label className="flex items-center gap-2 cursor-pointer select-none group">
            <div className={`w-3 h-3 border border-[#006600] flex items-center justify-center ${autoRefresh ? 'bg-[#00ff00]/20' : ''}`}>
               {autoRefresh && <div className="w-1.5 h-1.5 bg-[#00ff00]" />}
            </div>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="hidden"
            />
            <span className="text-[10px] text-[#006600] group-hover:text-[#00ff00] transition-colors">AUTO_SYNC [60s]</span>
          </label>
          
          <div className="h-4 w-px bg-[#1a1a1a]" />
          
          <Button
            onClick={fetchAllData}
            variant="ghost"
            size="sm"
            className="h-6 text-[10px] border border-[#00ff00]/30 text-[#00ff00] hover:bg-[#00ff00]/10 hover:border-[#00ff00]"
          >
            <RefreshCw className="h-3 w-3 mr-2" />
            FORCE_REFRESH
          </Button>
        </div>
      </div>
      
      {/* Grid Layout for Pools */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
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