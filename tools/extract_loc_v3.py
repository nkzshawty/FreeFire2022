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
    """Decompress a UnityFS bundle and return raw CAB bytes"""
    with open(path, 'rb') as f:
        data = f.read()
    
    offset = 0
    sig_end = data.index(b'\x00', offset)
    offset = sig_end + 1
    format_ver = struct.unpack_from('>I', data, offset)[0]
    offset += 4
    offset = data.index(b'\x00', offset) + 1
    offset = data.index(b'\x00', offset) + 1
    offset += 8
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


def extract_text_assets(cab_data):
    """Extract all TextAsset data from a Unity serialized file.
    
    In Unity serialized format for TextAsset:
    - m_Name: int32 length + bytes + padding to 4
    - m_Script: int32 length + bytes
    
    We look for the pattern: length-prefixed name 'loc_pt-br' followed by the script data.
    """
    
    # From the debug output, we know:
    # At offset 2612: name 'loc_pt-br' (9 bytes)
    # Before it (offset 2608): 4 bytes = 09 00 00 00 (LE int32 = 9, the name length)
    # After name (2621): padding to align to 4 (3 bytes of 0x00)
    # Then some metadata bytes
    # At offset 2774: 4 bytes = length of text data (589824)
    
    # The hex around name showed:
    # 00000000 09000000 6c6f635f70742d6272 00000001000000000000000000adf24110...
    # That's: [padding] [name_len=9] [name='loc_pt-br'] [3 null padding] [metadata...]
    
    # At offset 2774 we found length=589824 (0x00090000 LE = nope, let's check)
    # 589824 in hex = 0x00090000? No, 589824 = 0x00090000? 589824 / 256 = 2304, nope
    # 589824 = 0x0008FFC0? Let me check: 589824 = 9*65536 + 0*256 + 0 = 589824
    # Actually 589824 = 0x00090000? 9*65536 = 589824. Yes! So LE bytes: 00 00 09 00
    
    # The text starts at offset 2778 (2774 + 4)
    # But the preview showed it starts with '\x00\x00loc_pt-br\x00\x00\x00p\r.\x00Regi...'
    # So there's still some junk at the beginning
    
    # Let's find the actual text start by looking for the first real text after the length
    
    # Find the length prefix at offset 2774
    offset_2774 = 2774
    length_at_2774 = struct.unpack_from('<I', cab_data, offset_2774)[0]
    print(f"Length at offset 2774: {length_at_2774}")
    
    # The data starts at 2778
    raw_text = cab_data[2778:2778 + length_at_2774]
    
    # Now let's find where the actual Portuguese text starts
    # Skip past the header junk (name field embedded in the data?)
    # Looking at the preview: \x00\x00loc_pt-br\x00\x00\x00p\r.\x00Regi...
    # The real text starts with "Regi" (as in "Regiao invalida...")
    
    # Find first occurrence of a real text line
    # The format seems to be: entries separated by \r\n with no keys
    # Each line is just the translated string value
    
    # Skip binary header
    text_start = 0
    # Find the first printable character sequence after initial bytes
    for i in range(len(raw_text)):
        if i + 10 < len(raw_text):
            chunk = raw_text[i:i+10]
            # Look for start of real content (capital letter followed by lowercase)
            if chunk[0] >= 0x41 and chunk[0] <= 0x5A:  # A-Z
                # Check if reasonable text follows
                printable = sum(1 for b in chunk if 32 <= b < 127 or b >= 0xC0)
                if printable >= 8:
                    text_start = i
                    break
        # Also check for a line that starts right after \r\n or \n
        if raw_text[i:i+2] == b'\r\n' or raw_text[i:i+1] == b'\n':
            # Check what follows
            next_pos = i + (2 if raw_text[i:i+2] == b'\r\n' else 1)
            if next_pos + 5 < len(raw_text):
                next_chunk = raw_text[next_pos:next_pos+10]
                printable = sum(1 for b in next_chunk if 32 <= b < 127 or b >= 0xC0)
                if printable >= 8:
                    text_start = next_pos
                    break
    
    print(f"Text content starts at internal offset: {text_start}")
    print(f"First 20 bytes from start: {raw_text[text_start:text_start+20]}")
    
    # Actually, let's take a different approach. The data at offset 2778 has the full
    # TextAsset m_Script content. Let's look at what format it actually is.
    # 
    # Wait - looking more carefully at the "Found at offset 2774: length=589824"
    # and "Preview: b'\\x00\\x00loc_pt-br\\x00\\x00\\x00p\\r.\\x00Regi..."
    #
    # The \x00\x00 at the start + "loc_pt-br" suggests the length field might actually
    # be at a different offset. Let me look at this differently.
    #
    # Actually the issue is that the text data at offset 2778 includes:
    # - 2 null bytes
    # - "loc_pt-br" (9 bytes)  
    # - 3 null bytes (padding)
    # - "p\r.\x00" (4 bytes - some field)
    # - Then "Regiao invalida..."
    #
    # So the real text starts 18 bytes in (2+9+3+4 = 18)
    # Let's just find "Regi" in the raw data
    
    regi_idx = raw_text.find(b'Regi')
    if regi_idx >= 0:
        # Go back to find the very start of the first entry
        # Check if there's a \r\n or beginning-of-line indicator before
        line_start = regi_idx
        while line_start > 0 and raw_text[line_start-1] not in (0, 10, 13):
            line_start -= 1
        text_start = line_start
    
    # Actually, let me re-examine. The format might have a different structure.
    # Let's look at what's between the name and the actual text more carefully.
    # 
    # From the hex dump: offset 2608 area:
    # 00000000 09000000 6c6f635f70742d627200000001000000 000000000000 adf24110 3c4e2a61 01000000 002b000000 617373657473
    #
    # Breaking it down:
    # 00000000 - padding/previous data
    # 09000000 - name length = 9 (LE)
    # 6c6f635f70742d6272 - "loc_pt-br" 
    # 000000 - padding to align 4
    # 01000000 - some int (1)
    # 00000000 00 - more fields
    # adf24110 - hash?
    # 3c4e2a61 - more data
    # 01000000 - int (1)
    # 002b000000 - more data
    # 617373657473 - "assets"
    #
    # This is the AssetBundle manifest info, not the TextAsset itself.
    # The actual TextAsset m_Script data is stored in the DATA section,
    # referenced by offset from the metadata.
    
    # Let me just search for the actual text content in the full CAB data
    # The real localization text will be a large block starting with actual strings
    
    # From the debug we know text like "Regiao invalida" exists around offset 43000+
    # Let's find the FIRST occurrence of a recognizable text line
    
    # Actually, looking at the output again, the extracted data was 575973 bytes 
    # and had 18356 lines. It DID get the content but with some header junk.
    # Let's just clean it up properly.
    
    # The raw_text starts with: \x00\x00loc_pt-br\x00\x00\x00p\r.\x00Regi...
    # Let's find the actual text by looking for the first \r\n pattern
    
    # Better approach: find the byte that encodes the text length, right before the text
    # In Unity TextAsset serialized format:
    # The data section starts at an offset specified in the header
    # Let's parse the serialized file header properly
    
    # Parse Unity serialized file header
    header_offset = 0
    
    # Check endianness indicator byte
    # Modern Unity (format >= 22): first fields are big-endian
    # metadata_size (4 bytes), file_size (varies), version (4), data_offset (varies)
    
    metadata_size = struct.unpack_from('>I', cab_data, 0)[0]
    file_size_be = struct.unpack_from('>I', cab_data, 4)[0]
    version = struct.unpack_from('>I', cab_data, 8)[0]
    
    print(f"\nSerialized file header:")
    print(f"  metadata_size (BE): {metadata_size}")
    print(f"  file_size field (BE): {file_size_be}")
    print(f"  version: {version}")
    
    if version >= 22:
        # Version 22+ has 8-byte file_size and data_offset
        file_size_64 = struct.unpack_from('>Q', cab_data, 4)[0]
        data_offset = struct.unpack_from('>Q', cab_data, 12)[0]
        endian_byte = cab_data[20]
        print(f"  file_size (64-bit): {file_size_64}")
        print(f"  data_offset: {data_offset}")
        print(f"  endian byte: {endian_byte}")
    elif version >= 9:
        data_offset = struct.unpack_from('>I', cab_data, 12)[0]
        endian_byte = cab_data[16] if version >= 9 else 0
        print(f"  data_offset: {data_offset}")
        print(f"  endian byte: {endian_byte}")
    else:
        data_offset = 0
        endian_byte = 0
    
    # The text data is in the data section at data_offset
    # For TextAsset, the m_Script field will be at some offset within data section
    # Let's look at what's at the data_offset
    
    if data_offset > 0 and data_offset < len(cab_data):
        print(f"\n  Data section starts at: {data_offset}")
        # In the data section, the TextAsset stores:
        # - m_Name: int32 length + string + align4
        # - m_Script: int32 length + bytes
        
        # Find the first object data
        obj_data = cab_data[data_offset:]
        
        # Read name
        name_len = struct.unpack_from('<I', obj_data, 0)[0]
        print(f"  First object name length: {name_len}")
        if 0 < name_len < 100:
            name = obj_data[4:4+name_len].decode('utf-8', errors='replace')
            print(f"  First object name: '{name}'")
            
            # After name + padding to 4 bytes
            after_name = 4 + name_len
            after_name_aligned = (after_name + 3) & ~3
            
            # m_Script length
            script_len = struct.unpack_from('<I', obj_data, after_name_aligned)[0]
            print(f"  Script length: {script_len}")
            
            if 100000 < script_len < 5000000:
                script_start = after_name_aligned + 4
                script_data = obj_data[script_start:script_start + script_len]
                print(f"  Script data first 50 bytes: {script_data[:50]}")
                return script_data
    
    # Fallback: just use what we found before but clean it
    # Find the longest sequence of valid UTF-8 text
    print("\n  Using fallback: searching for text in raw data...")
    
    # Find offset where real text begins in the raw_text we extracted
    # Skip all leading null/binary bytes
    clean_start = 0
    for i in range(min(len(raw_text), 100)):
        if raw_text[i] >= 32 and raw_text[i] < 127:
            # Might be start of text, but check for name header
            if raw_text[i:i+9] == b'loc_pt-br':
                # Skip past this name + padding
                clean_start = i + 9
                while clean_start < len(raw_text) and raw_text[clean_start] == 0:
                    clean_start += 1
                # Skip any additional small header bytes
                continue
            else:
                clean_start = i
                break
    
    # Now find where text actually starts meaningfully
    # Look for first \r\n to find line structure
    first_newline = raw_text.find(b'\r\n', clean_start)
    if first_newline > clean_start:
        # Check what's before the first newline
        first_line = raw_text[clean_start:first_newline]
        print(f"  First line candidate: {first_line[:80]}")
    
    # Return from clean_start, trimming trailing nulls
    result = raw_text[clean_start:]
    # Trim trailing null bytes
    while result and result[-1] == 0:
        result = result[:-1]
    
    return result


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

