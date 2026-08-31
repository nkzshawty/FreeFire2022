# -*- coding: utf-8 -*-
"""
Final extraction script for Free Fire localization bundle.
Extracts the TextAsset text content from the UnityFS bundle.
"""
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
    """Decompress UnityFS bundle -> raw CAB bytes"""
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
    
    data_start = (data_after + 15) & ~15 if (flags & 0x200) else data_after
    
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


def extract_text_from_cab(cab_data):
    """
    Extract the TextAsset m_Script content from Unity serialized data.
    
    The Unity serialized file has a header, then type metadata, then object data.
    For a TextAsset, the data section contains:
      - m_Name: int32 length + utf8 string + padding to 4-byte alignment
      - m_Script: int32 length + raw bytes (the actual text content)
    
    We know from debugging that:
      - The asset name 'loc_pt-br' is at offset 2612
      - Before it (offset 2608) is the name length: 09000000 (LE int32 = 9)
      - The script data length is at offset 2774: value = 589824
    """
    
    # Find the TextAsset by locating the name 'loc_pt-br'
    name = b'loc_pt-br'
    name_idx = cab_data.find(name)
    
    if name_idx < 0:
        print("ERROR: Could not find asset name in CAB data")
        return None
    
    # Verify: 4 bytes before name should be the name length (9)
    name_len_offset = name_idx - 4
    name_len = struct.unpack_from('<I', cab_data, name_len_offset)[0]
    
    if name_len != len(name):
        # Try finding it differently - search for all occurrences
        idx = 0
        while True:
            idx = cab_data.find(name, idx)
            if idx < 0:
                break
            # Check if preceded by correct length
            if idx >= 4:
                check_len = struct.unpack_from('<I', cab_data, idx - 4)[0]
                if check_len == len(name):
                    name_idx = idx
                    name_len_offset = idx - 4
                    name_len = check_len
                    break
            idx += 1
    
    print(f"  Asset name at offset {name_idx}, length prefix: {name_len}")
    
    # After name: align to 4 bytes
    after_name = name_idx + name_len
    aligned = (after_name + 3) & ~3
    
    # The next field is m_Script (byte array): int32 length + data
    script_len_offset = aligned
    script_len = struct.unpack_from('<I', cab_data, script_len_offset)[0]
    
    print(f"  Script length at offset {script_len_offset}: {script_len}")
    
    if script_len < 1000 or script_len > 10000000:
        # Try looking further - there might be additional fields between name and script
        # In some Unity versions, TextAsset has: m_Name, m_Script, m_PathName
        # But in newer versions it's just m_Name then m_Script
        
        # Let's search for a reasonable length value after the name
        for probe_offset in range(aligned, min(aligned + 200, len(cab_data) - 4), 4):
            probe_len = struct.unpack_from('<I', cab_data, probe_offset)[0]
            if 100000 < probe_len < 5000000:
                # Verify by checking if data after looks like text
                data_start = probe_offset + 4
                sample = cab_data[data_start:data_start + 50]
                text_chars = sum(1 for b in sample if 32 <= b < 127 or b in (10, 13, 9) or b >= 0xC0)
                if text_chars > 30:
                    script_len_offset = probe_offset
                    script_len = probe_len
                    print(f"  Found script data at offset {probe_offset}: length={script_len}")
                    break
    
    # Extract the script data
    script_start = script_len_offset + 4
    script_data = cab_data[script_start:script_start + script_len]
    
    # Decode as UTF-8
    text = script_data.decode('utf-8', errors='replace')
    
    # The text uses \r\n line endings
    # Split into lines
    lines = text.split('\r\n')
    
    print(f"  Raw text: {len(text)} chars, {len(lines)} lines")
    print(f"  First line: '{lines[0][:80]}'")
    print(f"  Second line: '{lines[1][:80]}'" if len(lines) > 1 else "")
    
    return text


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

# Step 1: Decompress the bundle
cab_data = decompress_bundle(bundle_path)
print(f"Decompressed: {len(cab_data)} bytes")

# Step 2: Extract text content
text = extract_text_from_cab(cab_data)

if not text:
    print("FAILED to extract text!")
    sys.exit(1)

# Step 3: Clean up and save
# The text should be clean now - just the localization strings separated by \r\n
lines = text.split('\r\n')

# Remove any completely empty trailing lines
while lines and not lines[-1]:
    lines.pop()

print(f"\nTotal lines: {len(lines)}")
print(f"First 5 lines:")
for i, line in enumerate(lines[:5]):
    print(f"  [{i}]: {line[:100]}")
print(f"Last 3 lines:")
for i, line in enumerate(lines[-3:], len(lines)-3):
    print(f"  [{i}]: {line[:100]}")

# Save the clean text file
out_dir = r"C:\Users\Flavio\Downloads\Free Fire Server\unity-loc-builder\Assets\BundleAssets"
os.makedirs(out_dir, exist_ok=True)

# Save as loc_pt-br.txt (the format the game actually uses)
out_txt = os.path.join(out_dir, "loc_pt-br.txt")
with open(out_txt, 'w', encoding='utf-8', newline='') as f:
    f.write('\r\n'.join(lines))

print(f"\n{'=' * 80}")
print(f"SUCCESS!")
print(f"  Output: {out_txt}")
print(f"  Size: {os.path.getsize(out_txt)} bytes")
print(f"  Lines: {len(lines)}")

# Also save a copy as loc_en.txt (since our bundle is named loc_en)
out_en = os.path.join(out_dir, "loc_en.txt")
with open(out_en, 'w', encoding='utf-8', newline='') as f:
    f.write('\r\n'.join(lines))
print(f"  Also saved as: {out_en}")
