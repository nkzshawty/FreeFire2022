import frida
import sys
import time

SCRIPT = """
var found = false;

function log(msg) {
    send(msg);
}

function searchMetadata() {
    log('[*] Buscando metadata na memoria...');
    var ranges = Process.enumerateRanges('r--');
    log('[*] Total ranges: ' + ranges.length);
    var checked = 0;
    for (var i = 0; i < ranges.length; i++) {
        var range = ranges[i];
        if (range.size < 500000) continue;
        checked++;
        try {
            var matches = Memory.scanSync(range.base, range.size, 'AF 1B B1 FA');
            for (var j = 0; j < matches.length; j++) {
                var addr = matches[j].address;
                var version = addr.add(4).readU32();
                if (version >= 20 && version <= 31) {
                    log('[+] ENCONTRADO! Metadata v' + version + ' em ' + addr);
                    var offset = addr.sub(range.base).toInt32();
                    var size = range.size - offset;
                    if (size > 50 * 1024 * 1024) size = 50 * 1024 * 1024;
                    log('[+] Tamanho: ' + (size / 1024 / 1024).toFixed(1) + ' MB');
                    var data = addr.readByteArray(size);
                    var outPath = '/data/local/tmp/metadata-dump.dat';
                    var file = new File(outPath, 'wb');
                    file.write(data);
                    file.close();
                    log('[+] SALVO: ' + outPath);
                    found = true;
                    return true;
                }
            }
        } catch (e) {}
    }
    log('[-] Nao encontrado. Checked ' + checked + ' ranges.');
    return false;
}

function listModules() {
    var mods = Process.enumerateModules();
    var names = [];
    for (var i = 0; i < mods.length; i++) {
        if (mods[i].name.indexOf('il2cpp') >= 0 || mods[i].name.indexOf('unity') >= 0 || mods[i].name.indexOf('anogs') >= 0) {
            names.push(mods[i].name + ' (' + (mods[i].size/1024/1024).toFixed(0) + 'MB)');
        }
    }
    log('[*] Modulos relevantes: ' + (names.length > 0 ? names.join(', ') : 'NENHUM AINDA'));
}

// Check every 2s for 60s
var attempts = 0;
var maxAttempts = 30;
var timer = setInterval(function() {
    attempts++;
    listModules();
    var mod = Process.findModuleByName('libil2cpp.so');
    if (mod) {
        log('[+] libil2cpp.so CARREGADO! Size: ' + (mod.size/1024/1024).toFixed(0) + ' MB');
        clearInterval(timer);
        // Wait for metadata to be decrypted
        log('[*] Esperando 10s para decriptacao...');
        setTimeout(function() {
            searchMetadata();
            if (!found) {
                log('[*] Tentando de novo em 10s...');
                setTimeout(searchMetadata, 10000);
            }
        }, 10000);
    } else if (attempts >= maxAttempts) {
        clearInterval(timer);
        log('[!] Timeout - libil2cpp.so nunca carregou');
        log('[!] O jogo pode ter crashado ou o anti-cheat bloqueou');
    }
}, 2000);
"""

device = frida.get_usb_device()
print('[*] Spawning com.dts.freefireth...')
pid = device.spawn(['com.dts.freefireth'])
session = device.attach(pid)
script = session.create_script(SCRIPT)

def on_message(message, data):
    if message['type'] == 'send':
        print(message['payload'])
    elif message['type'] == 'error':
        print('[ERROR]', message.get('description', message))
    else:
        print('[MSG]', message)

script.on('message', on_message)
script.load()
print('[*] Resuming app...')
device.resume(pid)
print('[*] Monitoring for 90 seconds...')
time.sleep(90)
print('[*] Done.')
