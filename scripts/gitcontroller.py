from pathlib import Path
import pexpect

class GitController:
    def __init__(self, mount_dir, repo):
        self.mount_dir = mount_dir
        self.repo = repo

        Path(self.mount_dir).mkdir(parents=True)
        self.clone()

    def clone(self):
        clone_output = pexpect.run(
            f'git clone {self.repo} .',
            # Enter credential when asked. This should stop the clone because of unauthorization
            events={
                "Username for 'https://github.com':": "Username\n",
                "Password for 'https://Username@github.com':": "Password\n"
            },
            cwd=self.mount_dir,
            timeout=None
        ).decode()
        last_output_line = self.pexpect_output_last_line(clone_output)

        if last_output_line.startswith('fatal:'):
            raise RuntimeError(f'Can\'t clone {self.repo} ("{last_output_line}")')
        elif last_output_line.endswith('done.'):
            # Success
            pass
        else:
            raise RuntimeError(f'Can\'t clone {self.repo} for unknown reason ("{last_output_line}")')

    def pexpect_output_last_line(self, pexpect_output):
        pexpect_output = [line for line in pexpect_output.split('\r\n') if line != '']
        return pexpect_output[-1]
