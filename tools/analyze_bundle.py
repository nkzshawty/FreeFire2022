import struct
import sys
import os

def read_string(f):
    chars = []
    while True:
        c = f.read(1)
        if c == b'\x00' or c == b'':
            break
        chars.append(c)
    return b''.join(chars).decode('utf-8')

def analyze_bundle(path):
    print(f"Analyzing: {path}")
    size = os.path.getsize(path)
    print(f"File size: {size} bytes")
    
    if size < 50:
        print("  File too small to be a valid bundle")
        return
    
    with open(path, 'rb') as f:
        # Read UnityFS header
        signature = read_string(f)
        print(f"Signature: {signature}")
        
        if signature != "UnityFS":
            print("  NOT a UnityFS bundle!")
            # Print first bytes for investigation
            f.seek(0)
            raw = f.read(min(64, size))
            print(f"  First bytes: {raw[:32].hex()}")
            return
        
        format_version = struct.unpack('>I', f.read(4))[0]
        print(f"Format version: {format_version}")
        
        unity_version = read_string(f)
        print(f"Unity version: {unity_version}")
        
        generator_version = read_string(f)
        print(f"Generator version: {generator_version}")
        
        file_size = struct.unpack('>Q', f.read(8))[0]
        print(f"File size (header): {file_size}")
        
        compressed_size = struct.unpack('>I', f.read(4))[0]
        print(f"Compressed block info size: {compressed_size}")
        
        uncompressed_size = struct.unpack('>I', f.read(4))[0]
        print(f"Uncompressed block info size: {uncompressed_size}")
        
        flags = struct.unpack('>I', f.read(4))[0]
        compression = flags & 0x3F
        has_directory_info = (flags & 0x40) != 0
        block_info_at_end = (flags & 0x80) != 0
        print(f"Flags: 0x{flags:08X}")
        print(f"  Compression: {compression} (0=none, 1=LZMA, 2/3=LZ4)")
        print(f"  Has directory info: {has_directory_info}")
        print(f"  Block info at end: {block_info_at_end}")
        
        header_end = f.tell()
        print(f"Header end offset: {header_end}")
        
        # For format version 7+, there might be alignment padding
        if format_version >= 7:
            # Check if there's alignment after header
            aligned = (header_end + 15) & ~15
            if aligned != header_end:
                print(f"  Expected alignment padding to: {aligned}")
        
        # Print first 128 bytes as hex for additional context
        f.seek(0)
        raw = f.read(128)
        print(f"\nFirst 128 bytes (hex):")
        for i in range(0, len(raw), 16):
            hex_str = ' '.join(f'{b:02X}' for b in raw[i:i+16])
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in raw[i:i+16])
            print(f"  {i:04X}: {hex_str:<48} {ascii_str}")

print("=" * 80)
print("=== ALL BUNDLES IN SERVER STATIC (optionallocres) ===")
print("=" * 80)

static_dir = r"C:\Users\Flavio\Downloads\Free Fire Server\static\ABHotUpdates\android\optional\optionallocres\99\gameassetbundles"
for fname in sorted(os.listdir(static_dir)):
    fpath = os.path.join(static_dir, fname)
    if os.path.isfile(fpath) and os.path.getsize(fpath) > 50:
        print()
        print("-" * 60)
        analyze_bundle(fpath)

print("\n")
print("=" * 80)
print("=== REFERENCE: optionalab_109 FROM EMULATOR CACHE (working with game) ===")
print("=" * 80)

ref_bundle = r"C:\Users\Flavio\Downloads\com.dts.freefireth\com.dts.freefireth\files\contentcache\Optional\android\gameassetbundles\optionalab_109.b2P3Bv7~2BKtTbp5Ejk0Ohig7Wpv4~3D"
if os.path.exists(ref_bundle):
    print()
    analyze_bundle(ref_bundle)
else:
    print(f"File not found: {ref_bundle}")
