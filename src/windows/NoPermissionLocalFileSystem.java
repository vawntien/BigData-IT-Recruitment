package d04.localfs;

import java.io.IOException;
import java.io.File;

import org.apache.hadoop.fs.FileStatus;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.fs.RawLocalFileSystem;
import org.apache.hadoop.fs.permission.FsPermission;

/**
 * Local Hadoop filesystem adapter for Spark writes on Windows without winutils.
 *
 * Windows ACLs are inherited from the process. Hadoop's POSIX chmod/chown calls
 * require winutils.exe even though they are not meaningful for this local-only
 * staging pipeline, so only those two permission operations are made no-ops.
 */
public final class NoPermissionLocalFileSystem extends RawLocalFileSystem {
    @Override
    public void setPermission(Path path, FsPermission permission) throws IOException {
        // No POSIX permission operation on Windows local mode.
    }

    @Override
    public void setOwner(Path path, String username, String groupname) throws IOException {
        // Windows ACL ownership is outside the scope of this local Spark job.
    }

    @Override
    public FileStatus[] listStatus(Path path) throws IOException {
        FileStatus status = getFileStatus(path);
        if (status.isFile()) {
            return new FileStatus[] {status};
        }
        File[] files = pathToFile(path).listFiles();
        if (files == null) {
            throw new IOException("Unable to list local directory: " + path);
        }
        FileStatus[] statuses = new FileStatus[files.length];
        for (int index = 0; index < files.length; index++) {
            statuses[index] = getFileStatus(new Path(files[index].toURI()));
        }
        return statuses;
    }
}
