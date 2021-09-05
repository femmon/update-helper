import os
import pexpect
import subprocess
import time


class OreoController:
    # mount_dir needs to end with '/'
    def __init__(self, mount_dir, init_java_parser=False):
        self.mount_dir = mount_dir
        self.oreo_script = mount_dir + 'oreo/python_scripts/'
        self.metric_output_path = self.oreo_script + '1_metric_output/'
        self.snippet_path = self.metric_output_path + 'mlcc_input.file'

        if init_java_parser:
            self.init_java_parser()

    def init_java_parser(self):
        pexpect.run(
            'ant metric',
            cwd=self.mount_dir + 'oreo/java-parser',
            timeout=None
        )

    def calculate_metric(self, source):
        retry = 0
        subprocess.Popen(
            ['python3', 'metricCalculationWorkManager.py', '1', 'd', source],
            cwd = self.oreo_script
        )

        while True:
            time.sleep(10)
            with open(self.oreo_script + 'metric.out') as f:
                # For situation where the file is empty
                line = ''

                for line in f:
                    pass
                if line == 'done!\n':
                    break
                else:
                    target_command = f'java -jar ../java-parser/dist/metricCalculator.jar {self.oreo_script}output/1.txt dir'
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
                            cwd = self.oreo_script
                        )

    def clean_up_metric(self):
        # There might be no output folder
        try:
            for name in os.listdir(self.metric_output_path):
                os.remove(f'{self.metric_output_path}{name}')
        except FileNotFoundError:
            pass
