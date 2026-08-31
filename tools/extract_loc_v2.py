# -*- coding: utf-8 -*-
import struct
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

try:
    import lz4.block
except ImportError:
    print("ERROR: lz4 not installed")
    sys.exit(1)

def decompress_bundle(path):
    """Decompress a UnityFS bundle and return raw bytes"""
    with open(path, 'rb') as f:
        data = f.read()
    
    offset = 0
    sig_end = data.index(b'\x00', offset)
    offset = sig_end + 1
    format_ver = struct.unpack_from('>I', data, offset)[0]
    offset += 4
    offset = data.index(b'\x00', offset) + 1  # unity version
    offset = data.index(b'\x00', offset) + 1  # generator
    offset += 8  # file size
    cb_size = struct.unpack_from('>I', data, offset)[0]
    offset += 4
    ub_size = struct.unpack_from('>I', data, offset)[0]
    offset += 4
    flags = struct.unpack_from('>I', data, offset)[0]
    offset += 4
    compression = flags & 0x3F
    
    if format_ver >= 7:
        offset = (offset + 15) & ~15
    
    block_info_raw = data[offset:offset + cb_size]
    data_after = offset + cb_size
    
    if compression in (2, 3):
        block_info = lz4.block.decompress(block_info_raw, uncompressed_size=ub_size)
    else:
        block_info = block_info_raw
    
    if flags & 0x200:
        data_start = (data_after + 15) & ~15
    else:
        data_start = data_after
    
    bi_offset = 16
    block_count = struct.unpack_from('>I', block_info, bi_offset)[0]
    bi_offset += 4
    
    blocks = []
    for _ in range(block_count):
        uncomp = struct.unpack_from('>I', block_info, bi_offset)[0]
        bi_offset += 4
        comp = struct.unpack_from('>I', block_info, bi_offset)[0]
        bi_offset += 4
        bflags = struct.unpack_from('>H', block_info, bi_offset)[0]
        bi_offset += 2
        blocks.append((uncomp, comp, bflags))
    
    all_data = bytearray()
    read_offset = data_start
    for uncomp_size, comp_size, bflags in blocks:
        block_data = data[read_offset:read_offset + comp_size]
        read_offset += comp_size
        if (bflags & 0x3F) in (2, 3):
            all_data.extend(lz4.block.decompress(block_data, uncompressed_size=uncomp_size))
        else:
            all_data.extend(block_data)
    
    return bytes(all_data)


def find_text_asset(cab_data):
    """Find the TextAsset data within a Unity serialized file (CAB)"""
    
    # Unity serialized file format:
    # Header: metadata_size(4), file_size(4), version(4), data_offset(4), endianness(1), reserved(3)
    # For version >= 22: metadata_size(4), file_size(8), data_offset(8), ...
    
    # Let's check the serialized file header
    # First 4 bytes: metadata size (big-endian in newer format)
    
    # Actually let's just look for the text content directly
    # The asset path shows: "Resources/localization/loc_pt-br.txt"
    # This is a TextAsset. In serialized form, the text data is stored as:
    # - 4 bytes: string length (little-endian)
    # - N bytes: the actual text
    
    # Let's find the path reference and then look for the data nearby
    path_marker = b'localization/loc_pt-br.txt'
    idx = cab_data.find(path_marker)
    print(f"  Path marker at offset: {idx}")
    
    # The text content starts much later. Let's look for length-prefixed strings
    # that are large enough to be the full localization file
    
    # In Unity TextAsset, the serialized format has:
    # m_Name: string (length + data + align)
    # m_Script: byte array (length + data)
    
    # Let's find 'loc_pt-br' as the asset name
    name_marker = b'loc_pt-br'
    name_idx = cab_data.find(name_marker)
    print(f"  Name 'loc_pt-br' at offset: {name_idx}")
    
    # Look at the area around offset 2612 where we found 'loc_pt-br'
    # Dump some hex context
    if name_idx >= 0:
        # Before the name, there should be a 4-byte length
        # name_length = struct.unpack_from('<I', cab_data, name_idx - 4)[0]
        # print(f"  Name length prefix: {name_length}")
        
        # After name + alignment, the next field is m_Script (byte[])
        # which has a 4-byte length followed by the raw text data
        name_len = len(name_marker)
        # Align to 4 bytes after name
        after_name = name_idx + name_len
        aligned_after = (after_name + 3) & ~3
        
        # Show hex around this area
        area = cab_data[name_idx - 8:name_idx + 200]
        print(f"  Hex around name: {area[:50].hex()}")
        
    # Strategy: scan for a 4-byte LE integer that matches a large text block
    # The text content in Free Fire localization uses key=value format or similar
    
    # Let's search from offset 2700 onwards for a large length prefix
    # followed by text content
    print("\n  Searching for large text blocks (length-prefixed)...")
    
    for scan_offset in range(2700, min(len(cab_data) - 4, 50000)):
        length = struct.unpack_from('<I', cab_data, scan_offset)[0]
        if 500000 < length < 3000000:
            data_start = scan_offset + 4
            if data_start + 100 < len(cab_data):
                sample = cab_data[data_start:data_start + 100]
                # Check if it looks like text
                printable_count = sum(1 for b in sample if 32 <= b < 127 or b in (10, 13, 9) or b >= 0x80)
                if printable_count > 80:
                    print(f"  Found at offset {scan_offset}: length={length}")
                    preview = cab_data[data_start:data_start + 200]
                    print(f"  Preview: {preview[:100]}")
                    text_data = cab_data[data_start:data_start + length]
                    return text_data
    
    # Try scanning further
    print("  Scanning wider range...")
    for scan_offset in range(0, min(len(cab_data) - 4, 100000), 4):
        length = struct.unpack_from('<I', cab_data, scan_offset)[0]
        if 100000 < length < 3000000:
            data_start = scan_offset + 4
            if data_start + 50 < len(cab_data):
                sample = cab_data[data_start:data_start + 50]
                printable_count = sum(1 for b in sample if 32 <= b < 127 or b in (10, 13, 9) or b >= 0x80)
                if printable_count > 40:
                    print(f"  Found potential text at offset {scan_offset}: length={length}")
                    text_data = cab_data[data_start:data_start + length]
                    # Verify it's really text
                    test = text_data[:1000]
                    text_ratio = sum(1 for b in test if 32 <= b < 127 or b in (10, 13, 9) or b >= 0x80) / len(test)
                    if text_ratio > 0.9:
                        print(f"  Text ratio: {text_ratio:.2%} - looks good!")
                        return text_data
                    else:
                        print(f"  Text ratio: {text_ratio:.2%} - too low, skipping")
    
    # Last resort: find the longest text sequence
    print("  Finding longest text sequence...")
    best_start = -1
    best_len = 0
    cur_start = -1
    cur_len = 0
    
    for i in range(len(cab_data)):
        b = cab_data[i]
        if 32 <= b < 127 or b in (10, 13, 9) or b >= 0xC0:
            if cur_start < 0:
                cur_start = i
            cur_len += 1
        else:
            if b == 0 and cur_len > 0:
                # Allow occasional null bytes in otherwise text regions
                cur_len += 1
                continue
            if cur_len > best_len:
                best_len = cur_len
                best_start = cur_start
            cur_start = -1
            cur_len = 0
    
    if cur_len > best_len:
        best_len = cur_len
        best_start = cur_start
    
    if best_len > 10000:
        print(f"  Longest text: offset={best_start}, length={best_len}")
        return cab_data[best_start:best_start + best_len]
    
    return None


