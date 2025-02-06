import { ethers } from 'ethers';
import { Token, Pair, Route, Trade } from '@uniswap/sdk';
import { Pool, Route as RouteV3, Trade as TradeV3 } from '@uniswap/v3-sdk';
import { Token as PancakeToken, Pair as PancakePair } from '@pancakeswap/sdk';
import { Pool as PancakePool } from '@pancakeswap/v3-sdk';

// Router ABIs
import UniswapV2RouterABI from '../../../abi/IUniswapV2Router.json';
import UniswapV3RouterABI from '../../../abi/IUniswapV3Router.json';
import PancakeV2RouterABI from '../../../abi/pancakeswap_v2_router.json';
import PancakeV3RouterABI from '../../../abi/pancakeswap_v3_router.json';

// Environment variables
const {
  REACT_APP_UNISWAP_V2_ROUTER,
  REACT_APP_UNISWAP_V3_ROUTER,
  REACT_APP_PANCAKESWAP_V2_ROUTER,
  REACT_APP_PANCAKESWAP_V3_ROUTER,
  REACT_APP_NETWORK_RPC_URL,
  REACT_APP_CHAIN_ID,
} = process.env;

// Initialize provider
const provider = new ethers.providers.JsonRpcProvider(
  REACT_APP_NETWORK_RPC_URL,
  parseInt(REACT_APP_CHAIN_ID || '8453')
);

// Router interfaces
interface RouterConfig {
  address: string;
  abi: any;
  version: 'v2' | 'v3';
  protocol: 'uniswap' | 'pancakeswap';
}

const routers: { [key: string]: RouterConfig } = {
  uniswapV2: {
    address: REACT_APP_UNISWAP_V2_ROUTER || '',
    abi: UniswapV2RouterABI,
    version: 'v2',
    protocol: 'uniswap'
  },
  uniswapV3: {
    address: REACT_APP_UNISWAP_V3_ROUTER || '',
    abi: UniswapV3RouterABI,
    version: 'v3',
    protocol: 'uniswap'
  },
  pancakeV2: {
    address: REACT_APP_PANCAKESWAP_V2_ROUTER || '',
    abi: PancakeV2RouterABI,
    version: 'v2',
    protocol: 'pancakeswap'
  },
  pancakeV3: {
    address: REACT_APP_PANCAKESWAP_V3_ROUTER || '',
    abi: PancakeV3RouterABI,
    version: 'v3',
    protocol: 'pancakeswap'
  }
};

// Router instances
const routerInstances: { [key: string]: ethers.Contract } = {};

// Initialize router instances
Object.entries(routers).forEach(([key, config]) => {
  routerInstances[key] = new ethers.Contract(
    config.address,
    config.abi,
    provider
  );
});

export interface QuoteResult {
  amountOut: string;
  path: string[];
  priceImpact: string;
  fee?: number;
}

export class DEXManager {
  private provider: ethers.providers.JsonRpcProvider;

  constructor() {
    this.provider = provider;
  }

  /**
   * Get quote for a token swap
   */
  async getQuote(
    routerKey: string,
    tokenIn: string,
    tokenOut: string,
    amountIn: string,
    options?: {
      slippage?: number;
      deadline?: number;
      fee?: number; // For V3 only
    }
  ): Promise<QuoteResult> {
    const router = routers[routerKey];
    const contract = routerInstances[routerKey];

    if (!router || !contract) {
      throw new Error(`Router ${routerKey} not found`);
    }

    try {
      if (router.version === 'v2') {
        return await this.getV2Quote(
          contract,
          tokenIn,
          tokenOut,
          amountIn,
          options
        );
      } else {
        return await this.getV3Quote(
          contract,
          tokenIn,
          tokenOut,
          amountIn,
          options
        );
      }
    } catch (error) {
      console.error(`Error getting quote from ${routerKey}:`, error);
      throw error;
    }
  }

  /**
   * Get quote from V2 router
   */
  private async getV2Quote(
    contract: ethers.Contract,
    tokenIn: string,
    tokenOut: string,
    amountIn: string,
    options?: {
      slippage?: number;
      deadline?: number;
    }
  ): Promise<QuoteResult> {
    const path = [tokenIn, tokenOut];
    const amounts = await contract.getAmountsOut(amountIn, path);
    const amountOut = amounts[amounts.length - 1];

    // Calculate price impact
    const reservesRaw = await contract.getReserves();
    const reserves = {
      reserve0: reservesRaw[0],
      reserve1: reservesRaw[1]
    };
    const priceImpact = this.calculateV2PriceImpact(
      amountIn,
      amountOut,
      reserves
    );

    return {
      amountOut: amountOut.toString(),
      path,
      priceImpact: priceImpact.toString()
    };
  }

  /**
   * Get quote from V3 router
   */
  private async getV3Quote(
    contract: ethers.Contract,
    tokenIn: string,
    tokenOut: string,
    amountIn: string,
    options?: {
      slippage?: number;
      deadline?: number;
      fee?: number;
    }
  ): Promise<QuoteResult> {
    const fee = options?.fee || 3000; // Default to 0.3%
    const quoterParams = {
      tokenIn,
      tokenOut,
      fee,
      amountIn,
      sqrtPriceLimitX96: 0
    };

    const quote = await contract.callStatic.quoteExactInputSingle(quoterParams);
    const priceImpact = await this.calculateV3PriceImpact(
      contract,
      tokenIn,
      tokenOut,
      amountIn,
      quote.amountOut,
      fee
    );

    return {
      amountOut: quote.amountOut.toString(),
      path: [tokenIn, tokenOut],
      priceImpact: priceImpact.toString(),
      fee
    };
  }

  /**
   * Calculate price impact for V2
   */
  private calculateV2PriceImpact(
    amountIn: string,
    amountOut: string,
    reserves: { reserve0: string; reserve1: string }
  ): number {
    const k = BigInt(reserves.reserve0) * BigInt(reserves.reserve1);
    const newReserve0 = BigInt(reserves.reserve0) + BigInt(amountIn);
    const newReserve1 = k / newReserve0;
    const expectedOut = BigInt(reserves.reserve1) - newReserve1;
    const impact = (BigInt(amountOut) - expectedOut) * BigInt(10000) / expectedOut;
    return Number(impact) / 10000;
  }

  /**
   * Calculate price impact for V3
   */
  private async calculateV3PriceImpact(
    contract: ethers.Contract,
    tokenIn: string,
    tokenOut: string,
    amountIn: string,
    amountOut: string,
    fee: number
  ): Promise<number> {
    // Get pool state
    const slot0 = await contract.slot0();
    const sqrtPriceX96 = slot0.sqrtPriceX96;
    const tick = slot0.tick;

    // Calculate price impact using tick math
    const tickSpacing = fee / 50;
    const tickLower = Math.floor(tick / tickSpacing) * tickSpacing;
    const tickUpper = tickLower + tickSpacing;

    const priceBeforeX96 = sqrtPriceX96;
    const priceAfterX96 = await contract.getSqrtRatioAtTick(tickUpper);

    const priceImpact = (Number(priceAfterX96) - Number(priceBeforeX96)) / Number(priceBeforeX96);
    return priceImpact;
  }

  /**
   * Get supported routers
   */
  getSupportedRouters() {
    return Object.keys(routers);
  }

  /**
   * Get router details
   */
  getRouterDetails(routerKey: string) {
    return routers[routerKey];
  }
}

export const dexManager = new DEXManager();