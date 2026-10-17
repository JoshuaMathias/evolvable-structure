"""The public-repository hygiene scan."""
import subprocess

import pytest

from esoi import hygiene


def texts(text):
    return [f.pattern for f in hygiene.scan_text(text)]


def test_real_looking_secrets_are_found_and_redacted():
    key = "sk-ant-" + "a1b2c3d4e5f6a7b8"
    found = hygiene.scan_text(f"token = {key}")
    assert [f.pattern for f in found] == ["anthropic-key"] and key not in str(found[0])
    assert texts("AKIA" + "ABCDEFGHIJKLMNOP") == ["aws-key"]
    assert texts("ghp_" + "a" * 36) == ["github-token"]
    assert texts("Authorization: Bearer " + "x" * 30) == ["bearer-token"]
    assert texts("id " + "0123456789abcdef" + "01234567") == ["object-id"]
    assert texts("see /home" + "/realperson/project/x.py") == ["machine-path"]
    assert texts("write to person" + "@company-name.org") == ["email"]


def test_placeholders_are_not_findings():
    assert texts("sk-ant-... and /home/user/x and name@example.org and 000000000000000000000000") == []
    assert texts("security@somewhere.org, noreply@somewhere.org") == []
    assert texts("commit 61d93e6e4eb09ae926b23ee704c91912cefbc331") == []
    assert texts("snake_case_identifier_that_is_quite_long_indeed_yes") == []


def test_allowances_extend_the_placeholders():
    allow = hygiene.Allowances(email_domains=["corp.test"], users=["ci"], mailboxes=["team"])
    assert hygiene.scan_text("a" + "@corp.test /home" + "/ci/x team" + "@other.org", allow=allow) == []


def test_a_private_key_block_with_a_body_is_found():
    body = "A" * 80
    assert texts(f"-----BEGIN RSA PRIVATE KEY-----\n{body}\n-----END RSA PRIVATE KEY-----") == ["private-key"]
    assert texts("-----BEGIN RSA PRIVATE KEY-----\nstub\n-----END RSA PRIVATE KEY-----") == []


def git(root, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args], cwd=root, check=True, capture_output=True)


def test_scan_repo_staged_exclude_and_history(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "clean.txt").write_text("fine\n")
    (tmp_path / "leak.txt").write_text("path /home" + "/realperson/x\n")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "init")
    assert [f.path for f in hygiene.scan_repo(tmp_path)] == ["leak.txt"]
    assert hygiene.scan_repo(tmp_path, allow=hygiene.Allowances(exclude=["leak"])) == []
    (tmp_path / "leak.txt").write_text("gone\n")
    git(tmp_path, "commit", "-q", "-am", "remove")
    assert hygiene.scan_repo(tmp_path) == []
    assert any(f.pattern == "machine-path" for f in hygiene.scan_history(tmp_path))
    (tmp_path / "new.txt").write_text("a" + "@b-company.org\n")
    git(tmp_path, "add", "new.txt")
    assert [f.path for f in hygiene.scan_repo(tmp_path, staged=True)] == ["new.txt"]


def test_run_cli_exit_codes(tmp_path):
    git(tmp_path, "init", "-q")
    (tmp_path / "a.txt").write_text("fine\n")
    git(tmp_path, "add", "-A")
    lines = []
    assert hygiene.run_cli(tmp_path, False, False, hygiene.Allowances(), lines.append) == 0 and lines[-1] == "hygiene scan: clean"
    (tmp_path / "b.txt").write_text("/home" + "/realperson/x\n")
    assert hygiene.run_cli(tmp_path, False, False, hygiene.Allowances(), lines.append) == 1


def test_a_repository_names_its_own_secret_shapes(tmp_path):
    secret = "acme_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3"
    own = hygiene.allowances_from({"patterns": {"acme-key": "acme_[A-Za-z0-9]{20,}"}})
    found = hygiene.scan_text(f"key = {secret}", allow=own)
    assert [f.pattern for f in found] == ["acme-key"]   # named once, not also as the generic api-key
    assert [f.pattern for f in hygiene.scan_text(f"key = {secret}")] == ["api-key"]
    assert hygiene.scan_text("acme_ is a prefix", allow=own) == []
    with pytest.raises(hygiene.HygieneError, match="acme"):
        hygiene.allowances_from({"patterns": {"acme": "("}})


def test_outside_git_the_folder_is_walked_and_staged_or_history_say_why(tmp_path):
    (tmp_path / "leak.txt").write_text("/home" + "/realperson/x\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "skipped.txt").write_text("/home" + "/realperson/y\n")
    assert [f.path for f in hygiene.scan_repo(tmp_path)] == ["leak.txt"]
    lines = []
    assert hygiene.run_cli(tmp_path, False, False, hygiene.Allowances(), lines.append) == 1
    assert hygiene.run_cli(tmp_path, True, False, hygiene.Allowances(), lines.append) == 2 and "not a git checkout" in lines[-1]
    assert hygiene.run_cli(tmp_path, False, True, hygiene.Allowances(), lines.append) == 2 and "--history" in lines[-1]
