import os
import re
import shutil
import subprocess
import time


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

        if init_java_parser:
            self.init_java_parser()

    def init_java_parser(self):
        subprocess.run(
            ['ant', 'metric'],
            cwd=self.mount_dir + 'oreo/java-parser',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
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
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            clone_controller = subprocess.Popen(
                ['python', 'controller.py', '1'],
                stdout=subprocess.PIPE,
                cwd=self.clone_detector_path
            )

            subprocess.run(
                ['./runPredictor.sh'],
                cwd=self.python_scripts_path,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # TODO: starting sending out result while it's running: https://github.com/dabeaz/generators/blob/master/examples/follow.py
            output, e = clone_controller.communicate()
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
