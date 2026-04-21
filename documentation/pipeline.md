# CI/CD Pipeline

Both the backend and the front end were defined using AWS CDK, an infrastructure as code tool. The frontend website code and the backend lambdas code are encompassed in their respective CDK projects. Both projects use AWS CodePipeline to manage their CI/CD. The pipelines are composed of 7 stages:
1. Source
2. Build
3. UpdatePipeline
4. Assets
5. dev
6. staging
7. prod

## 1. Source
This stage detects when a new commit is made on the GitHub repository's master branch and triggers the pipeline execution.

## 2. Build
This stage builds the CDK code and creates a change list with the actions to be executed in the next stages.

## 3. UpdatePipeline
The AWS CDK code includes the definition of the CI/CD pipeline. If the definition has been updated on the last commit, this stage will execute the necessary changes on the pipeline itself.

## 4. Assets
This stage creates and updates the necessary files that are kept in a temporary storage and then deployed at the application environments (dev, staging, prod). For instance, these files include the website html, css and javascript files in the frontend and the initial configuration files (e.g.: reference array) in the backend.

## 5. dev
This stage deploys the resources in the dev application environment. After the resources are deployed, there is a manual approbation step that enables the deployment of  the current version to the staging environment.

## 6. staging
This stage deploys the resources in the staging application environment. After the resources are deployed, there is a manual approbation step that enables the deployment of  the current version to the prod environment.

## 7. prod
This stage deploys the resources in the prod application environment.