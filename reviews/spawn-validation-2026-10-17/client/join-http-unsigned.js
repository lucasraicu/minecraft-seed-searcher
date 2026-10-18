// Isolated HTTP transport adapter; no game-world commands or movement packets.
const nn = require('nethernet')
const OriginalClient = nn.Client
nn.Client = class extends OriginalClient {
 constructor(n,a,o) { super(n,a,{...o,http:{url:'http://127.0.0.1:19132',onServerKey:(fingerprint,origin)=>{console.log(JSON.stringify({event:'local_disposable_server_key',fingerprint,origin}));return true}}}) }
}
const { createClient } = require('bedrock-protocol')
const emit = (event, data) => console.log(JSON.stringify({event, data}, (_,v)=>typeof v==='bigint'?v.toString():v))
const client = createClient({host:'127.0.0.1', port:Number(process.argv[2]), username:'SpawnAudit1', offline:true, version:'1.26.51', transport:'nethernet', skipPing:true, nethernet:{networkId:1n,signalling:'lan',webrtcBackend:'werift'}, raknetBackend:'jsp-raknet', useRaknetWorkers:false, connectTimeout:25000})
client.on('start_game', data => emit('start_game', {player_position:data.player_position, spawn_position:data.spawn_position, world_seed:data.seed}))
client.on('spawn', () => {emit('spawn',true); setTimeout(()=>client.close(),3500)})
client.on('error', error => emit('error',String(error.stack||error)))
client.on('kick', data => emit('kick',data))
client.on('close',()=>{emit('close',true);process.exit(0)})
setTimeout(()=>{emit('timeout',true);client.close();process.exit(2)},40000)
