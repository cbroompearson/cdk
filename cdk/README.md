
# Oculus CDK Infrastructure

This is the home of the CDK code that deploys the Oculus infrastructure in AWS.  All the variables used for the stack are supplied in the `cdk.json` folder in the same path as this readme.

## CDK Context
The context system is used in this stack to have different variables per stage like dev, qa, prd, etc.  It can be found at the same dir level as this readme.  Below are the different options and what they do in the stack.

**Please Note: There are different context levels, the root context where say serviceName is at is used for the whole stack where options under dev for example only are used in the dev stack**

`serviceName` - Used to name the internal resources in the stack like vpc etc, we use the service name appended with the stage to name things so like servicename-dev for example.

`cidr` - The cidr that will be used for the vpc, this is per stage dev,qa,etc. String value

`vpcAzCount` - How many availability zones should the vpc have, Integer value.

`region` - Which AWS region to deploy to. String value

`siteDomain` - The prefix for the domain entry we create in Route53 for the application, this will be appended by the zoneDomain.

`zoneDomain` - The zone we will be adding the Route53 siteDomain value to, example `nonprod.pearsoncms.net.`

`apiHealthPath` - String path of the api health check - Example `"/oculus-api/health"`

`tcaHealthPath` - String path of the tca health check - Example `"/tca/swagger-ui/index.html"`


## Project Setup

**Ensure you have your aws profile already exported before running, this stack requires AWS_PROFILE export to be set**


manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .env
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .env/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .env\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth -c stage=dev
```

You can now also deploy the stack via the below, the stage is a context system and relates back to the different stages you supply in the cdk.json file.

```
$ cdk deploy -c stage=dev
```

## Mongo Peering
After deploying you can use the Mongo Peering Python Package located at https://bitbucket.pearson.com/projects/CDKM/repos/mongo-peering/browse to setup your mongo peering.  Please see the Readme in this repo for more information.


## Additional Info/Commands
To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

# Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation


# Running Tests

Ensure you are in your virtual env and activated:

```
$ source .env/bin/activate
```

Now we can run the below pytest command to test our code

```
pytest
```

We should see something like this if passing

```
================================================================ test session starts =================================================================
platform darwin -- Python 3.7.3, pytest-5.1.0, py-1.8.0, pluggy-0.12.0
rootdir: /Users/vhopkbr/projects/cdk-examples/python/vpc_flow_logs
collected 1 item

tests/unit/test_stack.py .                                                                                                                     [100%]

================================================================= 1 passed in 0.82s ==================================================================
```