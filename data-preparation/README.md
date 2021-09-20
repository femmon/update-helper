# **Data Preparation**

# Requirements
- Linus OS (this project is developed with Ubuntu 18.04, oreo is tested with CentOS)
- Python 3.6 (oreo requirement)
- Java 8 (oreo requirement). Please make sure `java` and `ant` using the correct version by having the appropriate value for `PATH` and `JAVA_HOME` environment variables
# Installing
All of the commands here are run from the module root '/data-preparation'
```
python3 -m pipenv install # Install dependencies
git clone https://github.com/Mondego/oreo-artifact.git
cd ./oreo-artifact/oreo/java-parser && ant metric # Generate oreo executable
```
# Running
Besides the universal environment variables, add to `.env` file at the module root `LIBRARIESIO_KEY` which can be obtained from [libraries.io](https://libraries.io/api#authentication)
```
python3 -m pipenv shell # Load environment
python3 ./scripts/fetchprojects.py # Populate update-helper/scripts/projects.txt with projects depending on guava
python3 ./scripts/preprocess.py # Preprocess guava dependents and save them to database
```
