import * as cdk from '@aws-cdk/core';
import * as cognito from '@aws-cdk/aws-cognito';
import * as iam from '@aws-cdk/aws-iam';
import * as s3 from '@aws-cdk/aws-s3';
import { BaseRestApi } from './samplifier-rest-api';

export interface SamplifierIdentityPoolProps {
    userPool: cognito.UserPool;
    userPoolClient: cognito.UserPoolClient;
    identityPoolName: string;
    restApi: BaseRestApi;
    bucket: s3.IBucket;
}

export class SamplifierIdentityPool extends cdk.Construct {
    constructor(scope: cdk.Construct, id: string, props: SamplifierIdentityPoolProps) {
        super(scope, id);

        const identityPool = new cognito.CfnIdentityPool(this, 'identity-pool', {
            identityPoolName: props.identityPoolName,
            allowUnauthenticatedIdentities: false,
            cognitoIdentityProviders: [
                {
                    clientId: props.userPoolClient.userPoolClientId,
                    providerName: props.userPool.userPoolProviderName
                }
            ]
        });

        const roleAutenticatedUsers = new iam.Role(this, 'users-group-role', {
            roleName: 'default-samplifier-authenticated-role',
            description: 'Default role for authenticated users',
            assumedBy: new iam.FederatedPrincipal(
                'cognito-identity.amazonaws.com',
                {
                    StringEquals: {
                        'cognito-identity.amazonaws.com:aud': identityPool.ref,
                    },
                    'ForAnyValue:StringLike': {
                        'cognito-identity.amazonaws.com:amr': 'authenticated',
                    },
                },
                'sts:AssumeRoleWithWebIdentity',
            ),
        });

        //role that allow authenticated users invoke api and upload object to s3
        roleAutenticatedUsers.attachInlinePolicy(
            new iam.Policy(this, 'bucket-read-upload', {
                statements: [
                    new iam.PolicyStatement({
                        effect: iam.Effect.ALLOW,
                        actions: [
                            'execute-api:Invoke',
                            'execute-api:ManageConnections',
                            'sts:AssumeRole',
                            'sts:AssumeRoleWithWebIdentity',
                        ],
                        resources: [props.restApi.arnForExecuteApi()],
                    }),
                    new iam.PolicyStatement({
                        effect: iam.Effect.ALLOW,
                        actions: [
                            's3:GetObject*', 's3:List*', 's3:PutObject', 's3:PutObjectAcl'
                        ],
                        resources: [props.bucket.bucketArn, props.bucket.arnForObjects('*')],
                    }),
                ],
            }),
        );

        new cognito.CfnIdentityPoolRoleAttachment(
            this,
            'identity-pool-role-attachment',
            {
                identityPoolId: identityPool.ref,
                roles: {
                    authenticated: roleAutenticatedUsers.roleArn
                },
                roleMappings: {
                    mapping: {
                        type: 'Token',
                        ambiguousRoleResolution: 'AuthenticatedRole',
                        identityProvider: `cognito-idp.${cdk.Stack.of(this).region}.amazonaws.com/${props.userPool.userPoolId}:${props.userPoolClient.userPoolClientId}`,
                    },
                },
            },
        );
    }
}