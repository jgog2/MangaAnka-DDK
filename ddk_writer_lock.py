"""Process-scoped OS lock for writable DDK application instances."""
import os
from pathlib import Path


class WriterLock:
    def __init__(self,database_path):
        self.path=Path(str(Path(database_path).resolve())+'.writer.lock')
        self.handle=open(self.path,'a+b')
        try:
            self.handle.seek(0,os.SEEK_END)
            if self.handle.tell()==0:self.handle.write(b'\0');self.handle.flush()
            self.handle.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except (OSError,BlockingIOError) as exc:
            self.handle.close()
            raise ValueError('This database is already open for writing in another DDK instance.') from exc

    def close(self):
        if self.handle.closed:return
        self.handle.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(self.handle.fileno(),msvcrt.LK_UNLCK,1)
        else:
            import fcntl
            fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN)
        self.handle.close()
