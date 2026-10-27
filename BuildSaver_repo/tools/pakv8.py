"""Minimal Unreal .pak writer (version 8B, uncompressed, unencrypted) - the format of legacy UI paks.
usage: pakv8.py build <out.pak> <root_dir> [mount]      (all files under root_dir, sorted)
       pakv8.py list <in.pak>"""
import hashlib, os, struct, sys

MAGIC = 0x5A6F12E1

def fstring(s):
    b = s.encode("ascii") + b"\0"
    return struct.pack("<i", len(b)) + b

def entry(offset, data):
    # Offset, CompressedSize, Size, CompressionMethodIndex(u32), SHA1, bEncrypted, CompressionBlockSize
    return struct.pack("<QQQI", offset, len(data), len(data), 0) + hashlib.sha1(data).digest() + b"\0" + struct.pack("<I", 0)

def build(out, root, mount="../../../"):
    files = []
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            files.append((os.path.relpath(p, root).replace(os.sep, "/"), p))
    files.sort(key=lambda t: t[0].lower())
    blob, index, offs = bytearray(), bytearray(), {}
    for name, p in reversed(files):              # data in reverse index order (same as common pak tools)
        data = open(p, "rb").read()
        offs[name] = (len(blob), data)
        blob += entry(0, data) + data            # inline header has offset 0
    index += fstring(mount) + struct.pack("<I", len(files))
    for name, _ in files:
        off, data = offs[name]
        index += fstring(name) + entry(off, data)
    footer = b"\0" * 16 + b"\0" + struct.pack("<IIQQ", MAGIC, 8, len(blob), len(index)) + hashlib.sha1(index).digest() + b"\0" * 160
    with open(out, "wb") as f:
        f.write(blob + index + footer)
    return [n for n, _ in files]

def listing(path):
    b = open(path, "rb").read()
    i = len(b) - 221 + 17
    magic, ver, ioff, isz = struct.unpack_from("<IIQQ", b, i)
    assert magic == MAGIC and ver == 8, (hex(magic), ver)
    idx = b[ioff:ioff + isz]
    assert hashlib.sha1(idx).digest() == b[i + 24:i + 44], "index hash"
    j = 0
    n = struct.unpack_from("<i", idx, j)[0]; mount = idx[4:4 + n - 1].decode(); j = 4 + n
    cnt = struct.unpack_from("<I", idx, j)[0]; j += 4
    out = []
    for _ in range(cnt):
        n = struct.unpack_from("<i", idx, j)[0]; name = idx[j + 4:j + 3 + n].decode(); j += 4 + n
        off, csz, usz, cm = struct.unpack_from("<QQQI", idx, j); sha = idx[j + 28:j + 48]; j += 53
        data = b[off + 53:off + 53 + usz]
        assert hashlib.sha1(data).digest() == sha, name + " sha1"
        out.append((name, usz))
    return mount, out

if __name__ == "__main__":
    if sys.argv[1] == "build":
        print("\n".join(build(sys.argv[2], sys.argv[3], *(sys.argv[4:5] or []))))
    else:
        m, files = listing(sys.argv[2]); print("mount", m)
        for n, s in files: print(s, n)
