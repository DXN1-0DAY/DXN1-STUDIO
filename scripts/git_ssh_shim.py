#!/usr/bin/env python3
# GIT_SSH shim — the studio's honest pipe to GitHub when no ssh binary
# exists on the machine (this sandbox has none, and none is installable).
# git invokes: <shim> [-p port] [-l user] [-o key=value …] host [command…]
# We connect with paramiko using the repo's deploy keys and bridge stdio
# to the remote git-upload-pack / git-receive-pack, byte-honestly.
import os
import sys
import select
import base64
import paramiko

KEYS = [
    os.path.expanduser("~/.ssh/id_ed25519_dxn1"),
    "/home/z/my-project/.ssh_deploy/id_ed25519",
]


def parse(argv):
    port = 22
    user = "git"
    host = None
    cmd = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "-p" and i + 1 < len(argv):
            port = int(argv[i + 1])
            i += 2
        elif a == "-l" and i + 1 < len(argv):
            user = argv[i + 1]
            i += 2
        elif a == "-o" or a == "-i" or a == "-F":
            i += 2                      # option + its value: swallowed
        elif a.startswith("-"):
            i += 1                      # bare flags: swallowed
        elif host is None:
            if "@" in a:                # user@host — the user part wins
                user, a = a.split("@", 1)
            host = a
            i += 1
        else:
            cmd.append(a)
            i += 1
    return port, user, host, cmd


def main():
    port, user, host, cmd = parse(sys.argv[1:])
    if host is None or not cmd:
        # git's -G probes and option queries carry no command: they
        # only ask "could you speak at all?" — an honest yes.
        sys.exit(0)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    last_err = None
    for key in KEYS:
        try:
            client.connect(
                hostname=host,
                port=port,
                username=user,
                key_filename=key,
                look_for_keys=False,
                allow_agent=False,
                timeout=20,
                banner_timeout=20,
                auth_timeout=20,
            )
            break
        except Exception as e:            # try the next key, honestly
            last_err = e
    else:
        sys.stderr.write(f"git_ssh_shim: auth failed: {last_err}\n")
        sys.exit(255)

    try:
        transport = client.get_transport()
        channel = transport.open_session(timeout=20)
        channel.exec_command(" ".join(cmd))
        # ── the bridge: git's stdin → channel, channel → git's stdout.
        # Non-blocking select on both ends; a blocking stdin read here
        # once deadlocked the whole push (the 2026-09-15 lesson).
        stdin_fd = sys.stdin.fileno()
        stdout_fd = sys.stdout.fileno()
        stderr_fd = sys.stderr.fileno()
        os.set_blocking(stdin_fd, False)
        os.set_blocking(stdout_fd, False)
        os.set_blocking(stderr_fd, False)
        while True:
            want_read = [channel, stdin_fd] if not channel.exit_ready else [stdin_fd]
            want_read = [x for x in (channel, stdin_fd) if x is not None]
            r, _, _ = select.select(want_read, [channel, stdout_fd, stderr_fd], [], 0.05)
            if channel in r:
                if channel.recv_ready():
                    data = channel.recv(32768)
                    if data:
                        os.write(stdout_fd, data)
                if channel.recv_stderr_ready():
                    data = channel.recv_stderr(32768)
                    if data:
                        os.write(stderr_fd, data)
                if channel.closed or channel.eof_received:
                    # drain anything left in the buffers before closing
                    while channel.recv_ready():
                        os.write(stdout_fd, channel.recv(32768))
                    while channel.recv_stderr_ready():
                        os.write(stderr_fd, channel.recv_stderr(32768))
                    break
            if stdin_fd in r:
                try:
                    data = os.read(stdin_fd, 32768)
                except BlockingIOError:
                    data = None
                if data:
                    channel.sendall(data)
                elif not channel.closed:
                    channel.shutdown_write()
            if channel.exit_status_ready() and not channel.recv_ready() \
                    and not channel.recv_stderr_ready():
                # stdin drained? close our half so the remote can finish
                if not channel.closed:
                    try:
                        os.read(stdin_fd, 1)
                    except BlockingIOError:
                        pass
                    if channel.eof_received or not channel.send_ready():
                        break
        rc = channel.recv_exit_status()
        client.close()
        sys.exit(rc)
    except Exception as e:
        sys.stderr.write(f"git_ssh_shim: bridge failed: {e}\n")
        sys.exit(255)


if __name__ == "__main__":
    main()
