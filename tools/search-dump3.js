'use strict';
const fs = require('fs');
const readline = require('readline');

const file = 'C:\\Users\\Flavio\\Downloads\\DUMP\\dump_fixed.cs';
const patterns = [
  /GameConfig/,
  /CurlManager/,
  /CurlHelper/,
  /ServiceManager/,
  /HttpService/,
  /class.*Login.*Controller/,
  /OverrideServer/,
  /DebugLogin/,
  /m_serverAddr/,
  /m_serverUrl/i,
  /server_addr/i,
  /server_url/i,
  /InitCurl/i,
  /SetUrl/i,
  /SetAddr/i,
  /live.*url/i,
  /login.*url/i,
  /cdn.*url/i,
];

const rl = readline.createInterface({ input: fs.createReadStream(file), crlfDelay: Infinity });
let lineNum = 0;
let results = [];

rl.on('line', (line) => {
  lineNum++;
  for (const p of patterns) {
    if (p.test(line)) {
      results.push(`L${lineNum}: ${line.trim().substring(0, 200)}`);
      break;
    }
  }
});

rl.on('close', () => {
  console.log('Found:', results.length);
  results.slice(0, 80).forEach(r => console.log(r));
});
