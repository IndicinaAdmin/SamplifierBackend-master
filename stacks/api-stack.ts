import * as cdk from '@aws-cdk/core';
import * as cognito from '@aws-cdk/aws-cognito';
import * as route53 from "@aws-cdk/aws-route53";
import { BaseRestApi } from '../lib/samplifier-rest-api';

export interface ApiStackStackProps extends cdk.StackProps {
    variables: any;
    userPool: cognito.IUserPool;
    hostedZone: route53.IHostedZone;
}

export class ApiStack extends cdk.Stack {
    private readonly hostedZoneInstance: route53.IHostedZone;
    readonly proxyApi: BaseRestApi;

    constructor(scope: cdk.Construct, id: string, props: ApiStackStackProps) {
        super(scope, id, props);

        //Creates the rest API
        this.proxyApi = new BaseRestApi(this, 'rest-api', {
            variables: props.variables,
            userPool: props.userPool,
            hostedZoneInstance: props.hostedZone
        });
    }
}