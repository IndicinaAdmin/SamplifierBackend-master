#!/usr/bin/env node
import * as cdk from '@aws-cdk/core';
import { PipelineStack } from '../pipeline/pipeline-stack';
import { CONFIG } from '../config/config';
import { SamplifierApp } from '../lib/samplifier-app';

const serviceName = CONFIG.serviceName;
const app = new cdk.App();

//Add tags
cdk.Tags.of(app).add("service", serviceName);

//Dev env
const devAccount = process.env.CDK_DEPLOY_ACCOUNT || process.env.CDK_DEFAULT_ACCOUNT;
const devRegion = process.env.CDK_DEPLOY_REGION || process.env.CDK_DEFAULT_REGION;
if (devAccount && devRegion && devAccount != CONFIG.deployment.account) {
    new SamplifierApp(app, serviceName, {
        env: {
            account: devAccount,
            region: devRegion
        },
        //this must be used for local deploy without ci-cd, put gere config.{local_credentials}
        envVariables: Object.assign({}, CONFIG, CONFIG.dev)
    });
}


//CI-CD stack
new PipelineStack(app, serviceName.concat("-pipeline"), {
    env: {
        account: CONFIG.deployment.account,
        region: CONFIG.deployment.region
    },
    envVariables: CONFIG
});

app.synth();
