import ctypes,os,pathlib
def sandbox(read,write):
    # Linux Landlock ABI1: deny read/write outside explicit paths (incl all Gold).
    lib=ctypes.CDLL(None,use_errno=True)
    class Ruleset(ctypes.Structure):_fields_=[('access',ctypes.c_uint64)]
    class Beneath(ctypes.Structure):_pack_=1;_fields_=[('access',ctypes.c_uint64),('fd',ctypes.c_int32)]
    handled=(1<<13)-1;fd=lib.syscall(444,ctypes.byref(Ruleset(handled)),8,0)
    if fd<0:raise OSError(ctypes.get_errno(),'Landlock required, no label-readable fallback')
    for path,access in [(p,(1<<0)|(1<<2)|(1<<3)) for p in read]+[(p,handled) for p in write]:
        pfd=os.open(path,os.O_PATH|os.O_CLOEXEC)
        if not pathlib.Path(path).is_dir():access&=~(1<<3)
        rule=Beneath(access,pfd)
        if lib.syscall(445,fd,1,ctypes.byref(rule),0):raise OSError(ctypes.get_errno(),str(path))
        os.close(pfd)
    if lib.prctl(38,1,0,0,0) or lib.syscall(446,fd,0):raise OSError(ctypes.get_errno(),'restrict_self')
    os.close(fd)
