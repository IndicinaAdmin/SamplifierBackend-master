import * as cdk from '@aws-cdk/core';
import * as cognito from '@aws-cdk/aws-cognito';
import * as s3 from '@aws-cdk/aws-s3';
import { SamplifierUserPoolClient } from '../lib/cognito-samplifier-client';
import { SamplifierIdentityPool } from '../lib/samplifier-identity-pool';
import { BaseRestApi } from '../lib/samplifier-rest-api';
import { ParameterHelper } from '../lib/helpers/ssm-helper';

export interface CognitoClientStackProps extends cdk.StackProps {
    userPool: cognito.IUserPool;
    bucket: s3.IBucket;
    restApi: BaseRestApi;
    variables: any;
}

export class CognitoClientStack extends cdk.Stack {

    constructor(scope: cdk.Construct, id: string, props: CognitoClientStackProps) {
        super(scope, id, props);

        const hostedZoneName = ParameterHelper.getParameter(this, props.variables.ssmParameters.hostedZoneName);

        const userPoolClient = new SamplifierUserPoolClient(this, 'userpool-client', {
            userPool: props.userPool,
            userPoolClientName: props.variables.serviceName,
            cognitoCallbackUrls: [`https://${hostedZoneName}/signin`, `https://www.${hostedZoneName}/signin`]
        });

        new SamplifierIdentityPool(this, 'identity-pool', {
            userPool: props.userPool as cognito.UserPool,
            userPoolClient: userPoolClient,
            identityPoolName: props.variables.serviceName,
            bucket: props.bucket,
            restApi: props.restApi
        });
    }
}