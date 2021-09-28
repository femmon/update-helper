import os
import re
import shutil
import subprocess
import time
import sys


VERBOSE = True


class OreoController:
    # mount_dir needs to end with '/'
    def __init__(self, mount_dir, init_java_parser=False):
        self.mount_dir = mount_dir
        self.python_scripts_path = mount_dir + 'oreo/python_scripts/'
        self.metric_output_path = self.python_scripts_path + '1_metric_output/'
        self.snippet_path = self.metric_output_path + 'mlcc_input.file'
        self.clone_detector_path = self.mount_dir + 'oreo/clone-detector/'
        self.clone_detector_input_path = self.clone_detector_path + 'input/dataset/'
        self.clone_result_path = self.mount_dir + 'oreo/results/predictions/'

        self.patch_cache_location()
        if init_java_parser:
            self.init_java_parser()

    # The default location is in Lambda read-only storage
    def patch_cache_location(self):
        with open(self.clone_detector_path + 'runnodes.sh', 'r+') as f:
            old_script = f.read()
            new_script = old_script.replace('java', f'java -Deproperties.cache.root="{self.mount_dir}.eproperties/cache/"')
            f.seek(0)
            f.write(new_script)

    def init_java_parser(self):
        subprocess.run(
            ['ant', 'metric'],
            cwd=self.mount_dir + 'oreo/java-parser',
            stdout=sys.stdout if VERBOSE else subprocess.DEVNULL,
            stderr=sys.stdout if VERBOSE else subprocess.DEVNULL
        )

    def calculate_metric(self, source):
        retry = 0
        subprocess.Popen(
            ['python3', 'metricCalculationWorkManager.py', '1', 'd', source],
            cwd = self.python_scripts_path
        )

        while True:
            time.sleep(10)
            with open(self.python_scripts_path + 'metric.out') as f:
                # For situation where the file is empty
                line = ''

                for line in f:
                    pass
                if line == 'done!\n':
                    break
                else:
                    target_command = f'java -jar ../java-parser/dist/metricCalculator.jar {self.python_scripts_path}output/1.txt dir'
                    ps = subprocess.run(['ps', '-e', '-o', 'command'], stdout = subprocess.PIPE)
                    running_processes = ps.stdout.decode().split('\n')
                    if target_command in running_processes:
                        pass
                    elif retry == 3:
                        error_message = 'Metric calculation has stopped unexpectedly'
                        raise RuntimeError(error_message)
                    else:
                        retry +=1
                        print('Retrying metric calculation')
                        subprocess.Popen(
                            ['python3', 'metricCalculationWorkManager.py', '1', 'd', source],
                            cwd = self.python_scripts_path
                        )
        
        OreoController.check_clone_input(self.snippet_path)

    def clean_up_metric(self):
        # There might be no output folder
        try:
            for name in os.listdir(self.metric_output_path):
                os.remove(f'{self.metric_output_path}{name}')
        except FileNotFoundError:
            pass

    def detect_clone(self, input):
        shutil.rmtree(self.clone_detector_input_path)
        os.makedirs(os.path.dirname(self.clone_detector_input_path), exist_ok=True)
        shutil.copy(input, self.clone_detector_input_path + 'blocks.file')
        print('Loaded input into detector')

        # Old results might interfere with the current run
        shutil.rmtree(self.clone_result_path, ignore_errors=True)

        try:
            subprocess.run(
                ['./cleanup.sh'],
                cwd=self.clone_detector_path,
                stdout=sys.stdout if VERBOSE else subprocess.DEVNULL,
                stderr=sys.stdout if VERBOSE else subprocess.DEVNULL
            )
            
            clone_controller = subprocess.Popen(
                ['python', 'controller.py', '1'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.clone_detector_path
            )

            subprocess.run(
                ['./runPredictor.sh'],
                cwd=self.python_scripts_path,
                stdout=sys.stdout if VERBOSE else subprocess.DEVNULL,
                stderr=sys.stdout if VERBOSE else subprocess.DEVNULL
            )

            # TODO: starting sending out result while it's running: https://github.com/dabeaz/generators/blob/master/examples/follow.py
            output, e = clone_controller.communicate()
            if VERBOSE:
                print(output)
                print(e)
            output = [line for line in output.decode().split('\n') if line != '']
            if output[-1] != 'SUCCESS: Search Completed on all nodes':
                raise RuntimeError()
        except Exception as e:
            # Ctrl + C kills everything but exception doesn't stop Popen nor runPredictor children
            ps = subprocess.run(['ps', '-e', '-o', 'pid,command'], stdout = subprocess.PIPE)
            running_processes = ps.stdout.decode().split('\n')
            p = re.compile('^\s*(\d+) python (controller.py 1|Predictor.py \d+)$')
            for process in running_processes:
                m = p.match(process)
                if m:
                    pid = m.group(1)
                    subprocess.run(['kill', '-9', pid])

            raise e

    @staticmethod
    def check_clone_input(input_path):
        total = 0
        count = 0
        with open(input_path) as f:
            for line in f:
                total += 1
                if len(line.split('@#@')[0].split(',')) < 6:
                    count += 1
                    if count < 3:
                        print(line)
        print(f'{count} broken out of {total}')
