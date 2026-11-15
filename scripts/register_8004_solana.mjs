import fs from 'node:fs';
import path from 'node:path';
import bs58 from 'bs58';
import { Connection, Keypair, LAMPORTS_PER_SOL } from '@solana/web3.js';
import { SolanaSDK } from '8004-solana';

const WALLET_PATH = path.resolve('data/bot_wallet_solana.json');
const RECEIPT_PATH = path.resolve('data/solana_8004_registration.json');
const METADATA_URI =
  'https://agent-security-gate-x402-212942243360.asia-northeast3.run.app/.well-known/erc8004-registration.json';
const RPC_URL = process.env.SOLANA_RPC_URL || 'https://api.mainnet-beta.solana.com';

async function main() {
  const raw = JSON.parse(fs.readFileSync(WALLET_PATH, 'utf8'));
  const secretBytes = bs58.decode(raw.private_key_b58);
  const signer = Keypair.fromSecretKey(secretBytes);

  const connection = new Connection(RPC_URL, 'confirmed');
  const balanceBefore = await connection.getBalance(signer.publicKey);
  console.log(`Owner Pubkey: ${signer.publicKey.toBase58()}`);
  console.log(`Balance Before: ${(balanceBefore / LAMPORTS_PER_SOL).toFixed(6)} SOL`);

  if (balanceBefore < 0.01 * LAMPORTS_PER_SOL) {
    throw new Error('Insufficient SOL balance for 8004-solana mainnet registration.');
  }

  const sdk = new SolanaSDK({
    cluster: 'mainnet-beta',
    rpcUrl: RPC_URL,
    signer,
  });

  console.log(`Registering A.GRID on Solana Mainnet 8004 Registry...`);
  console.log(`Metadata URI: ${METADATA_URI}`);

  const result = await sdk.registerAgent(METADATA_URI, {
    atomEnabled: true,
  });

  const assetPubkey = result.asset ? result.asset.toBase58() : null;
  const signature = result.signature || (result.signatures && result.signatures[0]) || null;

  const balanceAfter = await connection.getBalance(signer.publicKey);
  const costSol = (balanceBefore - balanceAfter) / LAMPORTS_PER_SOL;

  console.log('Registration Result:', {
    success: result.success ?? Boolean(signature),
    asset: assetPubkey,
    signature,
    costSol: Number(costSol.toFixed(6)),
    balanceAfterSol: Number((balanceAfter / LAMPORTS_PER_SOL).toFixed(6)),
  });

  const receipt = {
    cluster: 'mainnet-beta',
    programId: '8oo4dC4JvBLwy5tGgiH3WwK4B9PWxL9Z4XjA2jzkQMbQ',
    atomProgramId: 'AToMw53aiPQ8j7iHVb4fGt6nzUNxUhcPc3tbPBZuzVVb',
    owner: signer.publicKey.toBase58(),
    asset: assetPubkey,
    signature,
    metadataUri: METADATA_URI,
    atomEnabled: true,
    costSol: Number(costSol.toFixed(6)),
    registeredAt: new Date().toISOString(),
  };

  fs.writeFileSync(RECEIPT_PATH, JSON.stringify(receipt, null, 2) + '\n', 'utf8');
  console.log(`Saved receipt to ${RECEIPT_PATH}`);
}

main().catch((err) => {
  console.error('Registration failed:', err);
  process.exit(1);
});

