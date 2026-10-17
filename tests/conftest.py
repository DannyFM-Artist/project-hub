import os
import socket
import sys
from pathlib import Path

import pytest

REAL_DEFAULT = Path.home() / "project-hub-data"  # captured before any test patches HOME
_REAL = os.path.normcase(str(REAL_DEFAULT)) + os.sep
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
_real_writes = []


def _is_real(path):
    if isinstance(path, (str, os.PathLike)):
        full = os.path.normcase(os.path.abspath(os.fspath(path)))
        return full == _REAL[:-1] or full.startswith(_REAL)
    return False  # a file descriptor or bytes path


def _touches_real(event, args):
    """True when an audit event from this process writes, creates, moves or deletes something in the real data folder."""
    if event == "open":
        path, mode, flags = args
        writes = any(c in mode for c in "wax+") if mode else bool((flags or 0) & _WRITE_FLAGS)
        return writes and _is_real(path)
    if event == "os.rename":
        return _is_real(args[0]) or _is_real(args[1])
    if event in ("os.remove", "os.mkdir", "os.rmdir", "os.truncate", "shutil.rmtree"):
        return _is_real(args[0])
    return False


def _audit(event, args):
    if _touches_real(event, args):
        _real_writes.append((event, str(args[0])))


def _socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
    """socket.socketpair on Windows connects two loopback sockets and waits in accept() with no timeout. On this
    laptop a loopback handshake is sometimes dropped under load, and every new asyncio event loop then hangs the
    suite for good. Same pairing, with a timeout and a retry."""
    for _ in range(5):
        with socket.socket(family, type, proto) as lsock:
            lsock.bind(("127.0.0.1", 0))
            lsock.listen()
            lsock.settimeout(5)
            csock = socket.socket(family, type, proto)
            csock.settimeout(5)
            try:
                csock.connect(lsock.getsockname())
                ssock, _ = lsock.accept()
            except OSError:
                csock.close()
                continue
        if ssock.getpeername() != csock.getsockname():  # same check as the stdlib: the peer must be our own socket
            ssock.close(); csock.close()
            continue
        ssock.settimeout(None); csock.settimeout(None)
        return ssock, csock
    raise OSError("socketpair: the loopback connection failed 5 times")


if sys.platform == "win32":
    socket.socketpair = _socketpair


@pytest.fixture(scope="session", autouse=True)
def real_data_folder_untouched():
    """Fail the run if a test wrote to the real ~/project-hub-data. Only this process's own writes count
    (via an audit hook), so other Claude sessions and the tray dashboard writing there meanwhile are fine.
    shortcut: subprocesses are not audited; they inherit the temporary PROJECT_HUB_DATA from isolated_data_folder."""
    sys.addaudithook(_audit)  # hooks cannot be removed; it only appends to a list
    yield
    assert not _real_writes, f"a test touched the real data folder {REAL_DEFAULT}: {_real_writes[:5]}"


@pytest.fixture(autouse=True)
def isolated_data_folder(tmp_path, monkeypatch):
    """Every test (and every subprocess that inherits os.environ) uses a temporary data folder and home."""
    monkeypatch.setenv("PROJECT_HUB_DATA", str(tmp_path / "hub-data"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))


@pytest.fixture(autouse=True)
def no_real_quit_dialog(monkeypatch):
    """The real Salir dialog would pop up on Danny's desktop: a test must pass its own confirm."""
    from project_hub import tray

    def refuse():
        raise AssertionError("a test reached the real tray quit dialog; pass confirm= to quit_app")
    monkeypatch.setattr(tray, "confirm_quit", refuse)
