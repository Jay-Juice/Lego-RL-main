"""Read only bounded Python workspace data. Never receives issue/focus/PI inputs.
Stdlib only, suitable for stdin Python in disposable or real task container.
"""
import hashlib,json,os,pathlib,stat,time
SKIP={'.git','.hg','.svn','.venv','venv','env','site-packages','node_modules','__pycache__','tests','test','testing','fixtures','verifier','oracle','gold','reference','private','artifacts','logs','checkpoints','build','dist','.tox','.mypy_cache','.pytest_cache','docs','examples','benchmarks'}
def allowed(path):
    p=pathlib.PurePosixPath(path)
    if not path or p.is_absolute() or '..' in p.parts or '\\' in path or '\x00' in path:return False
    if any(s.lower() in SKIP or s.startswith('.') or any(w in s.lower() for w in ['oracle','gold_patch','reference_patch','fail_to_pass','pass_to_pass','injection','mutation']) for s in p.parts):return False
    return p.suffix=='.py' and not p.name.startswith('test_') and not p.name.endswith('_test.py')
def read_nofollow(root,rel):
    """Linux component-by-component openat; no symlink traversal race."""
    if os.name!='posix':
        p=root/rel
        if any((root/pathlib.Path(*pathlib.PurePosixPath(rel).parts[:i])).is_symlink() for i in range(1,len(pathlib.PurePosixPath(rel).parts)+1)):raise OSError('symlink')
        return p.open('rb')
    fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
    try:
        parts=pathlib.PurePosixPath(rel).parts
        for part in parts[:-1]:
            nxt=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=nxt
        source=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd)
        return os.fdopen(source,'rb')
    finally:os.close(fd)
def collect(root='/testbed'):
    start=time.monotonic();root=pathlib.Path(root).resolve();files={};identities={};bytes_read=0;walked=0;excluded=0;limited=False;large=0
    for base,dirs,names in os.walk(root,followlinks=False):
        walked+=len(dirs)
        if walked>50000:limited=True;break
        dirs[:]=sorted(d for d in dirs if d.lower() not in SKIP and not d.startswith('.') and not pathlib.Path(base,d).is_symlink() and not any(x in d.lower() for x in ['oracle','injection','mutation']))
        for name in sorted(names):
            walked+=1
            if walked>50000:limited=True;break
            p=pathlib.Path(base,name);rel=p.relative_to(root).as_posix()
            if not allowed(rel):excluded+=1;continue
            s=p.lstat()
            if not stat.S_ISREG(s.st_mode) or not p.resolve().is_relative_to(root):excluded+=1;continue
            if s.st_size>262144:large+=1;limited=True;continue
            if len(files)>=1500 or bytes_read+s.st_size>8388608:limited=True;break
            try:
                with read_nofollow(root,rel) as f:
                    a=os.fstat(f.fileno());raw=f.read(262145);b=os.fstat(f.fileno())
                if len(raw)>262144 or (a.st_ino,a.st_size,a.st_mtime_ns)!=(b.st_ino,b.st_size,b.st_mtime_ns):return dict(files={},stable=False,limited=True,reason='file_changed_during_read')
                text=raw.decode('utf-8-sig')
            except (OSError,UnicodeDecodeError):excluded+=1;limited=True;continue
            files[rel]=text;bytes_read+=len(raw);identities[rel]=(b.st_dev,b.st_ino,b.st_size,b.st_mtime_ns)
        if limited and (len(files)>=1500 or bytes_read>=8388608 or walked>50000):break
    stable=True
    for rel,identity in identities.items():
        try:
            s=(root/rel).lstat()
            if stat.S_ISLNK(s.st_mode) or (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)!=identity:stable=False
        except OSError:stable=False
    return dict(files=files,stable=stable,limited=limited,read_bytes=bytes_read,source_file_count=len(files),walked_entries=walked,excluded_entries=excluded,oversized_files=large,wall_seconds=time.monotonic()-start,scope='bounded Python source; excluded tests/private/dependencies; not full environment snapshot')
if __name__=='__main__':print(json.dumps(collect()))
