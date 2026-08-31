import struct
import sys
import os

try:
    import lz4.block
except ImportError:
    print("ERROR: lz4 not installed. Run: pip install lz4")
    sys.exit(1)

def extract_text_from_bundle(path):
    """Extract text content from a UnityFS bundle"""
    with open(path, 'rb') as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    # Parse UnityFS header
    offset = 0
    sig_end = data.index(b'\x00', offset)
    offset = sig_end + 1
    
    format_ver = struct.unpack_from('>I', data, offset)[0]
    offset += 4
    
    ver_end = data.index(b'\x00', offset)
    offset = ver_end + 1
    gen_end = data.index(b'\x00', offset)
    offset = gen_end + 1
    
    offset += 8  # file size
    cb_size = struct.unpack_from('>I', data, offset)[0]
    offset += 4
    ub_size = struct.unpack_from('>I', data, offset)[0]
    offset += 4
    flags = struct.unpack_from('>I', data, offset)[0]
    offset += 4
    
    compression = flags & 0x3F
    
    # Align to 16 for format >= 7
    if format_ver >= 7:
        offset = (offset + 15) & ~15
    
    # Block info
    block_info_raw = data[offset:offset + cb_size]
    data_after_blockinfo = offset + cb_size
    
    # Decompress block info
    if compression in (2, 3):
        block_info = lz4.block.decompress(block_info_raw, uncompressed_size=ub_size)
    else:
        block_info = block_info_raw
    
    # Align data start (flag 0x200 = padding)
    if flags & 0x200:
        data_start = (data_after_blockinfo + 15) & ~15
    else:
        data_start = data_after_blockinfo
    
    # Parse blocks from block info
    bi_offset = 16  # skip hash
    block_count = struct.unpack_from('>I', block_info, bi_offset)[0]
    bi_offset += 4
    
    blocks = []
    for i in range(block_count):
        uncomp = struct.unpack_from('>I', block_info, bi_offset)[0]
        bi_offset += 4
        comp = struct.unpack_from('>I', block_info, bi_offset)[0]
        bi_offset += 4
        bflags = struct.unpack_from('>H', block_info, bi_offset)[0]
        bi_offset += 2
        blocks.append((uncomp, comp, bflags))
    
    print(f"  Decompressing {block_count} blocks from offset {data_start}...")
    
    # Decompress all blocks
    all_data = bytearray()
    read_offset = data_start
    for uncomp_size, comp_size, bflags in blocks:
        block_data = data[read_offset:read_offset + comp_size]
        read_offset += comp_size
        block_comp = bflags & 0x3F
        if block_comp in (2, 3):
            all_data.extend(lz4.block.decompress(block_data, uncompressed_size=uncomp_size))
        else:
            all_data.extend(block_data)
    
    print(f"  Total decompressed: {len(all_data)} bytes")
    
    # The decompressed data is a Unity serialized file
    # TextAssets store their text as a length-prefixed string
    # We need to find the XML content within the serialized data
    
    all_bytes = bytes(all_data)
    
    # Strategy 1: Search for XML markers directly
    for marker in [b'<?xml', b'<localization>', b'<localization ']:
        idx = all_bytes.find(marker)
        if idx >= 0:
            end_idx = all_bytes.find(b'</localization>', idx)
            if end_idx > 0:
                xml = all_bytes[idx:end_idx + 15].decode('utf-8', errors='replace')
                return xml
    
    # Strategy 2: Search for '<l id="' which is the entry format
    idx = all_bytes.find(b'<l id="')
    if idx >= 0:
        # Found localization entries. Go back to find start
        search_back = max(0, idx - 5000)
        prefix = all_bytes[search_back:idx]
        
        xml_start = idx
        for sm in [b'<?xml', b'<localization']:
            sm_idx = prefix.rfind(sm)
            if sm_idx >= 0:
                xml_start = search_back + sm_idx
                break
        
        # Find end
        end_idx = all_bytes.rfind(b'</localization>')
        if end_idx > 0:
            xml = all_bytes[xml_start:end_idx + 15].decode('utf-8', errors='replace')
            return xml
        
        # Find last </l>
        last_l = all_bytes.rfind(b'</l>')
        if last_l > xml_start:
            xml = all_bytes[xml_start:last_l + 4].decode('utf-8', errors='replace') + '\n</localization>'
            return xml
    
    # Strategy 3: The TextAsset data is stored as a length-prefixed byte array
    # In Unity serialized format, TextAsset has: name (string), then script (byte array)
    # A byte array is stored as: int32 length, then data bytes
    # Look for a large length value followed by text content
    
    print("  No direct XML markers. Searching for length-prefixed text data...")
    
    # Find large strings that could be the XML content
    # Search for 4-byte little-endian lengths > 100000 followed by '<' or text
    for search_offset in range(0, min(len(all_bytes) - 100, 50000)):
        # Try little-endian 4-byte int
        length = struct.unpack_from('<I', all_bytes, search_offset)[0]
        if 100000 < length < 3000000:
            # Check if the data after this looks like text
            start = search_offset + 4
            if start + 10 < len(all_bytes):
                sample = all_bytes[start:start+20]
                if sample.startswith(b'<?xml') or sample.startswith(b'<loc') or b'<l ' in sample[:100]:
                    print(f"  Found text data at offset {search_offset}: length={length}")
                    text_data = all_bytes[start:start+length]
                    return text_data.decode('utf-8', errors='replace')
                # Also check if it's printable text
                if all(32 <= b < 127 or b in (10, 13, 9) for b in sample):
                    peek = all_bytes[start:start+200].decode('utf-8', errors='replace')
                    if '<l ' in peek or 'id=' in peek or 'xml' in peek.lower():
                        print(f"  Found text at offset {search_offset}: length={length}")
                        text_data = all_bytes[start:start+length]
                        return text_data.decode('utf-8', errors='replace')
    
    # Strategy 4: Broader search - find any long sequence of printable UTF-8
    print("  Searching for long printable text sequences...")
    best_start = -1
    best_length = 0
    current_start = -1
    current_length = 0
    
    for i in range(len(all_bytes)):
        b = all_bytes[i]
        if 32 <= b < 127 or b in (10, 13, 9) or b >= 0xC0:  # printable ASCII or UTF-8 multibyte
            if current_start < 0:
                current_start = i
                current_length = 0
            current_length += 1
        else:
            if current_length > best_length:
                best_length = current_length
                best_start = current_start
            current_start = -1
            current_length = 0
    
    if current_length > best_length:
        best_length = current_length
        best_start = current_start
    
    if best_length > 10000:
        print(f"  Found long text sequence: offset={best_start}, length={best_length}")
        text_data = all_bytes[best_start:best_start + best_length]
        text = text_data.decode('utf-8', errors='replace')
        if '<l ' in text or 'id=' in text:
            return text
        print(f"  Preview: {text[:200]}")
    
    # Strategy 5: dump hex around interesting areas for debugging
    print("\n  DEBUG: Scanning for patterns...")
    # Look for 'loc' anywhere
    idx = 0
    found_count = 0
    while idx < len(all_bytes) and found_count < 10:
        idx = all_bytes.find(b'loc', idx)
        if idx < 0:
            break
        context = all_bytes[max(0,idx-4):idx+20]
        hex_ctx = context.hex()
        ascii_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in context)
        print(f"    'loc' at {idx}: {ascii_ctx}")
        idx += 3
        found_count += 1
    
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

if not bundle_path or not os.path.exists(bundle_path):
    print("Bundle not found!")
    sys.exit(1)

print(f"Processing: {bundle_path}")
print("=" * 80)

xml = extract_text_from_bundle(bundle_path)
if xml:
    out_dir = r"C:\Users\Flavio\Downloads\Free Fire Server\unity-loc-builder\Assets\BundleAssets"
    os.makedirs(out_dir, exist_ok=True)
    
    out_path = os.path.join(out_dir, "loc_en.xml")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(xml)
    
    count = xml.count('<l id="')
    print(f"\n{'=' * 80}")
    print(f"SUCCESS! Wrote {len(xml)} bytes to {out_path}")
    print(f"Total string entries: {count}")
    print(f"\n--- First 500 chars ---")
    print(xml[:500].encode('ascii', errors='replace').decode('ascii'))
    print(f"--- End preview ---")
else:
    print("\nFailed to extract XML!")
    sys.exit(1)
