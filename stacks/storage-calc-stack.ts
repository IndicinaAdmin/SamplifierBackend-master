import * as cdk from '@aws-cdk/core';
import * as dynamodb from '@aws-cdk/aws-dynamodb';
import { BaseRestApi } from '../lib/samplifier-rest-api';
import { SamplifierCalBucket } from '../lib/samplifier-bucket';
import { DynamoDBSingleTable } from "../lib/samplifier-single-table";

export interface StorageCalcStackProps extends cdk.StackProps {
    restApi: BaseRestApi,
    serviceName: string
}

export class StorageCalcStack extends cdk.Stack {
    bucket: SamplifierCalBucket;

    constructor(scope: cdk.Construct, id: string, props: StorageCalcStackProps) {
        super(scope, id, props);

        //this api will use this bucket to 
        this.bucket = new SamplifierCalBucket(this, 'calc-bucket', {
            restApi: props.restApi,
            serviceName: props.serviceName
        });

        const dynamoSingleTable = new DynamoDBSingleTable(this, 'calc-table', {
            tableName: props.serviceName,
            partitionKey: { name: "pk", type: dynamodb.AttributeType.STRING }
        });

        dynamoSingleTable.grantReadWriteData(this.bucket.processUploadFunc);
        dynamoSingleTable.grantReadWriteData(props.restApi.calcProxyFunction);
        dynamoSingleTable.grantReadWriteData(props.restApi.userProxyFunction);
        
        //add global secondary index
        dynamoSingleTable.addGlobalSecondaryIndex({
            indexName: 'status-timestamp-index',
            partitionKey: {name: 'status', type: dynamodb.AttributeType.NUMBER},
            sortKey: {name: 'timestamp', type: dynamodb.AttributeType.NUMBER},
            projectionType: dynamodb.ProjectionType.INCLUDE,
            nonKeyAttributes: ['sk', 'preProcessedMrsss', 'pk', 'outputMetadata']
        });
    }
}
