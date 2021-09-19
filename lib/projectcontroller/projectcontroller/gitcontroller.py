import glob
import hashlib
from pathlib import Path
import shutil
import subprocess


class GitController:
    def __init__(self, mount_dir, repo, cloned=False):
        self.mount_dir = mount_dir
        # To make sure gather_java() extracts the right relative_file_path
        if self.mount_dir[-1] != '/':
            self.mount_dir = self.mount_dir + '/'
        self.repo = repo

        if not cloned:
            Path(self.mount_dir).mkdir(parents=True)
            self.clone()

    def clone(self):
        if not self.repo.startswith('https://github.com/'):
            raise RuntimeError(f'Can\'t clone {self.repo}: Only support Github at the moment')

        # Credential is only consumed when asked. This should stop clones that require unauthorization
        source_with_dummy_cred = self.repo.replace('https://github.com/', 'https://Username:Password@github.com/')
        clone_process = subprocess.Popen(
            ['git', 'clone', '--progress', source_with_dummy_cred, '.'],
            cwd=self.mount_dir,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE
        )
        clone_output = []
        for line in clone_process.stdout:
            clone_output.append(line.decode().rstrip())
        last_output_line = clone_output[-1]
        status = clone_process.wait()

        # Can't really trust the clone_output
        if status != 0:
            raise RuntimeError(f'Can\'t clone {self.repo} ("{last_output_line}")')

    def checkout(self, version, commit=False):
        print('Checking out ' + version)
        checkout_process = subprocess.Popen(
            ['git', 'checkout', f'{"" if commit else "tags/"}{version}'],
            cwd=self.mount_dir,
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL
        )
        status = checkout_process.wait()

        if status != 0:
            if commit:
                return False

            version = 'v' + version
            checkout_process = subprocess.Popen(
                ['git', 'checkout', f'tags/{version}'],
                cwd=self.mount_dir,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL
            )
            status = checkout_process.wait()

            if status != 0:
                return False

        return True

    def gather_java(self, des_folders):
        des_folders_iter = iter(des_folders)
        des_folder = next(des_folders_iter)
        Path(des_folder).mkdir(parents=True)

        file_dict = {}

        files = glob.glob(self.mount_dir + '/**/*.java', recursive=True)
        for raw_path in files:
            relative_file_path = raw_path[len(self.mount_dir):]
            new_file_name = hashlib.sha224(relative_file_path.encode()).hexdigest() + '.java'
            new_file_path = des_folder + '/' + new_file_name
            try:
                shutil.copy(raw_path, new_file_path)
            except OSError as e:
                if str(e) == f"[Errno 27] File too large: '{new_file_path}'":
                    des_folder = next(des_folders_iter)
                    Path(des_folder).mkdir(parents=True)
                    new_file_path = des_folder + '/' + new_file_name
                    shutil.copy(raw_path, new_file_path)
                else:
                    raise(e)
            file_dict[relative_file_path] = new_file_name

        return file_dict
