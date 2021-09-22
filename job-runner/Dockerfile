ARG CONTEXT_JOB_DIR="./job-runner"

ARG FUNCTION_DIR="/function"
ARG FUNCTION_SOURCE_DIR="/update-helper"
ARG JOB_SOURCE_DIR="${FUNCTION_SOURCE_DIR}/job-runner"


FROM python:3.6.15-buster AS build-image

ARG CONTEXT_JOB_DIR
ARG FUNCTION_DIR
ARG FUNCTION_SOURCE_DIR
ARG JOB_SOURCE_DIR

# Install aws-lambda-cpp build dependencies
RUN apt-get update && \
  apt-get install -y \
    g++ \
    make \
    cmake \
    unzip \
    libcurl4-openssl-dev

# Install lambda dependencies
RUN mkdir -p ${FUNCTION_DIR}
RUN pip install --target ${FUNCTION_DIR} awslambdaric

# Copy requirements
RUN mkdir -p ${JOB_SOURCE_DIR}
COPY ${CONTEXT_JOB_DIR}/Pipfile ${CONTEXT_JOB_DIR}/Pipfile.lock ${JOB_SOURCE_DIR}
COPY ./lib ${FUNCTION_SOURCE_DIR}/lib

RUN pip install pipenv==2021.5.29

WORKDIR ${JOB_SOURCE_DIR}
RUN pipenv lock -r | sed 's/-e //g' | pip install -r /dev/stdin --target ${FUNCTION_DIR}

COPY ${CONTEXT_JOB_DIR} ${JOB_SOURCE_DIR}
RUN cp -r ${JOB_SOURCE_DIR}/. ${FUNCTION_DIR}


FROM python:3.6.15-buster AS final-image

ARG FUNCTION_DIR

RUN mkdir -p ${FUNCTION_DIR}
WORKDIR ${FUNCTION_DIR}

# Install Oreo dependencies
RUN wget -qO - https://adoptopenjdk.jfrog.io/adoptopenjdk/api/gpg/key/public | apt-key add - && \
  apt-get update && \
  apt-get install -y software-properties-common && \
  add-apt-repository --yes https://adoptopenjdk.jfrog.io/adoptopenjdk/deb/ && \
  apt-get update && \
  apt-get install -y \
    adoptopenjdk-8-hotspot \
    ant
ENV JAVA_HOME=/usr/lib/jvm/adoptopenjdk-8-hotspot-amd64

# Copy in the built dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}
ENV PYTHONPATH=${FUNCTION_DIR}:$PYTHONPATH

ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "main.lambda_handler" ]
