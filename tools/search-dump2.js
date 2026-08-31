'use strict';
const fs = require('fs');
const readline = require('readline');

const file = 'C:\\Users\\Flavio\\Downloads\\DUMP\\dump_fixed.cs';
const patterns = [
  /class.*Service.*Manager/i,
  /class.*Http/i,
  /class.*Network/i, 
  /Init.*Url/i,
  /Init.*Server/i,
  /SetServer/i,
  /m_serverUrl/i,
  /m_baseUrl/i,
  /serverAddr/i,
  /InitCurl/i,
  /CurlManager/i,
  /CURL/,
  /class.*Curl/i,
  /ver\.php/i,
  /InitHttp/i,
  /SetHttp/i,
  /AESEncrypt/i,
  /AESDecrypt/i,
  /InitKey/i,
  /SetKey/i,
  /m_key/,
  /m_iv/,
  /aesKey/i,
  /aesIv/i,
  /encryptKey/i,
];

const rl = readline.createInterface({ input: fs.createReadStream(file), crlfDelay: Infinity });
let lineNum = 0;
let context = [];
let currentClass = '';

rl.on('line', (line) => {
  lineNum++;
  if (line.includes('class ') || line.includes('struct ')) {
    currentClass = line.trim();
  }
  for (const p of patterns) {
    if (p.test(line)) {
      context.push({ line: lineNum, cls: currentClass, text: line.trim().substring(0, 200) });
      break;
    }
  }
});

rl.on('close', () => {
  console.log('Found:', context.length);
  context.forEach(m => console.log(`L${m.line} [${m.cls.substring(0,60)}]: ${m.text}`));
});
