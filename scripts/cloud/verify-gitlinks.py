from pathlib import Path
import subprocess
import sys


def verify(root):
    """Check selected checkout gitlinks without selecting or rewriting sources."""
    records = subprocess.check_output(
        ['git', '-C', str(root), 'ls-tree', '-rz', 'HEAD'])
    count = 0
    for record in records.split(b'\0'):
        if not record:
            continue
        metadata, path = record.split(b'\t', 1)
        mode, _, expected = metadata.split()
        if mode != b'160000':
            continue
        module = root / path.decode('utf-8')
        try:
            actual_root = Path(subprocess.check_output(
                ['git', '-C', str(module), 'rev-parse', '--show-toplevel'],
                stderr=subprocess.DEVNULL, text=True).strip()).resolve()
            actual = subprocess.check_output(
                ['git', '-C', str(module), 'rev-parse', 'HEAD'], text=True).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ValueError(f'{module.name}: submodule is not initialized') from None
        if actual_root != module.resolve() or actual != expected.decode('ascii'):
            raise ValueError(f'{module.name}: checkout does not match the selected HEAD gitlink')
        count += 1 + verify(module)
    return count


if __name__ == '__main__':
    try:
        print(f'Checked {verify(Path(__file__).resolve().parents[2])} checkout gitlinks; sources unchanged.')
    except (ValueError, subprocess.CalledProcessError) as error:
        print(f'{error}. Initialize/select submodules explicitly with '
              'git submodule update --init --recursive after preserving local work.', file=sys.stderr)
        sys.exit(1)
