# **Job Runner**

# Requirements
 - AWS Lambda: the function needs to be configured with at least 7GB of memory (when detecting clones, Oreo set the memory reserve of Java to [10GB](https://github.com/Mondego/oreo-artifact/blob/474e3a7d06b3ff75b8778ba75d99f0e551bd6ecc/oreo/clone-detector/runnodes.sh#L22)) and 15 minutes of timeout. SQS trigger needs to have a batch size of 1.
 - AWS ECR: create a repo named `update-helper` to store the image consumed by Lambda.
 - AWS EFS: without EFS, Lambda only has access to 512MB of write storage, which can be lacking. An EFS is needed to be mount to `/mnt/tmp` for the lambda function to run when deployed.
 - Docker
 - [AWS Lambda Runtime Interface Emulator](https://github.com/aws/aws-lambda-runtime-interface-emulator): for local running.
# Running
Besides the universal environment variables, add to `.env` file : 
```
AWS_LAMBDA_RUNTIME_API=python3.6 # For AWS Lambda RIE
SERVER_HOST=http://localhost:5000/ # If running `server` alongside `job-runner`
GITHUB_USERNAME # This and the next one is optional. GitHub API can be used without it but with a very limited number of request
GITHUB_TOKEN
```
This [article](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) have the instructions to create the GitHub token.

All of the commands here are run from the module root '/job-runner'
```
docker build -f ./Dockerfile -t myfunction:latest ../
docker run -v $PATH_TO_RIE:/aws-lambda -p 9000:8080 --env-file $PATH_TO_ENV --entrypoint /aws-lambda myfunction:latest /usr/local/bin/python -m awslambdaric main.lambda_handler
```
To send test requests:
```
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -d '{"Records": [{"body": {}}]}'
```
This can also be run as a standalone server similar to `server`.
# Deployment
After setting up AWS, deployment involves retrieving authentication token, tag image to upload, and push to ECR. AWS console should have the list of commands needed.
```
docker tag myfunction:latest ecr.url.amazonaws.com/update-helper:latest
docker push ecr.url.amazonaws.com/update-helper:latest
```
The environment variables need to be configured as well using the setting in [Running](#Running).
