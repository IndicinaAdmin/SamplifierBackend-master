import { Construct, Stack, StackProps } from "@aws-cdk/core";
import { PipelineStage } from './pipeline-stage';
import { Pipeline } from "druid-cdk-construct";

export interface PipelineStackProps extends StackProps {
    envVariables: any;
}

export class PipelineStack extends Stack {
    config: any;

    constructor(scope: Construct, id: string, props: PipelineStackProps) {
        super(scope, id, props);
        this.config = props.envVariables;

        new Pipeline(this, "-pipeline", {
            owner: 'IndicinaMichael',
            githubRepoName: 'SamplifierBackend',
            buildCommand: 'make cdk-build', //TODO ajustar para make cdk-pr corrigir no arq make tbm
            qaStage: this.buildStage('dev', this.config.dev),
            preProdStage: this.buildStage('staging', this.config.staging),
            prodStage: this.buildStage('prod', this.config.prod)
        });
    }

    private buildStage(id: string, config: any, stageConfig?: any) {
        config["serviceName"] = this.config.serviceName;
        config["ssmParameters"] = this.config.ssmParameters;

        return new PipelineStage(this, id, {
            env: {
                account: config.account,
                region: config.region
            },
            config: stageConfig ?? null,
            envVariables: config
        });
    }
}