import * as cdk from '@aws-cdk/core';
import * as dynamodb from '@aws-cdk/aws-dynamodb';
import * as ssm from "@aws-cdk/aws-ssm";

/**
 * A Custom DynamoDB Table construct.
 */
export class DynamoDBSingleTable extends dynamodb.Table {

    constructor(scope: cdk.Construct, id: string, props: dynamodb.TableProps) {

        /**
         * The Default properties for the DynamoDB Table.
         */
        const defaultProps = {
            tableName: props.tableName,
            partitionKey: { name: "pk", type: dynamodb.AttributeType.STRING },
            sortKey: { name: "sk", type: dynamodb.AttributeType.STRING },
            removalPolicy: props.removalPolicy ?? cdk.RemovalPolicy.RETAIN,
            billingMode: props.billingMode ?? dynamodb.BillingMode.PAY_PER_REQUEST,
            pointInTimeRecovery: props.pointInTimeRecovery || true
        } as dynamodb.TableProps;

        const tableProps = Object.assign({}, defaultProps, props);

        super(scope, id, tableProps);

        //Export the ARN to ssm
        new ssm.StringParameter(this, 'dynamodb-table-arn', {
            stringValue: this.tableArn,
            parameterName: '/samplifier/dynamodb/table/arn'
        });

        //Export the table name to ssm
        new ssm.StringParameter(this, 'dynamodb-table-name', {
            stringValue: props.tableName || "table",
            parameterName: '/samplifier/dynamodb/table/name'
        });
    }
}