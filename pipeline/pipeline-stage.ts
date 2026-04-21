import * as cdk from "@aws-cdk/core";
import * as druid from "druid-cdk-construct";
import { SamplifierApp } from "../lib/samplifier-app";

export class PipelineStage extends druid.StageConfig {

    //StageProps
    constructor(scope: cdk.Construct, id: string, props: druid.StageConfigProps) {
        super(scope, id, props);

        if (!props.env)
            throw ('you must provide a env');

        new SamplifierApp(this, id, {
            env: props.env,
            envVariables: props.envVariables,
        });
    }
}