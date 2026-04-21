import * as cdk from '@aws-cdk/core';
import * as nodejs from '@aws-cdk/aws-lambda-nodejs';
import * as lambda from '@aws-cdk/aws-lambda';
import * as logs from '@aws-cdk/aws-logs';
import * as iam from "@aws-cdk/aws-iam";
import * as druid from 'druid-cdk-construct';

export class NodeFunction extends nodejs.NodejsFunction {
    constructor(scope: cdk.Construct, id: string, props: nodejs.NodejsFunctionProps) {
        const defaultProps: any = {
            runtime: lambda.Runtime.NODEJS_14_X,
            environment: {
                NODE_OPTIONS: '--enable-source-maps'
            },
            bundling: {
                externalModules: [// Use the 'aws-sdk' available in the Lambda runtime
                    'aws-sdk',
                ],
                minify: true,
                sourceMap: true
            },
            logRetention: logs.RetentionDays.ONE_WEEK
        } as nodejs.NodejsFunctionProps;

        const lambdaProps = druid.overrideProps(defaultProps, props);
        super(scope, id, lambdaProps);
        this.role?.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMFullAccess'));
    }
}