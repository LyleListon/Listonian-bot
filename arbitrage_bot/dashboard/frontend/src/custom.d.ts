// Allow importing JSON files
declare module "*.json" {
    const value: any;
    export default value;
}

// Environment variables
interface ProcessEnv {
    REACT_APP_UNISWAP_V2_ROUTER: string;
    REACT_APP_UNISWAP_V3_ROUTER: string;
    REACT_APP_PANCAKESWAP_V2_ROUTER: string;
    REACT_APP_PANCAKESWAP_V3_ROUTER: string;
    REACT_APP_NETWORK_RPC_URL: string;
    REACT_APP_CHAIN_ID: string;
    REACT_APP_WS_URL: string;
    REACT_APP_API_URL: string;
    [key: string]: string | undefined;
}

// Extend NodeJS namespace
declare namespace NodeJS {
    interface ProcessEnv {
        REACT_APP_UNISWAP_V2_ROUTER: string;
        REACT_APP_UNISWAP_V3_ROUTER: string;
        REACT_APP_PANCAKESWAP_V2_ROUTER: string;
        REACT_APP_PANCAKESWAP_V3_ROUTER: string;
        REACT_APP_NETWORK_RPC_URL: string;
        REACT_APP_CHAIN_ID: string;
        REACT_APP_WS_URL: string;
        REACT_APP_API_URL: string;
        [key: string]: string | undefined;
    }
}

// DEX SDK types
declare module '@uniswap/sdk' {
    export class Token {
        constructor(chainId: number, address: string, decimals: number, symbol?: string, name?: string);
    }
    export class Pair {
        static getAddress(tokenA: Token, tokenB: Token): string;
    }
    export class Route {
        constructor(pairs: Pair[], input: Token);
    }
    export class Trade {
        static bestTradeExactIn(
            pairs: Pair[],
            amountIn: any,
            tokenOut: Token,
            options?: { maxHops?: number }
        ): Trade[];
    }
}

declare module '@uniswap/v3-sdk' {
    export class Pool {
        static getAddress(tokenA: Token, tokenB: Token, fee: number): string;
    }
    export class Route {
        constructor(pools: Pool[], tokenIn: Token, tokenOut: Token);
    }
    export class Trade {
        static bestTradeExactIn(
            pools: Pool[],
            amountIn: any,
            tokenOut: Token,
            options?: { maxHops?: number }
        ): Trade[];
    }
}

declare module '@pancakeswap/sdk' {
    export class Token {
        constructor(chainId: number, address: string, decimals: number, symbol?: string, name?: string);
    }
    export class Pair {
        static getAddress(tokenA: Token, tokenB: Token): string;
    }
}

declare module '@pancakeswap/v3-sdk' {
    export class Pool {
        static getAddress(tokenA: Token, tokenB: Token, fee: number): string;
    }
}