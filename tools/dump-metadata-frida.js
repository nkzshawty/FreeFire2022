const METADATA_MAGIC = [0xAF, 0x1B, 0xB1, 0xFA];

function searchMetadata() {
    console.log('[*] Buscando global-metadata.dat na memoria...');
    var ranges = Process.enumerateRanges('r--');
    console.log('[*] Total de ranges: ' + ranges.length);
    for (var i = 0; i < ranges.length; i++) {
        var range = ranges[i];
        if (range.size < 1024 * 1024) continue;
        try {
            var matches = Memory.scanSync(range.base, range.size, 'AF 1B B1 FA');
            for (var j = 0; j < matches.length; j++) {
                var addr = matches[j].address;
                var version = addr.add(4).readU32();
                if (version >= 20 && version <= 31) {
                    console.log('[+] ENCONTRADO! Metadata v' + version + ' em ' + addr);
                    var offset = addr.sub(range.base).toInt32();
                    var size = range.size - offset;
                    if (size > 50 * 1024 * 1024) size = 50 * 1024 * 1024;
                    console.log('[+] Tamanho: ' + (size / 1024 / 1024).toFixed(1) + ' MB');
                    var data = addr.readByteArray(size);
                    var outPath = '/data/local/tmp/global-metadata-dumped.dat';
                    var file = new File(outPath, 'wb');
                    file.write(data);
                    file.close();
                    console.log('[+] SALVO: ' + outPath);
                    return true;
                }
            }
        } catch (e) {}
    }
    console.log('[-] Nao encontrado ainda.');
    return false;
}

console.log('=== FF Metadata Dumper ===');
var checkInterval = setInterval(function() {
    var mod = Process.findModuleByName('libil2cpp.so');
    if (mod) {
        clearInterval(checkInterval);
        console.log('[+] libil2cpp.so carregado (' + (mod.size/1024/1024).toFixed(0) + ' MB)');
        console.log('[*] Aguardando 8s...');
        setTimeout(function() {
            if (!searchMetadata()) {
                console.log('[*] Tentando de novo em 10s...');
                setTimeout(searchMetadata, 10000);
            }
        }, 8000);
    }
}, 1000);
