import * as ssm from '@aws-cdk/aws-ssm';
import * as cdk from '@aws-cdk/core';
export abstract class ParameterHelper {

    static getParameter(scope: cdk.Construct, name: string, id: string = '') {
        if (id == '')
            id = name.replace("/", "");
        return ssm.StringParameter.fromStringParameterName(scope, id, name).stringValue;
    }

    static putParameter(scope: cdk.Construct, name: string, value: string) {
        new ssm.StringParameter(scope, name.replace("/", ""), {
            stringValue: value,
            parameterName: name
        });
    }
}