from pathlib import Path
import datetime
import json
import os
import shutil
import subprocess

out = Path('/home/leonpano/amng-out/rmerlin-integration-20260916')
out.mkdir(exist_ok=False)
source = Path('/home/leonpano/amng-out/rmerlin-audit-20260916/review.git')
repo = out / 'integration.git'
env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
subprocess.run(['git', 'clone', '--bare', '--shared', str(source), str(repo)], env=env, check=True)
shutil.copy2(source / 'shallow', repo / 'shallow')
def git(*args):
    return subprocess.check_output(['git', '--git-dir=' + str(repo), *args], env=env).decode().strip()
ours = '15ee3e5f0cf462e2d54a6c7b23117d9936263e59'
upstream = '96831be75b3b891f6aa4c608f00cc7bb2d499d67'
git('update-ref', 'refs/remotes/rmerlin/main', upstream)
git('update-ref', 'refs/heads/gt-be98-102.9-integration', ours)
git('remote', 'add', 'rmerlin', 'https://github.com/RMerl/asuswrt-merlin.ng.git')
git('remote', 'add', 'fork', 'https://github.com/leonpano2006/asuswrt-merlin.ng-gt-be98.git')
with (out / 'merge-tree.txt').open('w') as log:
    result = subprocess.run(['git', '--git-dir=' + str(repo), 'merge-tree', '--write-tree', ours, upstream],
                            env=env, stdout=log, stderr=subprocess.STDOUT)
assert result.returncode in (0, 1), (out / 'merge-tree.txt').read_text()[-6000:]
lines = (out / 'merge-tree.txt').read_text().splitlines()
tree = lines[0]
assert len(tree) == 40, lines[:5]
record = {'created_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'ours': ours, 'upstream': upstream, 'base': git('merge-base', ours, upstream),
          'initial_merge_tree': tree, 'conflicts': result.returncode == 1,
          'original_worktree_modified': False, 'router_modified': False}
(out / 'preparation.json').write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
print('\n'.join(lines[1:])[:22000])
