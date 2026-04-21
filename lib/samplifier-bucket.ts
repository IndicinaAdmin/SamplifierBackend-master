import * as cdk from '@aws-cdk/core';
import * as s3 from '@aws-cdk/aws-s3';
import * as druid from 'druid-cdk-construct';
import * as path from 'path';
import * as event from '@aws-cdk/aws-lambda-event-sources';
import { BaseRestApi } from './samplifier-rest-api';
import { ParameterHelper } from './helpers/ssm-helper';
import * as iam from "@aws-cdk/aws-iam";
import { RetentionDays } from "@aws-cdk/aws-logs";

export interface SamplifierCalBucketProps extends s3.BucketProps {
    restApi: BaseRestApi;
    serviceName: string;
}

export class SamplifierCalBucket extends s3.Bucket {
    processUploadFunc: druid.LambdaPowerToolsFunction;

    constructor(scope: cdk.Construct, id: string, props: SamplifierCalBucketProps) {

        const defaultProps = {
            accessControl: s3.BucketAccessControl.PRIVATE,
            removalPolicy: cdk.RemovalPolicy.DESTROY,
            autoDeleteObjects: true,
            bucketName: cdk.PhysicalName.GENERATE_IF_NEEDED,
            objectOwnership: s3.ObjectOwnership.BUCKET_OWNER_PREFERRED,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
            cors: [
                {
                    allowedMethods: [
                        s3.HttpMethods.GET,
                        s3.HttpMethods.PUT,
                        s3.HttpMethods.HEAD,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.DELETE
                    ],
                    allowedHeaders: ['*'],
                    allowedOrigins: ['*'],
                    exposedHeaders: [
                        'x-amz-server-side-encryption',
                        'x-amz-request-id',
                        'x-amz-id-2',
                        'ETag'
                    ]
                }
            ],
            encryption: s3.BucketEncryption.S3_MANAGED
        } as s3.BucketProps;

        const _bucketProps = Object.assign({}, defaultProps, props);

        super(scope, id, _bucketProps);

        this._enableCrossEnvironment();
        this.grantDelete(props.restApi.calcProxyFunction);
        this.grantPut(props.restApi.calcProxyFunction);
        this.grantPutAcl(props.restApi.calcProxyFunction);
        this.grantReadWrite(props.restApi.calcProxyFunction);

        this.grantDelete(props.restApi.userProxyFunction);
        this.grantReadWrite(props.restApi.userProxyFunction);

        //put ssm parameters here
        ParameterHelper.putParameter(this, '/samplifier/backend/bucketcalc/arn', this.bucketArn);
        ParameterHelper.putParameter(this, '/samplifier/backend/bucketcalc/domainName', this.bucketDomainName);
        ParameterHelper.putParameter(this, '/samplifier/backend/bucketcalc/name', this.bucketName);

        this.triggers(props.serviceName);
        this.configureLifecycleRule();
    }

    private configureLifecycleRule() {
        this.addLifecycleRule({
            expiration: cdk.Duration.days(7),
            prefix: 'pending/'
        });

        this.addLifecycleRule({
            expiration: cdk.Duration.days(7),
            prefix: 'invalid/'
        });
    }

    private triggers(serviceName: string) {

        this.processUploadFunc = new druid.LambdaPowerToolsFunction(this, 'process-func', {
            entry: path.resolve(__dirname, '../runtime'),
            index: '_upload_process.py',
            handler: 'handler',
            functionName: serviceName.concat('-bucket-calc-upload-process'),
            serviceName: serviceName,
            memorySize: 512,
            timeout: cdk.Duration.seconds(30),
            logRetention: RetentionDays.SIX_MONTHS,
            environment: {
                LOG_EVENTS: "true"
            }
        });

        this.processUploadFunc.role?.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMFullAccess'));

        this.grantDelete(this.processUploadFunc);
        this.grantReadWrite(this.processUploadFunc);

        //User submission xml files
        this.processUploadFunc.addEventSource(new event.S3EventSource(this, {
            events: [s3.EventType.OBJECT_CREATED],
            filters: [
                {
                    prefix: 'pending/',
                    suffix: '.xml'
                }
            ]
        }));

        //Configuration files with calculus parameters
        this.processUploadFunc.addEventSource(new event.S3EventSource(this, {
            events: [s3.EventType.OBJECT_CREATED],
            filters: [
                {
                    prefix: 'configs/',
                }
            ]
        }));
    }
}
