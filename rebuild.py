"""Rebuild this release from its standalone EXE and the source overlay.

No sibling workspace, credentials, Godot installation or Python package needed.
The release EXE supplies the existing engine and compiled scene/resource base.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parent

def read_base(path):
    data = path.read_bytes()
    if data[-4:] != b'GDPC':
        raise ValueError('Base EXE has no embedded Godot pack footer')
    length = struct.unpack_from('<Q', data, len(data)-12)[0]
    start = len(data)-12-length
    if start <= 0 or data[start:start+4] != b'GDPC':
        raise ValueError('Invalid embedded pack size')
    pack = data[start:-12]
    version, major, minor, patch, flags, base, directory = struct.unpack_from('<IIIIIQQ', pack, 4)
    if (version,major,minor,patch,flags,base) != (4,4,7,2,2,112):
        raise ValueError('Expected the 1.0.0 Godot 4.7.2 executable pack')
    pos = directory
    count = struct.unpack_from('<I',pack,pos)[0]
    pos += 4
    entries = {}
    for _ in range(count):
        size = struct.unpack_from('<I',pack,pos)[0]
        pos += 4
        name = pack[pos:pos+size].rstrip(b'\0').decode('utf-8')
        pos += size
        offset, size = struct.unpack_from('<QQ',pack,pos)
        md5 = pack[pos+16:pos+32]
        entry_flags = struct.unpack_from('<I',pack,pos+32)[0]
        pos += 36
        if entry_flags != 0:
            raise ValueError('Unsupported resource flags: '+name)
        resource = PurePosixPath(name)
        if resource.is_absolute() or '..' in resource.parts:
            raise ValueError('Unsafe resource name')
        body = pack[base+offset:base+offset+size]
        if len(body) != size or hashlib.md5(body).digest() != md5:
            raise ValueError('Resource checksum mismatch: '+name)
        entries[name] = body
    if pos != len(pack):
        raise ValueError('Unexpected bytes after resource directory')
    return data[:start],entries

def build(base_path, destination):
    engine,entries = read_base(base_path)
    for path in sorted((ROOT/'source').rglob('*')):
        if not path.is_file():
            continue
        name = path.relative_to(ROOT/'source').as_posix()
        entries.pop(name+'.remap',None)
        if name.endswith('.gd'):
            entries.pop(name+'c',None)
        entries[name] = path.read_bytes()
    body = bytearray()
    directory = []
    for name,resource in sorted(entries.items()):
        offset = len(body)
        body.extend(resource)
        body.extend(b'\0'*((-len(body))%16))
        encoded = name.encode('utf-8')
        encoded += b'\0'*((-len(encoded))%4)
        directory.append(struct.pack('<I',len(encoded))+encoded+struct.pack('<QQ',offset,len(resource))+hashlib.md5(resource).digest()+struct.pack('<I',0))
    header = b'GDPC'+struct.pack('<IIIIIQQ',4,4,7,2,2,112,112+len(body))+b'\0'*72
    pack = header+body+struct.pack('<I',len(directory))+b''.join(directory)
    output = engine+b'\0'*((-len(engine))%8)+pack+struct.pack('<Q',len(pack))+b'GDPC'
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(output)
    result = {'executable':destination.name,'bytes':len(output),'sha256':hashlib.sha256(output).hexdigest(),'resources':len(entries),'base_executable_sha256':hashlib.sha256(base_path.read_bytes()).hexdigest()}
    destination.with_suffix('.manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,required=True,help='Downloaded 1.0.0 standalone EXE')
    parser.add_argument('--output',type=Path,default=ROOT/'现代突击者_正式版.exe')
    args = parser.parse_args()
    if args.base.resolve() == args.output.resolve():
        parser.error('Choose an output different from the base EXE')
    print(json.dumps(build(args.base,args.output),ensure_ascii=True))
