// Small CLI shim so Flask (Python) can trigger a GenLayerJS call without
// needing a Python GenLayer SDK. Every result — success or failure — is
// printed to stdout as a single line of JSON, so the Python side just needs
// to parse one line rather than scrape human-readable output.
//
// Usage:
//   node dispute-relay.js submit <disputeId> <roleOffer> <candidateAsk> <reason>
//   node dispute-relay.js verdict <disputeId>
//
// Required environment variables:
//   GENLAYER_CONTRACT_ADDR  - the deployed DisputeResolver contract address
//   GENLAYER_PRIVATE_KEY    - a Studionet test account private key
//                             (use a fresh key generated in Studio — never
//                             reuse a key that has been shared or committed)

import { createClient, createAccount } from 'genlayer-js';
import { studionet } from 'genlayer-js/chains';
import { TransactionStatus } from 'genlayer-js/types';

const CONTRACT_ADDR = process.env.GENLAYER_CONTRACT_ADDR;
const PRIVATE_KEY = process.env.GENLAYER_PRIVATE_KEY;

function fail(message) {
    console.log(JSON.stringify({ ok: false, error: message }));
    process.exit(1);
}

if (!CONTRACT_ADDR) fail('Missing GENLAYER_CONTRACT_ADDR environment variable');
if (!PRIVATE_KEY) fail('Missing GENLAYER_PRIVATE_KEY environment variable');

const [, , command, ...args] = process.argv;

async function main() {
    const account = createAccount(PRIVATE_KEY);
    const client = createClient({ chain: studionet, account });

    // Required once before any contract interaction, per GenLayerJS docs.
    await client.initializeConsensusSmartContract();

    if (command === 'submit') {
        const [disputeId, roleOffer, candidateAsk, reason] = args;
        if (!disputeId || roleOffer === undefined || candidateAsk === undefined) {
            fail('submit requires: <disputeId> <roleOffer> <candidateAsk> <reason>');
        }

        const txHash = await client.writeContract({
            address: CONTRACT_ADDR,
            functionName: 'resolve',
            args: [disputeId, Number(roleOffer), Number(candidateAsk), reason ?? ''],
        });

        // This blocks until the validators reach consensus. With an LLM call
        // inside the contract, this can take a while — the retry/interval
        // below allows up to ~4 minutes before giving up.
        const receipt = await client.waitForTransactionReceipt({
            hash: txHash,
            status: TransactionStatus.ACCEPTED,
            retries: 50,
            interval: 5000,
        });

        console.log(JSON.stringify({ ok: true, txHash, status: 'ACCEPTED', receipt }));
        return;
    }

    if (command === 'verdict') {
        const [disputeId] = args;
        if (!disputeId) fail('verdict requires: <disputeId>');

        const verdict = await client.readContract({
            address: CONTRACT_ADDR,
            functionName: 'get_verdict',
            args: [disputeId],
        });

        console.log(JSON.stringify({ ok: true, verdict }));
        return;
    }

    fail(`Unknown command: ${command}. Use "submit" or "verdict".`);
}

main().catch((err) => {
    fail(err && err.message ? err.message : String(err));
});