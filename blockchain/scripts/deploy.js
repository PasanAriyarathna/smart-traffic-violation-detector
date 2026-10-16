const hre = require("hardhat");

async function main() {
  const ViolationLogger = await hre.ethers.getContractFactory("ViolationLogger");
  const logger = await ViolationLogger.deploy();
  await logger.waitForDeployment();
  const address = await logger.getAddress();
  console.log("ViolationLogger deployed to:", address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
