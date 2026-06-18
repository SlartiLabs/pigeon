"""Pointer resolution across supported schemes."""

from __future__ import annotations

import pytest

from pigeon import manifest
from pigeon import resolve as rs


def test_repo_pointer(repo):
    r = rs.resolve("repo://AGENTS.md", repo)
    assert r.scheme == "repo"
    assert "canonical" in r.read_text()


def test_bare_path(repo):
    assert rs.resolve("AGENTS.md", repo).read_text().startswith("# AGENTS.md")


def test_file_url(repo):
    abs_path = (repo.root / "AGENTS.md").resolve()
    r = rs.resolve(f"file://{abs_path}", repo)
    assert r.scheme == "file"
    assert r.exists()


def test_manifest_head(repo):
    manifest.write_manifest(repo)
    r = rs.resolve("manifest@HEAD", repo)
    assert r.scheme == "manifest"
    assert r.path == repo.manifest
    assert "manifest_version" in r.read_text()


def test_unknown_scheme_rejected(repo):
    with pytest.raises(rs.PointerError):
        rs.resolve("ftp://example.com/x", repo)


def test_missing_file_raises(repo):
    r = rs.resolve("repo://does/not/exist.txt", repo)
    assert not r.exists()
    with pytest.raises(FileNotFoundError):
        r.read_bytes()


def test_s3_disabled_by_default(repo):
    with pytest.raises(rs.PointerError) as exc:
        rs.resolve("s3://bucket/key", repo)
    assert "allow_s3" in str(exc.value)


def test_manifest_rev_charset_validated(repo):
    from pigeon import resolve
    with pytest.raises(resolve.PointerError, match="charset"):
        resolve.resolve("manifest@--upload-pack=evil", repo)
    with pytest.raises(resolve.PointerError, match="charset"):
        resolve.resolve("manifest@-rf", repo)


# --- S1: pointer resolution is confined to the repo root --------------------
def test_repo_pointer_cannot_escape_root(repo):
    # A handoff carrying repo://../../etc/passwd must NOT read outside the repo.
    with pytest.raises(rs.PointerError, match="outside the repo root"):
        rs.resolve("repo://../../etc/passwd", repo)


def test_bare_absolute_path_confined(repo):
    # A bare absolute path landing outside the repo is rejected by default.
    with pytest.raises(rs.PointerError, match="outside the repo root"):
        rs.resolve("/etc/passwd", repo)


def test_file_url_outside_root_rejected_by_default(repo, tmp_path):
    outside = tmp_path.parent / "outside_file.txt"
    outside.write_text("secret", encoding="utf-8")
    with pytest.raises(rs.PointerError, match="outside the repo root"):
        rs.resolve(f"file://{outside.resolve()}", repo)


def test_allow_outside_root_lifts_absolute_schemes_but_never_repo(repo, tmp_path):
    outside = tmp_path.parent / "outside_ok.txt"
    outside.write_text("hello", encoding="utf-8")
    repo.data["resolve"]["allow_outside_root"] = True
    # the opt-in lifts the fence for file:// (an absolute scheme)...
    assert rs.resolve(f"file://{outside.resolve()}", repo).read_text() == "hello"
    # ...but repo:// is never lifted — it means "in the repo".
    with pytest.raises(rs.PointerError, match="outside the repo root"):
        rs.resolve("repo://../../etc/passwd", repo)


# --------------------------------------------------- coverage: fence/error branches

def test_empty_pointer_rejected(repo):
    with pytest.raises(rs.PointerError, match="non-empty string"):
        rs.resolve("", repo)


def test_resolved_data_branch_and_no_content():
    r = rs.Resolved(pointer="x", scheme="s3", data=b"hi")
    assert r.exists() is True
    assert r.read_bytes() == b"hi"
    assert r.read_text() == "hi"
    empty = rs.Resolved(pointer="x", scheme="s3")  # neither path nor data
    assert empty.exists() is False
    with pytest.raises(rs.PointerError, match="no resolvable content"):
        empty.read_bytes()


def test_resolve_text_convenience(repo):
    assert rs.resolve_text("repo://AGENTS.md", repo).startswith("# AGENTS.md")


def _git(root, *args):
    import subprocess
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _git_repo_with_manifest(repo):
    manifest.write_manifest(repo)
    for cmd in (("init", "-q"), ("config", "user.email", "t@t"),
                ("config", "user.name", "t"), ("add", "-A"),
                ("commit", "-q", "-m", "snapshot")):
        _git(repo.root, *cmd)


def test_manifest_rev_reads_from_git(repo):
    _git_repo_with_manifest(repo)
    import subprocess
    rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo.root,
                         capture_output=True, text=True, check=True).stdout.strip()
    r = rs.resolve(f"manifest@{rev}", repo)        # != "HEAD" -> git-show branch
    assert r.scheme == "manifest" and r.data is not None
    assert b'"' in r.read_bytes()                  # the committed manifest JSON


def test_manifest_bad_rev_raises(repo):
    _git_repo_with_manifest(repo)
    with pytest.raises(rs.PointerError):
        rs.resolve("manifest@deadbeefcafe", repo)  # nonexistent rev -> git fails


def test_s3_reads_via_mocked_client(repo, monkeypatch):
    repo.data["resolve"]["allow_s3"] = True

    class _Body:
        def read(self):
            return b"s3-bytes"

    class _Client:
        def get_object(self, Bucket, Key):
            assert Bucket == "my-bucket" and Key == "a/b.txt"
            return {"Body": _Body()}

    import boto3
    monkeypatch.setattr(boto3, "client", lambda svc: _Client())
    r = rs.resolve("s3://my-bucket/a/b.txt", repo)
    assert r.scheme == "s3" and r.read_bytes() == b"s3-bytes"
