'use strict';
const fs = require('fs');
const readline = require('readline');

const file = 'C:\\Users\\Flavio\\Downloads\\DUMP\\dump_fixed.cs';
const patterns = [
  /http/i, /encrypt/i, /decrypt/i, /aes/i, /cipher/i,
  /HttpManager/i, /NetworkManager/i, /ServerUrl/i, /BaseUrl/i,
  /LoginUrl/i, /server_url/i, /cdn_url/i, /ver\.php/i,
  /ggblueshark/i, /garena/i, /freefire/i,
  /AesKey/i, /AesIv/i, /InitKey/i, /CryptoKey/i
];

const rl = readline.createInterface({ input: fs.createReadStream(file), crlfDelay: Infinity });
let lineNum = 0;
let matches = [];

rl.on('line', (line) => {
  lineNum++;
  for (const p of patterns) {
    if (p.test(line)) {
      matches.push({ line: lineNum, text: line.trim().substring(0, 200) });
      break;
    }
  }
});

rl.on('close', () => {
  console.log('Total matches:', matches.length);
  matches.slice(0, 100).forEach(m => console.log(`L${m.line}: ${m.text}`));
});
