require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config({ path: require("path").join(__dirname, "..", ".env") });

const { SEPOLIA_RPC_URL, DEPLOYER_PRIVATE_KEY } = process.env;

const networks = { hardhat: {} };
if (SEPOLIA_RPC_URL && DEPLOYER_PRIVATE_KEY) {
  networks.sepolia = {
    url: SEPOLIA_RPC_URL,
    accounts: [DEPLOYER_PRIVATE_KEY],
  };
}

module.exports = {
  solidity: "0.8.24",
  networks,
};
