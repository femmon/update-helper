# **Update Helper**
This is the back-end of the project Update Helper. It comprises 3 main modules:
- `data-preparation` which populates the database with project metrics beforehand
- `server` is a Flask web server that communicates directly with clients
- `job-runner` runs in the background to do the clone detection

There are also 2 common modules that are used in the main modules:
- `update-helper-database` manages database operations
- `update-helper-project-controller` is a wrapper around git commands and [Oreo](https://github.com/Mondego/oreo-artifact) operations
- `update-helper-semver` handles working with versions
# Dependencies
This project is designed to run on Linux, and it makes use of AWS services. This page only lists the common dependencies between modules.
The programs will access these services through the credential/configuration in the environment variables.

## Ubuntu 18.04
Ubuntu is used for this project development. Part of this project, [Oreo](https://github.com/Mondego/oreo-artifact), does require Linux to run.

AWS EC2 initially was used to host both the `server` and `job-runner`. The setup will be like this:
```
sudo apt update
sudo apt install python3.6-distutils
curl -O https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py --user
echo 'PATH="/home/ubuntu/.local/bin:$PATH"' > ~/.profile
python3 -m pip install --user pipenv==2021.5.29
sudo apt-get install openjdk-8-jdk ant # This is only required by `job-runner`
```

## MySQL 8.0
The database is used by every module. Schema detail is in `update-helper-database`.

## AWS S3
A bucket named `update-helper` is required for the following modules to work:
1. `data-preparation` use S3 to:
 - Write the preprocessed metric
 - Read the list of objects to determine where to continue with preprocessing
2. `job-runner` use S3 to:
 - Read and write metric

## AWS SQS
A queue named `update-helper_job` with a visibility timeout of 30 minutes is required for the following modules to work:
1. `server` use SQS to:
 - Write messages containing the initialization task of a job
2. `job-runner` use SQS to:
 - Read messages when running as its own server (like on AWS EC2)
 - Write job_component message

# Environment Variables
All modules need to have these to access MySQL:
 - `MYSQL_HOST`
 - `MYSQL_PORT`
 - `MYSQL_USER`
 - `MYSQL_PASSWORD`
 - `MYSQL_DATABASE`
 
And these to access AWS resources:
 - `AWS_ACCESS_KEY_ID`
 - `AWS_SECRET_ACCESS_KEY`

Depending on how the modules are run, these need to be specified in a `.env` at the module's root folder or in the relevant AWS configuration.