# Main
bundle_path = None
if len(sys.argv) > 1:
    bundle_path = sys.argv[1]

if not bundle_path:
    search_dir = r"C:\Users\Flavio\Downloads\com.dts.freefireth"
    if os.path.isdir(search_dir):
        for root, dirs, files in os.walk(search_dir):
            for f in files:
                fp = os.path.join(root, f)
                if f.startswith("loc_pt-br") and os.path.getsize(fp) > 100000:
                    bundle_path = fp
                    break
            if bundle_path:
                break

if not bundle_path:
    print("Bundle not found!")
    sys.exit(1)

print(f"Processing: {bundle_path}")
print("=" * 80)

# Decompress the bundle
cab_data = decompress_bundle(bundle_path)
print(f"Decompressed CAB data: {len(cab_data)} bytes")

# Extract text asset
text_data = find_text_asset(cab_data)

if text_data:
    # Decode text
    try:
        text = text_data.decode('utf-8')
    except:
        text = text_data.decode('utf-8', errors='replace')
    
    # Clean up - remove trailing nulls
    text = text.rstrip('\x00')
    
    out_dir = r"C:\Users\Flavio\Downloads\Free Fire Server\unity-loc-builder\Assets\BundleAssets"
    os.makedirs(out_dir, exist_ok=True)
    
    # Determine if it's XML or key-value format
    if '<l id="' in text or '<localization' in text:
        out_path = os.path.join(out_dir, "loc_en.xml")
        ext = "XML"
    else:
        out_path = os.path.join(out_dir, "loc_pt-br.txt")
        ext = "TXT"
    
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    # Count entries (try different formats)
    line_count = text.count('\n')
    xml_count = text.count('<l id="')
    
    print(f"\n{'=' * 80}")
    print(f"SUCCESS! Wrote {len(text)} bytes ({ext}) to {out_path}")
    print(f"Lines: {line_count}, XML entries: {xml_count}")
    print(f"\n--- First 500 chars ---")
    print(text[:500])
    print(f"\n--- Last 200 chars ---")
    print(text[-200:])
    print(f"--- End ---")
else:
    # Dump the decompressed data for manual inspection
    dump_path = r"C:\Users\Flavio\Downloads\Free Fire Server\tools\cab_dump.bin"
    with open(dump_path, 'wb') as f:
        f.write(cab_data)
    print(f"\nFailed to extract text! Dumped raw CAB to: {dump_path}")
    print(f"CAB size: {len(cab_data)} bytes")
    
    # Show some structure info
    print("\nFirst 100 bytes hex:")
    print(cab_data[:100].hex())
