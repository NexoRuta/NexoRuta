import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('gitlinks', Path(__file__).with_name('verify-gitlinks.py'))
gitlinks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gitlinks)


class CheckoutGitlinksTests(unittest.TestCase):
    def test_selected_checkout_is_authority_and_mismatch_is_not_rewritten(self):
        with tempfile.TemporaryDirectory(prefix='nexoruta-gitlinks-') as temporary:
            root = Path(temporary) / 'root'
            child = Path(temporary) / 'child'
            def git(where, *args):
                return subprocess.check_output(['git', '-C', str(where), *args], stderr=subprocess.DEVNULL, text=True).strip()
            for directory in (root, child):
                directory.mkdir()
                git(directory, 'init')
                git(directory, 'config', 'user.email', 'fixture@example.invalid')
                git(directory, 'config', 'user.name', 'Gitlink fixture')
                (directory / 'content.txt').write_text('initial', encoding='utf-8')
                git(directory, 'add', '.')
                git(directory, 'commit', '-m', 'initial')
            git(root, '-c', 'protocol.file.allow=always', 'submodule', 'add', str(child), 'module')
            git(root, 'commit', '-am', 'module')
            # A historical manifest must not override the selected checkout.
            manifest = root / 'scripts' / 'cloud' / 'checkpoint.json'
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"submodules":[{"path":"module","commit":"old-checkpoint"}]}', encoding='utf-8')
            self.assertEqual(1, gitlinks.verify(root))
            module = root / 'module'
            first = git(module, 'rev-parse', 'HEAD')
            git(module, 'config', 'user.email', 'fixture@example.invalid')
            git(module, 'config', 'user.name', 'Gitlink fixture')
            (module / 'content.txt').write_text('later', encoding='utf-8')
            git(module, 'commit', '-am', 'later')
            later = git(module, 'rev-parse', 'HEAD')
            with self.assertRaisesRegex(ValueError, 'does not match'):
                gitlinks.verify(root)
            self.assertEqual(later, git(module, 'rev-parse', 'HEAD'))
            self.assertNotEqual(first, later)
            git(root, 'add', 'module')
            git(root, 'commit', '-m', 'selected later checkout')
            self.assertEqual(1, gitlinks.verify(root))
            self.assertEqual('later', (module / 'content.txt').read_text(encoding='utf-8'))
            git(root, 'submodule', 'deinit', 'module')
            with self.assertRaisesRegex(ValueError, 'does not match|not initialized'):
                gitlinks.verify(root)


if __name__ == '__main__':
    unittest.main()
