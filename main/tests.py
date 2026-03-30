import shutil
import subprocess
import tempfile
import unittest
import importlib
import sys
import types
from pathlib import Path
from unittest import mock

from main.utils.helpers import exec_commands


class PullGitChangesReproTests(unittest.TestCase):
    def _git(self, cwd, *args):
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _set_up_repo_with_branch_created_after_clone(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        base_dir = Path(temp_dir.name)
        source_dir = base_dir / "source"
        remote_dir = base_dir / "remote.git"
        default_clone_dir = base_dir / "default-clone"
        deploy_clone_dir = base_dir / "deploy-clone"
        branch_name = "feature/new-branch"

        source_dir.mkdir()
        self._git(source_dir, "init")
        self._git(source_dir, "config", "user.name", "Test User")
        self._git(source_dir, "config", "user.email", "test@example.com")

        readme_path = source_dir / "README.md"
        readme_path.write_text("main branch\n", encoding="utf-8")
        self._git(source_dir, "add", "README.md")
        self._git(source_dir, "commit", "-m", "Initial commit")
        self._git(source_dir, "branch", "-M", "main")

        self._git(base_dir, "clone", "--bare", str(source_dir), str(remote_dir))
        self._git(source_dir, "remote", "add", "origin", str(remote_dir))
        self._git(source_dir, "push", "-u", "origin", "main")

        self._git(base_dir, "clone", str(remote_dir), str(default_clone_dir))

        self._git(source_dir, "checkout", "-b", branch_name)
        readme_path.write_text("feature branch\n", encoding="utf-8")
        self._git(source_dir, "commit", "-am", "Feature commit")
        self._git(source_dir, "push", "-u", "origin", branch_name)

        shutil.copytree(default_clone_dir, deploy_clone_dir)
        return remote_dir, deploy_clone_dir, branch_name

    def _load_services_module(self):
        fake_celery = types.ModuleType("celery")

        def shared_task(*args, **kwargs):
            if args and callable(args[0]) and len(args) == 1 and not kwargs:
                return args[0]

            def decorator(func):
                return func

            return decorator

        fake_celery.shared_task = shared_task

        fake_django_conf = types.ModuleType("django.conf")
        fake_django_conf.settings = types.SimpleNamespace(
            STAGING_CONF={
                "DEPLOYMENT_DOCKER_NETWORK": None,
            }
        )

        with mock.patch.dict(
            sys.modules,
            {
                "celery": fake_celery,
                "django.conf": fake_django_conf,
            },
        ):
            sys.modules.pop("main.services", None)
            services = importlib.import_module("main.services")

        self.addCleanup(lambda: sys.modules.pop("main.services", None))
        return services

    def test_pull_then_checkout_fails_for_branch_created_after_default_clone(self):
        remote_dir, deploy_clone_dir, branch_name = self._set_up_repo_with_branch_created_after_clone()

        status, err = exec_commands(
            commands=[
                ["git", "pull", str(remote_dir)],
                ["git", "checkout", branch_name],
            ],
            cwd=str(deploy_clone_dir),
            logger="",
            logger_not_file=True,
            err=f"Error while pulling latest changes from branch {branch_name}",
            print_stderr=True,
        )

        self.assertFalse(status)
        self.assertIn(
            f"pathspec '{branch_name}' did not match any file(s) known to git",
            err,
        )

    def test_pull_git_changes_updates_branch_created_after_default_clone(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)

        base_dir = Path(temp_dir.name)
        source_dir = base_dir / "source"
        remote_dir = base_dir / "remote.git"
        clone_root = base_dir / "clones"
        log_root = base_dir / "logs"
        branch_name = "feature/new-branch"
        repo_name = "demo-repo"
        url = "https://example.test/org/demo-repo.git"
        user_name = "user"
        token = "token"
        translated_clone_url = f"https://{user_name}:{token}@example.test/org/demo-repo.git"

        source_dir.mkdir()
        self._git(source_dir, "init")
        self._git(source_dir, "config", "user.name", "Test User")
        self._git(source_dir, "config", "user.email", "test@example.com")

        readme_path = source_dir / "README.md"
        readme_path.write_text("main branch\n", encoding="utf-8")
        self._git(source_dir, "add", "README.md")
        self._git(source_dir, "commit", "-m", "Initial commit")
        self._git(source_dir, "branch", "-M", "main")

        self._git(base_dir, "clone", "--bare", str(source_dir), str(remote_dir))
        self._git(source_dir, "remote", "add", "origin", str(remote_dir))
        self._git(source_dir, "push", "-u", "origin", "main")

        services = self._load_services_module()
        original_exec_commands = services.exec_commands

        def translated_exec_commands(commands, **kwargs):
            updated_commands = []
            for command in commands:
                updated_commands.append(
                    [str(remote_dir) if arg == translated_clone_url else arg for arg in command]
                )
            return original_exec_commands(updated_commands, **kwargs)

        with mock.patch.object(services, "exec_commands", side_effect=translated_exec_commands):
            status, result = services.pull_git_changes(
                url=url,
                user_name=user_name,
                token=token,
                org_name="demo-org",
                repo_name=repo_name,
                branch_name=None,
                clone_path=str(clone_root),
                log_file_path=str(log_root),
            )

            self.assertTrue(status, result)

            self._git(source_dir, "checkout", "-b", branch_name)
            readme_path.write_text("feature branch\n", encoding="utf-8")
            self._git(source_dir, "commit", "-am", "Feature commit")
            self._git(source_dir, "push", "-u", "origin", branch_name)

            status, result = services.pull_git_changes(
                url=url,
                user_name=user_name,
                token=token,
                org_name="demo-org",
                repo_name=repo_name,
                branch_name=branch_name,
                clone_path=str(clone_root),
                log_file_path=str(log_root),
            )

        self.assertTrue(status, result)
        self.assertEqual(
            (
                clone_root / branch_name / repo_name / "README.md"
            ).read_text(encoding="utf-8"),
            "feature branch\n",
        )
