const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("ViolationLogger", function () {
  async function deploy() {
    const ViolationLogger = await ethers.getContractFactory("ViolationLogger");
    return ViolationLogger.deploy();
  }

  it("stores a violation once and rejects duplicates", async function () {
    const logger = await deploy();
    const eventId = ethers.id("event-001");
    const violationTypeHash = ethers.id("helmet_not_observed_on_associated_rider");
    const evidenceHash = ethers.id("evidence-hash");
    const plateHash = ethers.id("plate-hash");
    const timestamp = 1_700_000_000n;

    await expect(
      logger.logViolation(eventId, timestamp, violationTypeHash, evidenceHash, plateHash)
    ).to.emit(logger, "ViolationLogged");

    const record = await logger.getViolation(eventId);
    expect(record.exists).to.equal(true);
    expect(record.timestampUtc).to.equal(timestamp);
    expect(record.recordedBy).to.properAddress;

    await expect(
      logger.logViolation(eventId, timestamp, violationTypeHash, evidenceHash, plateHash)
    ).to.be.revertedWithCustomError(logger, "DuplicateEvent");
  });

  it("rejects non-owner writes", async function () {
    const logger = await deploy();
    const [, other] = await ethers.getSigners();
    const eventId = ethers.id("event-002");
    await expect(
      logger
        .connect(other)
        .logViolation(eventId, 1n, ethers.ZeroHash, ethers.ZeroHash, ethers.ZeroHash)
    ).to.be.revertedWithCustomError(logger, "NotOwner");
  });
});
