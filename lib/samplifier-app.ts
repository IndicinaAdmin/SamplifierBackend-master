import * as cdk from '@aws-cdk/core';
import { ApiStack } from '../stacks/api-stack';
import { StorageCalcStack } from '../stacks/storage-calc-stack';
import { CognitoClientStack } from '../stacks/userpool-client-cognito';
import { CognitoStack } from '../stacks/userpool-cognito-stack';
import { SesConfigStack } from "../stacks/ses-config-stack";

export interface SamplifierAppProps {
    envVariables: any;
    env: cdk.Environment;
}

export class SamplifierApp extends cdk.Construct {
    constructor(scope: cdk.Construct, id: string, props: SamplifierAppProps) {
        super(scope, id);

        // The Stack that configures AWS SES to allow Cognito emails to use custom email addresses
        const sesStack = new SesConfigStack(this, 'ses-config', {
            stackName: String(props.envVariables.serviceName).concat('-ses'),
            env: props.env,
            hostedZoneId: props.envVariables.ssmParameters.hostedZoneId,
            hostedZoneName: props.envVariables.ssmParameters.hostedZoneName
        });

        const cognitoStack = new CognitoStack(this, 'cognito-base', {
            stackName: String(props.envVariables.serviceName).concat('-cognito'),
            env: props.env,
            domainIdentityArn: sesStack.domainIdentityArn,
            hostedZone: sesStack.zone,
            variables: props.envVariables
        });

        cognitoStack.node.addDependency(sesStack);

        let apiStack = new ApiStack(this, 'rest-api', {
            stackName: String(props.envVariables.serviceName).concat('-rest-api'),
            env: props.env,
            userPool: cognitoStack.userPool,
            hostedZone: sesStack.zone,
            variables: props.envVariables
        });

        const storageStack = new StorageCalcStack(this, 'bucket-calc', {
            stackName: String(props.envVariables.serviceName).concat('-storage'),
            env: props.env,
            restApi: apiStack.proxyApi,
            serviceName: props.envVariables.serviceName
        });

        const cognitoClientStack = new CognitoClientStack(this, 'client', {
            stackName: String(props.envVariables.serviceName).concat('-cognito-client'),
            env: props.env,
            userPool: cognitoStack.userPool,
            bucket: storageStack.bucket,
            restApi: apiStack.proxyApi,
            variables: props.envVariables
        });

        cognitoClientStack.node.addDependency(cognitoStack);
    }
}