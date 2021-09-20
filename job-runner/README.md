# **Job Runner**

# Requirements
 - AWS Lambda: the function needs to be configured with 2560 MB of memory and 15 minutes of timeout. SQS trigger needs to have a batch size of 2.
 - AWS ECR: create a repo named `update-helper` to store the image consumed by Lambda.
 - Docker
 - [AWS Lambda Runtime Interface Emulator](https://github.com/aws/aws-lambda-runtime-interface-emulator): for local running.
# Running
Besides the universal environment variables, add to `.env` file : 
```
JAVA_HOME=/user/bin # For Oreo
AWS_LAMBDA_RUNTIME_API=python3.6 # For AWS Lambda RIE
SERVER_HOST=http://localhost:5000/ # If running `server` alongside `job-runner`
```
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
