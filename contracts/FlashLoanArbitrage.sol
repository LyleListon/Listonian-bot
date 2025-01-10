// SPDX-License-Identifier: MIT
pragma solidity 0.8.19;

// DEX Interfaces
interface IBaseSwapRouter {
    function swapExactTokensForTokens(
        uint amountIn,
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts);
}

interface IPancakeV3Router {
    struct ExactInputSingleParams {
        address tokenIn;
        address tokenOut;
        uint24 fee;
        address recipient;
        uint256 deadline;
        uint256 amountIn;
        uint256 amountOutMinimum;
        uint160 sqrtPriceLimitX96;
    }

    function exactInputSingle(ExactInputSingleParams calldata params)
        external
        payable
        returns (uint256 amountOut);
}

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

interface IPool {
    function flashLoanSimple(
        address receiverAddress,
        address asset,
        uint256 amount,
        bytes calldata params,
        uint16 referralCode
    ) external;
}

interface IPoolAddressesProvider {
    function getPool() external view returns (address);
}

contract FlashLoanArbitrage {
    using SafeERC20 for IERC20;

    address public owner;
    IPool public immutable POOL;
    
    event FlashLoanExecuted(address token, uint256 amount, uint256 profit);

    constructor(address _addressProvider) {
        owner = msg.sender;
        POOL = IPool(IPoolAddressesProvider(_addressProvider).getPool());
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address /* initiator */,
        bytes calldata params
    ) external returns (bool) {
        // Decode params
        (address[] memory dexPaths, uint256[] memory amounts, bool[] memory isV3) = abi.decode(
            params,
            (address[], uint256[], bool[])
        );

        // Ensure we have enough allowance to repay the flash loan
        uint256 amountToRepay = amount + premium;
        IERC20(asset).approve(address(POOL), amountToRepay);

        // Execute arbitrage trades
        executeTrades(asset, dexPaths, amounts, isV3);
        uint256 finalBalance = IERC20(asset).balanceOf(address(this));

        // Verify profit
        require(finalBalance >= amountToRepay, "Insufficient funds to repay flash loan");
        uint256 profit = finalBalance - amountToRepay;
        emit FlashLoanExecuted(asset, amount, profit);

        return true;
    }

    function executeTrades(
        address asset,
        address[] memory dexPaths,
        uint256[] memory amounts,
        bool[] memory isV3
    ) internal {
        require(dexPaths.length == amounts.length && amounts.length == isV3.length, "Invalid parameters");

        for (uint i = 0; i < dexPaths.length; i++) {
            if (isV3[i]) {
                executeV3Trade(asset, dexPaths[i], amounts[i]);
            } else {
                executeV2Trade(asset, dexPaths[i], amounts[i]);
            }
        }
    }

    // Token addresses
    address public WETH;
    address public USDC;

    function setTokenAddresses(address _weth, address _usdc) external onlyOwner {
        WETH = _weth;
        USDC = _usdc;
    }

    function executeV3Trade(address asset, address router, uint256 amount) internal {
        // Approve router
        IERC20(asset).approve(router, amount);
        
        // Determine token path
        address tokenIn = asset;
        address tokenOut = asset == WETH ? USDC : WETH;
        
        // Execute trade through PancakeSwap V3
        IPancakeV3Router(router).exactInputSingle(
            IPancakeV3Router.ExactInputSingleParams({
                tokenIn: tokenIn,
                tokenOut: tokenOut,
                fee: 500, // 0.05%
                recipient: address(this),
                deadline: block.timestamp + 300,
                amountIn: amount,
                amountOutMinimum: 0, // No slippage check in flash loan
                sqrtPriceLimitX96: 0
            })
        );
    }

    function executeV2Trade(address asset, address router, uint256 amount) internal {
        // Approve router
        IERC20(asset).approve(router, amount);
        
        // Create path
        address[] memory path = new address[](2);
        path[0] = asset;
        path[1] = asset == WETH ? USDC : WETH;
        
        // Execute trade through BaseSwap V2
        IBaseSwapRouter(router).swapExactTokensForTokens(
            amount,
            0, // No slippage check in flash loan
            path,
            address(this),
            block.timestamp + 300
        );
    }

    function executeFlashLoan(
        address asset,
        uint256 amount,
        bytes calldata params
    ) external onlyOwner {
        POOL.flashLoanSimple(
            address(this),
            asset,
            amount,
            params,
            0
        );
    }

    // Emergency functions
    function withdrawToken(address token, uint256 amount) external onlyOwner {
        IERC20(token).safeTransfer(owner, amount);
    }

    function withdrawETH() external onlyOwner {
        payable(owner).transfer(address(this).balance);
    }

    // Required for receiving ETH
    receive() external payable {}
}
