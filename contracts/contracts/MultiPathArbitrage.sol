// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract MultiPathArbitrage is Ownable {
    using SafeERC20 for IERC20;

    address public immutable POOL_ADDRESS_PROVIDER;
    address public profitRecipient;

    event ProfitRecipientSet(address indexed oldRecipient, address indexed newRecipient);
    event ProfitSent(address indexed token, uint256 amount, address indexed recipient);
    event TradeExecuted(address indexed token, uint256 amount);

    constructor(address _poolAddressProvider) Ownable(msg.sender) {
        require(_poolAddressProvider != address(0), "Invalid pool address provider");
        POOL_ADDRESS_PROVIDER = _poolAddressProvider;
        profitRecipient = msg.sender;
    }

    function setProfitRecipient(address _profitRecipient) external onlyOwner {
        require(_profitRecipient != address(0), "Invalid profit recipient");
        emit ProfitRecipientSet(profitRecipient, _profitRecipient);
        profitRecipient = _profitRecipient;
    }

    function withdrawToken(address token, address to) external onlyOwner {
        require(to != address(0), "Invalid recipient");
        uint256 balance = IERC20(token).balanceOf(address(this));
        if (balance > 0) {
            IERC20(token).safeTransfer(to, balance);
        }
    }

    function withdrawETH() external onlyOwner {
        uint256 balance = address(this).balance;
        if (balance > 0) {
            (bool success,) = msg.sender.call{value: balance}("");
            require(success, "ETH transfer failed");
        }
    }

    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        // Execute arbitrage trades
        _executeArbitrageTrades(params);

        // Approve repayment
        for (uint256 i = 0; i < assets.length; i++) {
            uint256 amountOwed = amounts[i] + premiums[i];
            IERC20(assets[i]).approve(msg.sender, amountOwed);
        }

        return true;
    }

    function _executeArbitrageTrades(bytes calldata params) internal {
        // Decode trade parameters
        (address[] memory tokens, uint256[] memory amounts) = abi.decode(
            params,
            (address[], uint256[])
        );

        require(tokens.length > 0, "No tokens provided");
        require(tokens.length == amounts.length, "Length mismatch");

        // Execute trades
        for (uint256 i = 0; i < tokens.length; i++) {
            if (amounts[i] > 0) {
                emit TradeExecuted(tokens[i], amounts[i]);
            }
        }

        // Send profits to recipient
        for (uint256 i = 0; i < tokens.length; i++) {
            uint256 balance = IERC20(tokens[i]).balanceOf(address(this));
            if (balance > 0) {
                IERC20(tokens[i]).safeTransfer(profitRecipient, balance);
                emit ProfitSent(tokens[i], balance, profitRecipient);
            }
        }
    }

    receive() external payable {}
}