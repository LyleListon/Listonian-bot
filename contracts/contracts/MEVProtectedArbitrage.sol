// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import "./FlashLoanArbitrage.sol";

contract MEVProtectedArbitrage is FlashLoanArbitrage {
    // MEV Protection Settings
    uint256 public maxGasPrice;
    address public flashbotsRelayer;
    bool public usePrivateMempool;
    uint256 public minProfitBasisPoints;
    uint256 public maxTradeSize;

    event MEVProtectionUpdated(
        address flashbotsRelayer,
        bool usePrivateMempool,
        uint256 maxGasPrice
    );

    constructor(
        address _addressProvider,
        address _flashbotsRelayer,
        uint256 _maxGasPrice,
        uint256 _minProfitBasisPoints,
        uint256 _maxTradeSize
    ) FlashLoanArbitrage(_addressProvider) {
        require(_addressProvider != address(0), "Invalid address provider");
        require(_maxGasPrice > 0, "Invalid max gas price");
        require(_minProfitBasisPoints > 0, "Invalid min profit basis points");
        require(_maxTradeSize > 0, "Invalid max trade size");

        flashbotsRelayer = _flashbotsRelayer;
        maxGasPrice = _maxGasPrice;
        usePrivateMempool = true;
        minProfitBasisPoints = _minProfitBasisPoints;
        maxTradeSize = _maxTradeSize;

        emit MEVProtectionUpdated(
            _flashbotsRelayer,
            usePrivateMempool,
            _maxGasPrice
        );
    }

    modifier onlyFlashbotsRelayer() {
        require(
            msg.sender == flashbotsRelayer,
            "Only Flashbots relayer can call this"
        );
        _;
    }

    modifier protectedExecution() {
        require(
            tx.gasprice <= maxGasPrice,
            "Gas price too high"
        );
        require(
            !usePrivateMempool || msg.sender == flashbotsRelayer,
            "Must use Flashbots relayer"
        );
        _;
    }

    function setMEVProtection(
        address _flashbotsRelayer,
        bool _usePrivateMempool,
        uint256 _maxGasPrice
    ) external onlyOwner {
        require(_maxGasPrice > 0, "Invalid max gas price");
        flashbotsRelayer = _flashbotsRelayer;
        usePrivateMempool = _usePrivateMempool;
        maxGasPrice = _maxGasPrice;

        emit MEVProtectionUpdated(
            _flashbotsRelayer,
            _usePrivateMempool,
            _maxGasPrice
        );
    }

    function executeFlashLoan(
        address asset,
        uint256 amount,
        bytes calldata params
    ) external override protectedExecution onlyOwner {
        require(amount <= maxTradeSize, "Amount exceeds max trade size");
        
        // Decode expected profit from params
        (, , , uint256 expectedProfit) = abi.decode(
            params,
            (address[], uint256[], bool[], uint256)
        );

        // Verify minimum profit
        require(
            expectedProfit >= (amount * minProfitBasisPoints) / 10000,
            "Expected profit too low"
        );

        // Execute flash loan with MEV protection
        POOL.flashLoanSimple(
            address(this),
            asset,
            amount,
            params,
            0
        );
    }

    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address /* initiator */,
        bytes calldata params
    ) public virtual override returns (bool) {
        require(
            tx.gasprice <= maxGasPrice,
            "Gas price exceeded during execution"
        );

        return super.executeOperation(asset, amount, premium, address(0), params);
    }

    // Enhanced trade execution with MEV protection
    function executeTrades(
        address asset,
        address[] memory dexPaths,
        uint256[] memory amounts,
        bool[] memory isV3
    ) internal virtual override {
        require(
            tx.gasprice <= maxGasPrice,
            "Gas price exceeded during trades"
        );

        super.executeTrades(asset, dexPaths, amounts, isV3);
    }

    // Getter functions for MEV protection settings
    function getMEVProtectionSettings() external view returns (
        address _flashbotsRelayer,
        bool _usePrivateMempool,
        uint256 _maxGasPrice,
        uint256 _minProfitBasisPoints,
        uint256 _maxTradeSize
    ) {
        return (
            flashbotsRelayer,
            usePrivateMempool,
            maxGasPrice,
            minProfitBasisPoints,
            maxTradeSize
        );
    }
}