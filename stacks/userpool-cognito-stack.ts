import * as cdk from '@aws-cdk/core';
import * as cognito from '@aws-cdk/aws-cognito';
import * as route53 from "@aws-cdk/aws-route53";

import { SamplifierUserPool } from '../lib/samplifier-userpool';

export interface CognitoStackProps extends cdk.StackProps {
    domainIdentityArn: string;
    hostedZone: route53.IHostedZone;
    variables: any;
}

export class CognitoStack extends cdk.Stack {
    userPool: cognito.IUserPool;

    constructor(scope: cdk.Construct, id: string, props: CognitoStackProps) {
        super(scope, id, props);

        // identity provider
        const appUserPool = new SamplifierUserPool(this, 'samplifier-cognito', {
            domainIdentityArn: props.domainIdentityArn,
            hostedZone: props.hostedZone,
            variables: props.variables
        });
        this.userPool = appUserPool.userPool;
    }
}