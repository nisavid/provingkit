import { sampleExecutor } from './executor.mjs';

const { config, collectorPid, claimedPid } = JSON.parse(process.argv[2]);
const result = await sampleExecutor(config, collectorPid, claimedPid);
process.stdout.write(JSON.stringify(result));
