// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
    function transfer(address recipient, uint256 amount) external returns (bool);
}

contract CrossChainAtomicSwap {
    enum SwapState { INACTIVE, INITIATED, COMMITTED, COMPLETED, REFUNDED }

    struct Swap {
        address initiator;
        address participant;
        address tokenAddress;
        uint256 amount;
        uint256 timelock;
        bytes32 hashedSecret;
        SwapState state;
        uint256 sourceChainId;
        uint256 destinationChainId;
    }

    mapping(bytes32 => Swap) public swaps;
    address public bridgeAddress;
    address public owner;

    event SwapInitiated(bytes32 indexed swapId, address indexed initiator, address indexed participant, uint256 amount, bytes32 hashedSecret, uint256 sourceChainId, uint256 destinationChainId);
    event SwapCommitted(bytes32 indexed swapId);
    event SwapCompleted(bytes32 indexed swapId);
    event SwapRefunded(bytes32 indexed swapId);
    event BridgeAddressUpdated(address indexed oldAddress, address indexed newAddress);

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this function");
        _;
    }

    constructor(address _bridgeAddress) {
        bridgeAddress = _bridgeAddress;
        owner = msg.sender;
    }

    function updateBridgeAddress(address _newBridgeAddress) external onlyOwner {
        require(_newBridgeAddress != address(0), "Invalid bridge address");
        address oldAddress = bridgeAddress;
        bridgeAddress = _newBridgeAddress;
        emit BridgeAddressUpdated(oldAddress, _newBridgeAddress);
    }

    function initiateSwap(
        address _participant,
        address _tokenAddress,
        uint256 _amount,
        uint256 _timelock,
        bytes32 _hashedSecret,
        uint256 _destinationChainId
    ) external {
        require(_amount > 0, "Amount must be greater than 0");
        require(_timelock > block.timestamp, "Timelock must be in the future");
        require(_participant != address(0), "Invalid participant address");
        require(_tokenAddress != address(0), "Invalid token address");

        bytes32 swapId = keccak256(abi.encodePacked(msg.sender, _participant, _tokenAddress, _amount, _timelock, _hashedSecret, block.chainid, _destinationChainId));
        require(swaps[swapId].state == SwapState.INACTIVE, "Swap already exists");

        require(IERC20(_tokenAddress).transferFrom(msg.sender, address(this), _amount), "Token transfer failed");

        swaps[swapId] = Swap({
            initiator: msg.sender,
            participant: _participant,
            tokenAddress: _tokenAddress,
            amount: _amount,
            timelock: _timelock,
            hashedSecret: _hashedSecret,
            state: SwapState.INITIATED,
            sourceChainId: block.chainid,
            destinationChainId: _destinationChainId
        });

        emit SwapInitiated(swapId, msg.sender, _participant, _amount, _hashedSecret, block.chainid, _destinationChainId);
    }

    function commitSwap(bytes32 _swapId, bytes memory _signature) external {
        Swap storage swap = swaps[_swapId];
        require(swap.state == SwapState.INITIATED, "Invalid swap state");
        require(block.timestamp < swap.timelock, "Swap expired");

        bytes32 message = keccak256(abi.encodePacked(_swapId));
        require(recoverSigner(message, _signature) == bridgeAddress, "Invalid signature");

        swap.state = SwapState.COMMITTED;
        emit SwapCommitted(_swapId);
    }

    function completeSwap(bytes32 _swapId, bytes32 _secret) external {
        Swap storage swap = swaps[_swapId];
        require(swap.state == SwapState.COMMITTED, "Invalid swap state");
        require(block.timestamp < swap.timelock, "Swap expired");
        require(keccak256(abi.encodePacked(_secret)) == swap.hashedSecret, "Invalid secret");

        swap.state = SwapState.COMPLETED;
        require(IERC20(swap.tokenAddress).transfer(swap.participant, swap.amount), "Token transfer failed");

        emit SwapCompleted(_swapId);
    }

    function refundSwap(bytes32 _swapId) external {
        Swap storage swap = swaps[_swapId];
        require(swap.state == SwapState.INITIATED || swap.state == SwapState.COMMITTED, "Invalid swap state");
        require(swap.initiator == msg.sender, "Only initiator can refund");
        require(block.timestamp >= swap.timelock, "Timelock not expired");

        swap.state = SwapState.REFUNDED;
        require(IERC20(swap.tokenAddress).transfer(swap.initiator, swap.amount), "Token transfer failed");

        emit SwapRefunded(_swapId);
    }

    function recoverSigner(bytes32 message, bytes memory signature) internal pure returns (address) {
        require(signature.length == 65, "Invalid signature length");

        bytes32 r;
        bytes32 s;
        uint8 v;

        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }

        if (v < 27) {
            v += 27;
        }

        require(v == 27 || v == 28, "Invalid signature 'v' value");

        return ecrecover(keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", message)), v, r, s);
    }
}
