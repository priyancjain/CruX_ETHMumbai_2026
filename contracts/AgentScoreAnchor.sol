// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title AgentScoreAnchor — On-chain score attestation for AI agents
/// @notice Stores keccak256 hashes of credit scores on Base Sepolia/mainnet
/// @dev Deployed by AgentScore backend; only owner can write scores
contract AgentScoreAnchor {

    struct ScoreRecord {
        bytes32 scoreHash;
        uint256 score;
        uint256 scoredAt;
        string  tier;
    }

    address public owner;

    /// @notice Latest anchored score per wallet
    mapping(address => ScoreRecord) public latestScore;

    /// @notice Full history of score hashes per wallet
    mapping(address => bytes32[]) public scoreHashes;

    /// @notice Total number of scores anchored
    uint256 public totalAnchored;

    event ScoreAnchored(
        address indexed wallet,
        bytes32 indexed scoreHash,
        uint256 score,
        string  tier,
        uint256 scoredAt
    );

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "AgentScoreAnchor: not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    /// @notice Anchor a credit score on-chain
    /// @param wallet  The agent's wallet address
    /// @param score   Credit score 0-1000
    /// @param tier    Tier string: "S", "A", "B", "C", or "D"
    /// @param scoredAt Unix timestamp when score was computed
    function anchorScore(
        address wallet,
        uint256 score,
        string calldata tier,
        uint256 scoredAt
    ) external onlyOwner {
        require(score <= 1000, "Score out of range");
        require(wallet != address(0), "Invalid wallet");

        bytes32 scoreHash = keccak256(abi.encodePacked(wallet, score, scoredAt));

        latestScore[wallet] = ScoreRecord({
            scoreHash: scoreHash,
            score: score,
            scoredAt: scoredAt,
            tier: tier
        });

        scoreHashes[wallet].push(scoreHash);
        totalAnchored++;

        emit ScoreAnchored(wallet, scoreHash, score, tier, scoredAt);
    }

    /// @notice Verify a score by recomputing the hash
    /// @return valid True if the hash matches the latest anchored score
    function verifyScore(
        address wallet,
        uint256 score,
        uint256 scoredAt
    ) external view returns (bool valid) {
        bytes32 expectedHash = keccak256(abi.encodePacked(wallet, score, scoredAt));
        return latestScore[wallet].scoreHash == expectedHash;
    }

    /// @notice Get the number of scores anchored for a wallet
    function getScoreCount(address wallet) external view returns (uint256) {
        return scoreHashes[wallet].length;
    }

    /// @notice Get all score hashes for a wallet
    function getScoreHistory(address wallet) external view returns (bytes32[] memory) {
        return scoreHashes[wallet];
    }

    /// @notice Transfer ownership to a new address
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "Invalid new owner");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }
}
