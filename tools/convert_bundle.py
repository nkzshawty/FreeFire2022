import struct
import os
import sys
import shutil

def read_string_from_bytes(data, offset):
    """Read null-terminated string from bytes, return (string, new_offset)"""
    end = data.index(b'\x00', offset)
    return data[offset:end].decode('utf-8'), end + 1

def convert_bundle(input_path, output_path):
    """Convert a Unity format 8 (2022) bundle to format 6 (2018)"""
    with open(input_path, 'rb') as f:
        data = bytearray(f.read())
    
    original_size = len(data)
    
    # Parse header
    offset = 0
    sig_end = data.index(b'\x00', offset)
    signature = data[offset:sig_end].decode('utf-8')
    offset = sig_end + 1
    
    if signature != "UnityFS":
        print(f"  SKIP: Not a UnityFS bundle ({signature})")
        return False
    
    # Format version (uint32 BE)
    format_version = struct.unpack_from('>I', data, offset)[0]
    format_version_offset = offset
    offset += 4
    
    if format_version == 6:
        print(f"  SKIP: Already format 6 (Unity 2018 compatible)")
        if os.path.abspath(input_path) != os.path.abspath(output_path):
            shutil.copy2(input_path, output_path)
        return True
    
    if format_version != 8:
        print(f"  SKIP: Unexpected format version {format_version}")
        return False
    
    # Unity version string
    unity_ver, offset = read_string_from_bytes(data, offset)
    
    # Generator version string
    generator_start = offset
    generator_ver, offset = read_string_from_bytes(data, offset)
    generator_end = offset
    
    print(f"  Format: {format_version}, Unity: {unity_ver}, Generator: {generator_ver}")
    
    # File size (uint64 BE)
    file_size_offset = offset
    file_size = struct.unpack_from('>Q', data, offset)[0]
    offset += 8
    
    # Compressed block info size (uint32 BE)
    compressed_size_offset = offset
    compressed_size = struct.unpack_from('>I', data, offset)[0]
    offset += 4
    
    # Uncompressed block info size (uint32 BE)
    uncompressed_size_offset = offset
    uncompressed_size = struct.unpack_from('>I', data, offset)[0]
    offset += 4
    
    # Flags (uint32 BE)
    flags_offset = offset
    flags = struct.unpack_from('>I', data, offset)[0]
    offset += 4
    
    header_end = offset  # Should be 50
    print(f"  Header end: {header_end}, file_size: {file_size}, flags: 0x{flags:08X}")
    
    # Check for alignment padding (format 8 aligns to 16 bytes)
    padding_size = 0
    if format_version >= 7:
        aligned_offset = (header_end + 15) & ~15
        padding_size = aligned_offset - header_end
        # Verify it's actually zero padding
        padding_bytes = data[header_end:header_end + padding_size]
        if all(b == 0 for b in padding_bytes):
            print(f"  Alignment padding: {padding_size} bytes (offset {header_end} to {aligned_offset})")
        else:
            print(f"  WARNING: Expected zero padding but found non-zero bytes at {header_end}")
            padding_size = 0
    
    # --- CONVERSION ---
    
    # 1. Change format version: 8 -> 6
    struct.pack_into('>I', data, format_version_offset, 6)
    
    # 2. Replace generator version string (same length!)
    new_generator = b'2018.4.11f1\x00'
    old_generator = b'2022.3.47f1\x00'
    if data[generator_start:generator_end] == old_generator:
        data[generator_start:generator_end] = new_generator
    else:
        # Try finding it
        idx = data.find(old_generator)
        if idx >= 0:
            data[idx:idx+len(old_generator)] = new_generator
        else:
            print(f"  WARNING: Could not find generator string to replace")
    
    # 3. Change flags: remove 0x200 bit
    new_flags = flags & ~0x200
    struct.pack_into('>I', data, flags_offset, new_flags)
    
    # 4. Remove alignment padding
    if padding_size > 0:
        data = data[:header_end] + data[header_end + padding_size:]
        # 5. Adjust file_size
        new_file_size = file_size - padding_size
        struct.pack_into('>Q', data, file_size_offset, new_file_size)
    
    # Write output
    with open(output_path, 'wb') as f:
        f.write(data)
    
    print(f"  Converted: {original_size} -> {len(data)} bytes (removed {original_size - len(data)} bytes)")
    print(f"  Output: {output_path}")
    return True

def main():
    bundle_dir = r"C:\Users\Flavio\Downloads\Free Fire Server\static\ABHotUpdates\android\optional\optionallocres\99\gameassetbundles"
    
    print("=" * 70)
    print("Unity Bundle Converter: Format 8 (2022) -> Format 6 (2018)")
    print("=" * 70)
    
    converted = 0
    skipped = 0
    
    for fname in sorted(os.listdir(bundle_dir)):
        fpath = os.path.join(bundle_dir, fname)
        if not os.path.isfile(fpath) or os.path.getsize(fpath) < 50:
            continue
        
        print(f"\nProcessing: {fname}")
        
        # Check if it starts with UnityFS
        with open(fpath, 'rb') as f:
            magic = f.read(7)
        
        if magic != b'UnityFS':
            print(f"  SKIP: Not UnityFS (starts with {magic[:8].hex()})")
            skipped += 1
            continue
        
        # Convert in-place (overwrite the original)
        if convert_bundle(fpath, fpath):
            converted += 1
        else:
            skipped += 1
    
    print(f"\n{'=' * 70}")
    print(f"Done! Converted: {converted}, Skipped: {skipped}")
    print(f"{'=' * 70}")

if __name__ == '__main__':
    main()
