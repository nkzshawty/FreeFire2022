import struct
import sys
import os

try:
    import lz4.block
except ImportError:
    print("ERROR: lz4 not installed")
    sys.exit(1)

# Find the bundle
search_dir = r"C:\Users\Flavio\Downloads\com.dts.freefireth"
bundle_path = None
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

with open(bundle_path, 'rb') as f:
    data = f.read()

print(f"File: {bundle_path}")
print(f"Size: {len(data)} bytes")
print(f"First 100 bytes hex: {data[:100].hex()}")
print()

# Parse header manually
offset = 0
sig_end = data.index(b'\x00', offset)
sig = data[offset:sig_end]
print(f"Signature: {sig} (bytes: {sig.hex()})")
offset = sig_end + 1

fmt_ver = struct.unpack_from('>I', data, offset)[0]
offset += 4
print(f"Format version: {fmt_ver}")

ver_end = data.index(b'\x00', offset)
unity_ver = data[offset:ver_end].decode('ascii')
offset = ver_end + 1
print(f"Unity version: '{unity_ver}'")

gen_end = data.index(b'\x00', offset)
generator = data[offset:gen_end].decode('ascii')
offset = gen_end + 1
print(f"Generator: '{generator}'")

file_size = struct.unpack_from('>Q', data, offset)[0]
offset += 8
print(f"File size: {file_size}")

cb_size = struct.unpack_from('>I', data, offset)[0]
offset += 4
print(f"Compressed block info size: {cb_size}")

ub_size = struct.unpack_from('>I', data, offset)[0]
offset += 4
print(f"Uncompressed block info size: {ub_size}")

flags = struct.unpack_from('>I', data, offset)[0]
offset += 4
print(f"Flags: 0x{flags:08X}")
print(f"  Compression: {flags & 0x3F}")
print(f"  Block info at end: {bool(flags & 0x80)}")
print(f"  Padding after block info: {bool(flags & 0x200)}")

print(f"\nHeader ends at byte: {offset}")

# For format 7+, align to 16 bytes  
if fmt_ver >= 7:
    aligned = (offset + 15) & ~15
    print(f"Aligned header end: {aligned}")
    # The block info data immediately follows the header (before alignment padding)
    # OR does alignment apply before block info?
    # Let's check: in UnityFS format 6+, the structure is:
    # header | [padding] | block_info | data_blocks
    # But with flag 0x80, block_info is at end of file
    
    # Standard layout (block_info NOT at end):
    # header(50 bytes) -> align to 16 -> block_info(183 compressed) -> data_blocks
    # header end = 50, aligned = 64
    # block info at 64, 183 bytes long
    # data starts at 64 + 183 = 247
    
    offset = aligned

print(f"\nBlock info starts at: {offset}")
block_info_raw = data[offset:offset+cb_size]
print(f"Block info first 20 bytes: {block_info_raw[:20].hex()}")

# Try to decompress block info with LZ4
compression = flags & 0x3F
if compression == 3 or compression == 2:
    # Try standard decompress
    try:
        block_info = lz4.block.decompress(block_info_raw, uncompressed_size=ub_size)
        print(f"Block info decompressed OK: {len(block_info)} bytes")
    except Exception as e:
        print(f"Block info decompress failed: {e}")
        # Try with size prefix
        try:
            block_info = lz4.block.decompress(struct.pack('<I', ub_size) + block_info_raw)
            print(f"Block info decompressed with prefix: {len(block_info)} bytes")
        except Exception as e2:
            print(f"Block info decompress with prefix also failed: {e2}")
            sys.exit(1)

data_start = offset + cb_size
print(f"\nData blocks start at: {data_start}")
print(f"Remaining data: {len(data) - data_start} bytes")

# Parse block info
bi_offset = 16  # skip hash
block_count = struct.unpack_from('>I', block_info, bi_offset)[0]
bi_offset += 4
print(f"\nBlock count: {block_count}")

blocks = []
total_compressed = 0
total_uncompressed = 0
for i in range(block_count):
    uncomp = struct.unpack_from('>I', block_info, bi_offset)[0]
    bi_offset += 4
    comp = struct.unpack_from('>I', block_info, bi_offset)[0]
    bi_offset += 4
    bflags = struct.unpack_from('>H', block_info, bi_offset)[0]
    bi_offset += 2
    blocks.append((uncomp, comp, bflags))
    total_compressed += comp
    total_uncompressed += uncomp

print(f"Total compressed: {total_compressed} bytes")
print(f"Total uncompressed: {total_uncompressed} bytes")
print(f"Available data: {len(data) - data_start} bytes")
print(f"Difference (available - total_compressed): {len(data) - data_start - total_compressed}")

# Try decompressing first block
print(f"\n--- First block details ---")
uncomp, comp, bflags = blocks[0]
print(f"  Uncompressed: {uncomp}, Compressed: {comp}, Flags: 0x{bflags:04X}")
print(f"  Block compression: {bflags & 0x3F}")

first_block = data[data_start:data_start+comp]
print(f"  First 32 bytes: {first_block[:32].hex()}")

# Try different decompression approaches
print("\n  Trying decompress approaches:")

# Approach 1: standard
try:
    result = lz4.block.decompress(first_block, uncompressed_size=uncomp)
    print(f"  [1] Standard: OK! {len(result)} bytes")
except Exception as e:
    print(f"  [1] Standard: FAILED - {e}")

# Approach 2: with store_size prefix
try:
    result = lz4.block.decompress(struct.pack('<I', uncomp) + first_block)
    print(f"  [2] With size prefix: OK! {len(result)} bytes")
except Exception as e:
    print(f"  [2] With size prefix: FAILED - {e}")

# Approach 3: skip first 4 bytes (maybe there's a size header in the data)
try:
    # Maybe the compressed data itself has a 4-byte size prefix
    actual_data = first_block[4:]
    result = lz4.block.decompress(actual_data, uncompressed_size=uncomp)
    print(f"  [3] Skip 4 bytes: OK! {len(result)} bytes")
except Exception as e:
    print(f"  [3] Skip 4 bytes: FAILED - {e}")

# Approach 4: maybe the compressed sizes in block info are wrong - try +/- a few bytes
for delta in [-4, -2, -1, 1, 2, 4]:
    try:
        adjusted = data[data_start:data_start+comp+delta]
        result = lz4.block.decompress(adjusted, uncompressed_size=uncomp)
        print(f"  [4] Adjusted size by {delta}: OK! {len(result)} bytes")
        break
    except:
        pass

# Approach 5: maybe data starts at a different offset
print("\n  Trying different data start offsets:")
for test_offset in [48, 50, 52, 54, 56, 58, 60, 62, 64, 66, 128, 183, 247, 248, 250, 252, 256]:
    try:
        test_data = data[test_offset:test_offset+comp]
        result = lz4.block.decompress(test_data, uncompressed_size=uncomp)
        print(f"  Offset {test_offset}: OK! {len(result)} bytes")
        # Check if it contains XML
        if b'<l ' in result or b'xml' in result:
            print(f"    Contains XML markers!")
        break
    except:
        pass
else:
    print("  None of the tested offsets worked")

# Let's also check if the data could be at offset after the aligned header without block_info in between
# Maybe for format 8, block_info is stored differently
print(f"\n--- Checking raw bytes at key offsets ---")
for check_offset in [50, 64, 128, 247, 256]:
    print(f"  Bytes at {check_offset}: {data[check_offset:check_offset+16].hex()}")