cab_data = decompress_bundle(bundle_path)
print(f"Decompressed CAB: {len(cab_data)} bytes")

text_data = extract_text_assets(cab_data)

if text_data:
    try:
        text = text_data.decode('utf-8')
    except:
        text = text_data.decode('utf-8', errors='replace')
    
    text = text.rstrip('\x00')
    
    # Count lines and check format
    lines = text.split('\n')
    non_empty_lines = [l for l in lines if l.strip()]
    
    print(f"\nExtracted text: {len(text)} bytes, {len(lines)} lines, {len(non_empty_lines)} non-empty")
    
    # Check if it's the expected format
    # Show first 10 non-empty lines
    print("\nFirst 10 non-empty lines:")
    for i, line in enumerate(non_empty_lines[:10]):
        print(f"  {i}: {line[:100]}")
    
    print(f"\nLast 5 non-empty lines:")
    for line in non_empty_lines[-5:]:
        print(f"  {line[:100]}")
    
    # Save it
    out_dir = r"C:\Users\Flavio\Downloads\Free Fire Server\unity-loc-builder\Assets\BundleAssets"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "loc_pt-br.txt")
    
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f"\n{'=' * 80}")
    print(f"SUCCESS! Saved to: {out_path}")
    print(f"Size: {len(text)} bytes, Lines: {len(non_empty_lines)}")
else:
    # Dump for analysis
    dump_path = r"C:\Users\Flavio\Downloads\Free Fire Server\tools\cab_dump.bin"
    with open(dump_path, 'wb') as f:
        f.write(cab_data)
    print(f"\nFailed! CAB dumped to: {dump_path} ({len(cab_data)} bytes)")
