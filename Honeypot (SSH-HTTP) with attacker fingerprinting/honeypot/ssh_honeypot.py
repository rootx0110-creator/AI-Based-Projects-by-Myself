import socket
import threading
import logging
import random
import time
import datetime
import json
import paramiko

from . import database
from .fingerprint import SSH_DUMMY_VERSIONS, analyze_request

logger = logging.getLogger(__name__)

FAKE_BANNER = random.choice(SSH_DUMMY_VERSIONS)
FAKE_USERS = {
    "root": "toor",
    "admin": "admin123",
    "user": "password",
}
DUMMY_FILE_SYSTEM = {
    "/": ["bin", "boot", "dev", "etc", "home", "lib", "opt", "proc", "root", "sbin", "tmp", "usr", "var"],
    "/etc": ["passwd", "shadow", "hostname", "ssh", "network", "nginx", "apt", "sysctl.conf"],
    "/etc/ssh": ["sshd_config", "authorized_keys", "ssh_host_rsa_key"],
    "/home": ["user", "admin", "root"],
    "/root": ["passwords.txt", ".bash_history", "scripts", "interesting.txt"],
    "/var": ["log", "www", "cache", "tmp", "lib"],
    "/var/www": ["index.html", "config.php", "wp-config.php", ".htaccess"],
    "/tmp": ["ids", "logs", "uploads"],
    "/usr": ["bin", "local", "lib", "share"],
    "/opt": ["backups", "ippy", "scripts"],
}
DUMMY_COMMANDS_OUTPUT = {
    "whoami": True,
    "id": True,
    "uname -a": True,
    "ls": True,
    "pwd": True,
    "cat /etc/passwd": True,
    "cat /etc/ssh/sshd_config": True,
    "ifconfig": True,
    "ip addr": True,
    "wget": True,
    "curl": True,
    "w": True,
    "route": True,
}


class SSHServer(paramiko.ServerInterface):
    def __init__(self, client_socket, addr, on_event, on_fingerprint):
        self.client_socket = client_socket
        self.addr = addr
        self.username = None
        self.password = None
        self.commands = []
        self.on_event = on_event
        self.on_fingerprint = on_fingerprint
        self.started_at = time.time()

    def check_auth_none(self, username):
        self.username = username
        self._log_auth(username, "", "none")
        return paramiko.AUTH_FAILED

    def check_auth_password(self, username, password):
        self.username = username
        self.password = password
        self._log_auth(username, password, "password")
        if username in FAKE_USERS and FAKE_USERS[username] == password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        self.username = username
        self._log_auth(username, "", "publickey")
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def _log_auth(self, username, password, method):
        try:
            self.on_event({
                "protocol": "ssh",
                "src_ip": self.addr[0],
                "src_port": self.addr[1],
                "event_type": "ssh_auth",
                "username": username,
                "password": password,
                "raw_data": f"auth method: {method}",
            })
        except Exception as e:
            logger.error(f"Failed to log auth: {e}")

    def get_allowed_auths(self, username):
        return "none,password,publickey"

    def check_channel_shell_request(self, channel):
        self._run_shell(channel)
        return True

    def check_channel_exec_request(self, channel, command):
        self.commands.append(command.decode() if isinstance(command, bytes) else command)
        self._run_command(channel, command)
        return True

    def _run_shell(self, channel):
        threading.Thread(target=self._shell_loop, args=(channel,), daemon=True).start()

    def _shell_loop(self, channel):
        channel.sendall(b"Welcome to Ubuntu 22.04 LTS\r\n\r\n")
        channel.sendall(b"Last login: " + datetime.datetime.now().strftime("%a %b %d %H:%M:%S").encode() + b" from unknown\r\n")
        prompt = b"$ "
        channel.sendall(b"$ ")
        buf = b""
        try:
            while True:
                if not channel.recv_ready():
                    time.sleep(0.1)
                    continue
                data = channel.recv(256).decode(errors="ignore")
                buf += data.encode("latin-1", errors="ignore") if isinstance(data, str) else data
                while b"\n" in buf or b"\r" in buf:
                    line, buf = self._extract_line(buf)
                    if line is None:
                        continue
                    cmd = line.strip()
                    if cmd:
                        self.commands.append(cmd)
                        self._process_dummy_command(channel, cmd)
                    channel.sendall(prompt)
        except Exception:
            pass
        finally:
            try:
                channel.close()
            except Exception:
                pass
            self._save_session()

    def _extract_line(self, buf):
        for sep in (b"\r\n", b"\n", b"\r"):
            if sep in buf:
                line, rest = buf.split(sep, 1)
                return line, rest
        return None, buf

    def _run_command(self, channel, command):
        try:
            cmd = command.decode() if isinstance(command, bytes) else command
            self._log_command(cmd)
            self._process_dummy_command(channel, cmd.strip())
            channel.send_exit_status(0)
            channel.close()
        except Exception:
            pass
        finally:
            self._save_session()

    def _log_command(self, cmd):
        try:
            self.on_event({
                "protocol": "ssh",
                "src_ip": self.addr[0],
                "src_port": self.addr[1],
                "dst_port": 22,
                "event_type": "ssh_command",
                "username": self.username,
                "raw_data": cmd,
            })
        except Exception as e:
            logger.error(e)

    def _save_session(self):
        if not self.commands:
            return
        try:
            database.insert_ssh_session({
                "event_id": None,
                "client_version": "unknown",
                "auth_method": "shell/exec",
                "commands": self.commands,
                "session_duration": round(time.time() - self.started_at, 2),
            })
        except Exception as e:
            logger.error(e)

    def _process_dummy_command(self, channel, cmd):
        if cmd in ["whoami", "id"]:
            channel.sendall(b"uid=0(root) gid=0(root) groups=0(root)\r\n")
        elif cmd in ["uname -a", "uname"]:
            channel.sendall(b"Linux honeypot 5.15.0-76-generic #83-Ubuntu SMP Thu Jun 15 19:16:32 UTC 2026 x86_64 x86_64 x86_64 GNU/Linux\r\n")
        elif cmd in ["pwd", "."]:
            channel.sendall(b"/root\r\n")
        elif cmd in ["ls", "ls -la"]:
            channel.sendall(b"total 8\r\ndrwx------ 2 root root 4096 Jun 15 10:32 .\r\ndrwxr-xr-x 22 root root 4096 Jun 15 10:21 ..\r\n-rw-r--r-- 1 root root  1924 Jun 15 10:32 credentials.txt\r\n-rw-r--r-- 1 root root   888 Jun 15 10:32 .bash_history\r\n")
        elif cmd in ["cat /etc/passwd", "cat /etc/shadow"]:
            channel.sendall(b"root:x:0:0:root:/root:/bin/bash\r\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\r\nubuntu:x:1000:1000:Ubuntu:/home/ubuntu:/bin/bash\r\n")
        elif cmd == "cat /etc/hostname":
            channel.sendall(b"honeypot-01\r\n")
        elif cmd == "ifconfig":
            channel.sendall(b"eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\r\n        inet " + self.addr[0].encode() + b"  netmask 255.255.255.0  broadcast 255.255.255.255\r\n")
        elif cmd in ["wget", "curl"]:
            channel.sendall(b"wget: command not found\r\n")
        elif cmd == "exit":
            channel.sendall(b"logout\r\n")
            try:
                channel.close()
            except Exception:
                pass
        elif cmd in ["history", "cat ~/.bash_history"]:
            channel.sendall(b" 1  cd /var/www\r\n 2  ls -la\r\n 3  cat index.html\r\n 4  passwd\r\n 5  exit\r\n")
        elif cmd in ["cat credentials.txt", "cat /root/credentials.txt"]:
            channel.sendall(b"admin:SuperSecret2024!\r\nroot:h4ckedPassw0rd\r\ndb_admin:dbPass12345\r\n")
        elif cmd in ["mysql", "sqlite3"]:
            channel.sendall(b"ERROR 2002 (HY000): Can't connect to local MySQL server\r\n")
        elif cmd == "git --version":
            channel.sendall(b"git version 2.34.1\r\n")
        elif cmd == "python3 --version":
            channel.sendall(b"Python 3.10.12\r\n")
        elif cmd.startswith("echo"):
            channel.sendall(cmd[5:].encode() + b"\r\n")
        elif cmd in ["ls -la /tmp", "ls /tmp"]:
            channel.sendall(b"total 0\r\ndrwxrwxrwx  2 root root 40 Jun 15 11:02 .\r\ndrwxrwxr-x 22 root root 4096 Jun 15 10:21 ..\r\n")
        elif cmd.startswith("cd"):
            pass
        elif cmd.startswith("id"):
            channel.sendall(b"uid=0(root) gid=0(root) groups=0(root)\r\n")
        elif cmd in ["nproc", "free -m"]:
            channel.sendall(b"              total        used        free\r\nMem:           1986        1234         752\r\n")
        elif cmd in ["systemctl status", "service ssh status"]:
            channel.sendall(b"* ssh.service - OpenBSD Secure Shell server\r\n   Active: active (running)\r\n")
        else:
            channel.sendall(b"bash: " + cmd.encode() + b": command not found\r\n")

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True


class SSHListener:
    def __init__(self, host="0.0.0.0", port=2222, on_event=None):
        self.host = host
        self.port = port
        self.on_event = on_event or (lambda *a, **k: None)
        self.server_socket = None
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass

    def _listen_loop(self):
        host_key = paramiko.RSAKey.generate(2048)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(50)
        logger.info(f"SSH honeypot listening on {self.host}:{self.port}")

        while self.running:
            try:
                client, addr = self.server_socket.accept()
                client.settimeout(10)
                threading.Thread(
                    target=self._handle_client,
                    args=(client, addr, host_key),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except OSError:
                break
            except Exception as e:
                logger.error(f"SSH accept error: {e}")
                continue

    def _handle_client(self, client, addr, host_key):
        try:
            transport = paramiko.Transport(client)
            transport.local_version = FAKE_BANNER
            transport.add_server_key(host_key)
            server = SSHServer(client, addr, self.on_event, None)
            transport.start_server(server=server)
            handshake_start = time.time()
            while time.time() - handshake_start < 15:
                if not transport.is_active():
                    break
                time.sleep(0.5)
            if transport.is_active():
                transport.close()
        except (paramiko.SSHException, EOFError, socket.error, OSError) as e:
            logger.debug(f"SSH client error for {addr}: {e}")
        except Exception as e:
            logger.error(f"Unexpected SSH client error: {e}")
        finally:
            try:
                client.close()
            except Exception:
                pass